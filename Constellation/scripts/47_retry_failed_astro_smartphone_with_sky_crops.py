"""Retry failed AstroSmartphone plate solves using sky crops and overlap tiles.

Only stage-30 failures are queued. Derived JPEG crops contain no EXIF metadata
and source images are never changed. On success the crop WCS CRPIX is shifted
back into the original-image pixel system and a stage-31-compatible combined
result CSV is written alongside the retry artifacts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astropy.io import fits
from PIL import Image, ImageEnhance, ImageOps

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE30 = PROJECT_ROOT / "data" / "results" / "astro_smartphone_plate_solving" / "plate_solve_results.csv"
DEFAULT_DERIVED = PROJECT_ROOT / "data" / "processed" / "astro_smartphone_sky_crops"
DEFAULT_WCS = PROJECT_ROOT / "data" / "wcs" / "astro_smartphone_crop_retry"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_crop_retry"
PLATE_SOLVER = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
SUCCESS = {"success", "cached_success", "recovered_success"}
FAILURE = {"failed", "timeout", "invalid_input", "all_strategies_failed"}
STAGE30_FIELDS = [
    "capture_group_id", "session_id", "device_folder", "filename", "source_path",
    "captured_at", "gps_available", "width", "height", "resolution_kind",
    "status", "attempt_count", "last_attempt_at_utc", "elapsed_seconds",
    "wcs_path", "report_path", "new_fits_path", "corr_path", "error_type", "error",
]
RETRY_FIELDS = STAGE30_FIELDS + [
    "strategy", "strategy_attempts", "crop_path", "crop_x", "crop_y",
    "crop_width", "crop_height", "original_width", "original_height",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage30-results", type=Path, default=DEFAULT_STAGE30)
    parser.add_argument("--derived-dir", type=Path, default=DEFAULT_DERIVED)
    parser.add_argument("--wcs-dir", type=Path, default=DEFAULT_WCS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, help="이번 실행에서 처리할 원본 사진 수")
    parser.add_argument("--timeout-seconds", type=int, default=35, help="crop 하나당 제한 시간")
    parser.add_argument("--scale-lower", type=float, default=5.0)
    parser.add_argument("--scale-upper", type=float, default=100.0)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit은 1 이상이어야 합니다.")
    if args.timeout_seconds < 30:
        raise ValueError("--timeout-seconds는 30 이상이어야 합니다.")
    if not 0 < args.scale_lower < args.scale_upper:
        raise ValueError("화각 범위를 확인하세요.")


def safe(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in value).strip("_") or "unknown"


def crop_strategies(width: int, height: int) -> list[tuple[str, tuple[int, int, int, int]]]:
    # Landscape foreground is normally at the bottom. Overlapping horizontal
    # tiles also reduce the blind-search field while retaining many stars.
    return [
        ("sky_top85", (0, 0, width, max(64, round(height * 0.85)))),
        ("sky_top70", (0, 0, width, max(64, round(height * 0.70)))),
        ("sky_left", (0, 0, max(64, round(width * 0.65)), max(64, round(height * 0.82)))),
        ("sky_center", (round(width * 0.175), 0, round(width * 0.825), max(64, round(height * 0.82)))),
        ("sky_right", (round(width * 0.35), 0, width, max(64, round(height * 0.82)))),
    ]


def create_crop(source: Path, target: Path, box: tuple[int, int, int, int]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        return
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert("RGB").crop(box)
        # Mild contrast enhancement helps local star extraction without
        # inventing sources or altering the original file.
        image = ImageEnhance.Contrast(image).enhance(1.15)
        image.save(target, "JPEG", quality=92, optimize=True)


def product_paths(root: Path, crop: Path) -> dict[str, Path]:
    folder = root / crop.stem
    return {
        "folder": folder, "wcs": folder / f"{crop.stem}.wcs",
        "report": folder / f"{crop.stem}_plate_solve.json",
        "new_fits": folder / f"{crop.stem}.new", "corr": folder / f"{crop.stem}.corr",
    }


def report_error(path: Path) -> tuple[str, str]:
    if not path.is_file():
        return "PlateSolveFailed", "WCS가 생성되지 않았습니다."
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        return str(report.get("error_type") or "PlateSolveFailed"), str(report.get("error") or "WCS가 생성되지 않았습니다.")
    except (OSError, json.JSONDecodeError):
        return "PlateSolveFailed", "Plate Solving 보고서를 읽지 못했습니다."


def solve_crop(crop: Path, root: Path, args: argparse.Namespace) -> tuple[bool, float, dict[str, Path], str, str]:
    paths = product_paths(root, crop)
    command = [
        sys.executable, str(PLATE_SOLVER), str(crop), "--backend", "local", "--no-nova-fallback",
        "--output-dir", str(root), "--wsl-distribution", args.wsl_distribution,
        "--timeout-seconds", str(args.timeout_seconds), "--downsample", "2",
        "--scale-units", "degwidth", "--scale-lower", str(args.scale_lower),
        "--scale-upper", str(args.scale_upper),
    ]
    if args.force:
        command.append("--force")
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    elapsed = round(time.monotonic() - started, 3)
    if paths["wcs"].is_file():
        return True, elapsed, paths, "", ""
    error_type, error = report_error(paths["report"])
    if not error:
        error = (completed.stderr.strip() or completed.stdout.strip())[-1000:]
    return False, elapsed, paths, error_type, error[-1000:]


def restore_original_wcs(crop_wcs: Path, target: Path, x0: int, y0: int, width: int, height: int) -> None:
    header = fits.getheader(crop_wcs, 0)
    header["CRPIX1"] = float(header["CRPIX1"]) + x0
    header["CRPIX2"] = float(header["CRPIX2"]) + y0
    header["NAXIS"] = 2
    header["NAXIS1"] = width
    header["NAXIS2"] = height
    header.add_history(f"Restored from crop offset x={x0}, y={y0}")
    target.parent.mkdir(parents=True, exist_ok=True)
    fits.PrimaryHDU(header=header).writeto(target, overwrite=True, output_verify="silentfix")


def load_previous(path: Path) -> dict[str, dict[str, str]]:
    return {row["capture_group_id"]: row for row in read_csv(path)} if path.is_file() else {}


def base_retry(row: dict[str, str], previous: dict[str, str] | None) -> dict[str, Any]:
    previous = previous or {}
    return {
        **{field: row.get(field, "") for field in STAGE30_FIELDS},
        "status": previous.get("status", "unprocessed"),
        "attempt_count": int(previous.get("attempt_count") or 0),
        "last_attempt_at_utc": previous.get("last_attempt_at_utc", ""),
        "elapsed_seconds": previous.get("elapsed_seconds", ""),
        "wcs_path": previous.get("wcs_path", ""), "report_path": previous.get("report_path", ""),
        "new_fits_path": previous.get("new_fits_path", ""), "corr_path": previous.get("corr_path", ""),
        "error_type": previous.get("error_type", ""), "error": previous.get("error", ""),
        "strategy": previous.get("strategy", ""), "strategy_attempts": previous.get("strategy_attempts", ""),
        "crop_path": previous.get("crop_path", ""), "crop_x": previous.get("crop_x", ""),
        "crop_y": previous.get("crop_y", ""), "crop_width": previous.get("crop_width", ""),
        "crop_height": previous.get("crop_height", ""), "original_width": previous.get("original_width", row.get("width", "")),
        "original_height": previous.get("original_height", row.get("height", "")),
    }


def checkpoint(path: Path, queue: list[dict[str, str]], results: dict[str, dict[str, Any]]) -> None:
    write_csv(path, [results[row["capture_group_id"]] for row in queue], RETRY_FIELDS)


def write_combined(stage30: list[dict[str, str]], retries: dict[str, dict[str, Any]], path: Path) -> None:
    combined: list[dict[str, Any]] = []
    for original in stage30:
        recovered = retries.get(original["capture_group_id"])
        source = recovered if recovered and recovered.get("status") == "recovered_success" else original
        combined.append({field: source.get(field, "") for field in STAGE30_FIELDS})
    write_csv(path, combined, STAGE30_FIELDS)


def summary(queue: list[dict[str, str]], results: dict[str, dict[str, Any]], attempted: int, strategy_attempts: int, dry_run: bool) -> dict[str, Any]:
    counts = Counter(str(results[row["capture_group_id"]]["status"]) for row in queue)
    elapsed = sum(float(results[row["capture_group_id"]].get("elapsed_seconds") or 0) for row in queue)
    return {
        "status": "completed", "failed_stage30_images": len(queue), "attempted_source_images_this_run": attempted,
        "strategy_attempts_this_run": strategy_attempts, "status_counts": dict(sorted(counts.items())),
        "recovered_wcs": counts.get("recovered_success", 0), "remaining_unprocessed": counts.get("unprocessed", 0),
        "recorded_elapsed_seconds": round(elapsed, 3), "dry_run": dry_run,
        "source_images_modified": False, "derived_images_have_exif": False,
        "backend": "WSL local Astrometry.net only", "nova_fallback": False,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    stage30_path, output = args.stage30_results.resolve(), args.output_dir.resolve()
    if not stage30_path.is_file():
        raise FileNotFoundError(f"30번 결과가 없습니다: {stage30_path}")
    stage30 = read_csv(stage30_path)
    queue = [row for row in stage30 if row.get("status") not in SUCCESS]
    result_path = output / "crop_retry_results.csv"
    combined_path = output / "combined_plate_solve_results.csv"
    summary_path = output / "summary.json"
    previous = load_previous(result_path)
    results = {row["capture_group_id"]: base_retry(row, previous.get(row["capture_group_id"])) for row in queue}
    attempted = strategy_attempts = 0
    for index, row in enumerate(queue, 1):
        result = results[row["capture_group_id"]]
        if result["status"] == "recovered_success" and Path(result.get("wcs_path", "")).is_file() and not args.force:
            continue
        if result["status"] in FAILURE and not args.retry_failed and not args.force:
            continue
        if args.limit is not None and attempted >= args.limit:
            continue
        if args.dry_run:
            attempted += 1
            continue
        source = Path(row["source_path"])
        print(f"[{index:03d}/{len(queue):03d}] {row['capture_group_id']}: {source.name}")
        if not source.is_file():
            result.update({"status": "invalid_input", "error_type": "FileNotFoundError", "error": str(source)})
            attempted += 1
            continue
        with Image.open(source) as image:
            width, height = ImageOps.exif_transpose(image).size
        total_elapsed = 0.0
        last_type = last_error = ""
        strategies_used = 0
        for strategy, box in crop_strategies(width, height):
            crop = args.derived_dir.resolve() / safe(row["capture_group_id"]) / f"{safe(row['capture_group_id'])}_{strategy}.jpg"
            create_crop(source, crop, box)
            success, elapsed, paths, error_type, error = solve_crop(crop, args.wcs_dir.resolve() / safe(row["capture_group_id"]), args)
            total_elapsed += elapsed
            strategies_used += 1
            strategy_attempts += 1
            print(f"  {strategy}: {'success' if success else 'failed'} ({elapsed:.1f}초)")
            if success:
                restored = args.wcs_dir.resolve() / "restored_original" / f"{safe(row['capture_group_id'])}.wcs"
                x0, y0, x1, y1 = box
                restore_original_wcs(paths["wcs"], restored, x0, y0, width, height)
                result.update({
                    "status": "recovered_success", "strategy": strategy, "strategy_attempts": strategies_used,
                    "crop_path": str(crop), "crop_x": x0, "crop_y": y0, "crop_width": x1 - x0,
                    "crop_height": y1 - y0, "original_width": width, "original_height": height,
                    "wcs_path": str(restored), "report_path": str(paths["report"]),
                    "new_fits_path": str(paths["new_fits"]) if paths["new_fits"].is_file() else "",
                    "corr_path": str(paths["corr"]) if paths["corr"].is_file() else "",
                    "error_type": "", "error": "",
                })
                break
            last_type, last_error = error_type, error
        else:
            result.update({"status": "all_strategies_failed", "strategy": "", "strategy_attempts": strategies_used, "error_type": last_type, "error": last_error})
        result.update({
            "attempt_count": int(result.get("attempt_count") or 0) + 1,
            "last_attempt_at_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": round(total_elapsed, 3),
        })
        attempted += 1
        checkpoint(result_path, queue, results)
        write_combined(stage30, results, combined_path)
        write_json(summary_path, summary(queue, results, attempted, strategy_attempts, False))

    checkpoint(result_path, queue, results)
    write_combined(stage30, results, combined_path)
    payload = summary(queue, results, attempted, strategy_attempts, args.dry_run)
    payload["paths"] = {"results": str(result_path), "combined_results": str(combined_path), "restored_wcs": str(args.wcs_dir.resolve() / "restored_original")}
    write_json(summary_path, payload)
    print("47번 AstroSmartphone crop/tile Plate Solving 종료")
    print(f"이번 실행 원본: {attempted}장 / crop 시도: {strategy_attempts}회")
    print(f"복구 성공: {payload['recovered_wcs']}/{len(queue)}장 / 미처리: {payload['remaining_unprocessed']}장")
    print(f"results: {result_path}")
    print(f"combined: {combined_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
