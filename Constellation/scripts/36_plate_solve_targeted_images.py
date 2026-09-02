"""Plate-solve stage-35 TargetedWeb night-sky candidates with resume support.

Only the local WSL Astrometry.net backend is used, so no downloaded image is
uploaded to Nova.  Results are checkpointed after every attempt.  Existing WCS
files are cached, and failed rows are skipped unless ``--retry-failed`` is set.
This stage creates celestial WCS solutions only; target projection and YOLO
labels belong to stage 37.
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

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLASSIFICATION = (
    PROJECT_ROOT / "data" / "results" / "targeted_web_classification" / "classification.csv"
)
DEFAULT_WCS = PROJECT_ROOT / "data" / "wcs" / "targeted_web"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "targeted_web_plate_solving"
PLATE_SOLVER = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
VALID_LABELS = {"valid_smartphone_night_sky", "valid_night_sky_device_unknown"}
FINAL_FAILURES = {"failed", "timeout", "invalid_input"}
RESULT_FIELDS = [
    "item_id", "provider", "provider_id", "query_group", "filename", "source_path",
    "classification", "camera_kind", "width", "height", "status", "attempt_count",
    "last_attempt_at_utc", "elapsed_seconds", "used_position_hint", "hint_ra",
    "hint_dec", "hint_radius", "wcs_path", "report_path", "new_fits_path", "corr_path",
    "center_ra", "center_dec", "pixscale", "orientation", "radius",
    "error_type", "error",
]

POSITION_HINTS: dict[str, tuple[float, float, float]] = {
    "hassaleh": (74.25, 33.17, 55.0),
    "bellatrix": (81.28, 6.35, 55.0),
    "aldebaran": (68.98, 16.51, 55.0),
    "zeta_tauri": (84.41, 21.14, 55.0),
    "other_targets": (76.0, 20.0, 65.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classification", type=Path, default=DEFAULT_CLASSIFICATION)
    parser.add_argument("--wcs-dir", type=Path, default=DEFAULT_WCS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, help="이번 실행에서 새로 시도할 최대 사진 수")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--scale-lower", type=float, default=10.0)
    parser.add_argument("--scale-upper", type=float, default=130.0)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force", action="store_true", help="성공 캐시도 다시 해결")
    parser.add_argument("--no-position-hints", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit은 1 이상이어야 합니다.")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds는 1 이상이어야 합니다.")
    if not 0 < args.scale_lower < args.scale_upper:
        raise ValueError("Plate Solving 화각 범위를 확인하세요.")


def safe_component(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in "-_" else "_" for character in value)
    return cleaned.strip("_") or "unknown"


def item_id(row: dict[str, str]) -> str:
    return safe_component(Path(row.get("filename", "unknown")).stem)


def product_paths(wcs_root: Path, row: dict[str, str]) -> dict[str, Path]:
    identity = item_id(row)
    folder = wcs_root / identity
    return {
        "folder": folder,
        "wcs": folder / f"{identity}.wcs",
        "report": folder / f"{identity}_plate_solve.json",
        "new_fits": folder / f"{identity}.new",
        "corr": folder / f"{identity}.corr",
    }


def read_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def report_value(report: dict[str, Any], *names: str) -> Any:
    for name in names:
        if report.get(name) not in (None, ""):
            return report[name]
    solution = report.get("solution")
    if isinstance(solution, dict):
        for name in names:
            if solution.get(name) not in (None, ""):
                return solution[name]
    return ""


def load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row.get("item_id", ""): row for row in read_csv(path) if row.get("item_id")}


def base_result(row: dict[str, str], previous: dict[str, str] | None = None) -> dict[str, Any]:
    previous = previous or {}
    prior_status = previous.get("status", "unprocessed")
    if prior_status == "dry_run_pending":
        prior_status = "unprocessed"
    hint = POSITION_HINTS.get(row.get("query_group", ""))
    return {
        "item_id": item_id(row), "provider": row.get("provider", ""),
        "provider_id": row.get("provider_id", ""), "query_group": row.get("query_group", ""),
        "filename": row.get("filename", ""), "source_path": row.get("source_path", ""),
        "classification": row.get("final_label", ""), "camera_kind": row.get("camera_kind", ""),
        "width": row.get("width", ""), "height": row.get("height", ""),
        "status": prior_status, "attempt_count": int(previous.get("attempt_count") or 0),
        "last_attempt_at_utc": previous.get("last_attempt_at_utc", ""),
        "elapsed_seconds": previous.get("elapsed_seconds", ""),
        "used_position_hint": previous.get("used_position_hint", ""),
        "hint_ra": previous.get("hint_ra", hint[0] if hint else ""),
        "hint_dec": previous.get("hint_dec", hint[1] if hint else ""),
        "hint_radius": previous.get("hint_radius", hint[2] if hint else ""),
        "wcs_path": previous.get("wcs_path", ""), "report_path": previous.get("report_path", ""),
        "new_fits_path": previous.get("new_fits_path", ""), "corr_path": previous.get("corr_path", ""),
        "center_ra": previous.get("center_ra", ""), "center_dec": previous.get("center_dec", ""),
        "pixscale": previous.get("pixscale", ""), "orientation": previous.get("orientation", ""),
        "radius": previous.get("radius", ""), "error_type": previous.get("error_type", ""),
        "error": previous.get("error", ""),
    }


def checkpoint(path: Path, queue: list[dict[str, str]], results: dict[str, dict[str, Any]]) -> None:
    write_csv(path, [results[item_id(row)] for row in queue], RESULT_FIELDS)


def solve_one(
    row: dict[str, str], paths: dict[str, Path], args: argparse.Namespace
) -> tuple[str, dict[str, Any], float, bool]:
    image = Path(row["source_path"])
    if not image.is_file():
        return "invalid_input", {"error_type": "FileNotFoundError", "error": f"사진이 없습니다: {image}"}, 0.0, False
    longest = max(int(float(row.get("width") or 0)), int(float(row.get("height") or 0)))
    downsample = 4 if longest >= 3000 else 2
    command = [
        sys.executable, str(PLATE_SOLVER), str(image), "--backend", "local",
        "--no-nova-fallback", "--output-dir", str(args.wcs_dir.resolve()),
        "--wsl-distribution", args.wsl_distribution,
        "--timeout-seconds", str(args.timeout_seconds), "--downsample", str(downsample),
        "--scale-units", "degwidth", "--scale-lower", str(args.scale_lower),
        "--scale-upper", str(args.scale_upper),
    ]
    hint = None if args.no_position_hints else POSITION_HINTS.get(row.get("query_group", ""))
    if hint:
        command.extend([
            "--center-ra", str(hint[0]), "--center-dec", str(hint[1]), "--radius", str(hint[2]),
        ])
    if args.force:
        command.append("--force")
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    elapsed = round(time.monotonic() - started, 3)
    report = read_report(paths["report"])
    if paths["wcs"].is_file():
        return "success", report, elapsed, bool(hint)
    error_type = str(report.get("error_type") or "PlateSolveFailed")
    error = str(report.get("error") or completed.stderr.strip() or completed.stdout.strip())[-1000:]
    status = "timeout" if "timeout" in error_type.lower() or "시간" in error else "failed"
    return status, {"error_type": error_type, "error": error}, elapsed, bool(hint)


def create_summary(
    queue: list[dict[str, str]], results: dict[str, dict[str, Any]], attempted: int, dry_run: bool
) -> dict[str, Any]:
    rows = [results[item_id(row)] for row in queue]
    counts = Counter(str(row["status"]) for row in rows)
    return {
        "status": "completed", "selected_images": len(queue),
        "attempted_this_run": attempted, "status_counts": dict(sorted(counts.items())),
        "successful_wcs": counts.get("success", 0) + counts.get("cached_success", 0),
        "remaining_unprocessed": counts.get("unprocessed", 0) + counts.get("dry_run_pending", 0),
        "dry_run": dry_run, "backend": "WSL local Astrometry.net only",
        "nova_fallback": False, "privacy": "No image is uploaded to an external service.",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    classification_path = args.classification.resolve()
    output_dir = args.output_dir.resolve()
    results_path = output_dir / "plate_solve_results.csv"
    summary_path = output_dir / "summary.json"
    success_path = output_dir / "successful_wcs.csv"
    failure_path = output_dir / "failed_plate_solves.csv"
    if not classification_path.is_file():
        raise FileNotFoundError(f"35번 분류 결과가 없습니다: {classification_path}")
    queue = [
        row for row in read_csv(classification_path)
        if row.get("final_label") in VALID_LABELS
    ]
    if not queue:
        raise RuntimeError("Plate Solving 대상 밤하늘 후보가 없습니다.")
    identities = [item_id(row) for row in queue]
    if len(set(identities)) != len(identities):
        raise ValueError("파일명 기반 item_id가 중복됩니다.")

    previous = load_existing(results_path)
    results = {item_id(row): base_result(row, previous.get(item_id(row))) for row in queue}
    attempted = 0
    for index, row in enumerate(queue, 1):
        identity = item_id(row)
        result = results[identity]
        paths = product_paths(args.wcs_dir.resolve(), row)
        if paths["wcs"].is_file() and not args.force:
            report = read_report(paths["report"])
            result.update({
                "status": "cached_success", "wcs_path": str(paths["wcs"]),
                "report_path": str(paths["report"]),
                "new_fits_path": str(paths["new_fits"]) if paths["new_fits"].is_file() else "",
                "corr_path": str(paths["corr"]) if paths["corr"].is_file() else "",
                "center_ra": report_value(report, "center_ra", "ra"),
                "center_dec": report_value(report, "center_dec", "dec"),
                "pixscale": report_value(report, "pixscale", "pixel_scale"),
                "orientation": report_value(report, "orientation"), "radius": report_value(report, "radius"),
                "error_type": "", "error": "",
            })
            continue
        if result["status"] in FINAL_FAILURES and not args.retry_failed and not args.force:
            continue
        if args.limit is not None and attempted >= args.limit:
            continue
        if args.dry_run:
            result["status"] = "dry_run_pending"
            attempted += 1
            continue

        print(f"[{index:03d}/{len(queue):03d}] {identity}: {row['filename']}")
        status, details, elapsed, used_hint = solve_one(row, paths, args)
        report = details if status == "success" else read_report(paths["report"])
        result.update({
            "status": status, "attempt_count": int(result["attempt_count"]) + 1,
            "last_attempt_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed, "used_position_hint": used_hint,
            "wcs_path": str(paths["wcs"]) if paths["wcs"].is_file() else "",
            "report_path": str(paths["report"]),
            "new_fits_path": str(paths["new_fits"]) if paths["new_fits"].is_file() else "",
            "corr_path": str(paths["corr"]) if paths["corr"].is_file() else "",
            "center_ra": report_value(report, "center_ra", "ra"),
            "center_dec": report_value(report, "center_dec", "dec"),
            "pixscale": report_value(report, "pixscale", "pixel_scale"),
            "orientation": report_value(report, "orientation"), "radius": report_value(report, "radius"),
            "error_type": details.get("error_type", "") if status != "success" else "",
            "error": details.get("error", "") if status != "success" else "",
        })
        attempted += 1
        print(f"  결과: {status} ({elapsed:.1f}초)")
        checkpoint(results_path, queue, results)
        write_json(summary_path, create_summary(queue, results, attempted, False))

    checkpoint(results_path, queue, results)
    ordered = [results[item_id(row)] for row in queue]
    successes = [row for row in ordered if row["status"] in {"success", "cached_success"}]
    failures = [row for row in ordered if row["status"] in FINAL_FAILURES]
    write_csv(success_path, successes, RESULT_FIELDS)
    write_csv(failure_path, failures, RESULT_FIELDS)
    summary = create_summary(queue, results, attempted, args.dry_run)
    write_json(summary_path, summary)
    print("TargetedWeb Plate Solving 배치 종료")
    print(f"이번 실행 시도: {attempted:,}장")
    print(f"누적 WCS 성공: {summary['successful_wcs']:,}/{len(queue):,}장")
    print(f"실패: {len(failures):,}장")
    print(f"미처리: {summary['remaining_unprocessed']:,}장")
    print(f"results: {results_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
