"""Plate-solve stage-42 Roboflow WCS candidates with resumable checkpoints.

The local WSL Astrometry.net backend is used exclusively. Images are never
uploaded. Successful solutions are cached, each attempt is checkpointed, and
previous failures are skipped unless --retry-failed is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = PROJECT_ROOT / "data" / "results" / "roboflow_training_selection" / "selected_wcs.csv"
DEFAULT_WCS = PROJECT_ROOT / "data" / "wcs" / "roboflow"
DEFAULT_INPUTS = PROJECT_ROOT / "data" / "processed" / "roboflow_plate_inputs"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "roboflow_plate_solving"
PLATE_SOLVER = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
FINAL_FAILURES = {"failed", "timeout", "invalid_input"}
RESULT_FIELDS = [
    "item_id", "sample_id", "dataset", "source_split", "image_path",
    "target_candidates", "status", "attempt_count", "last_attempt_at_utc",
    "elapsed_seconds", "used_position_hint", "hint_ra", "hint_dec", "hint_radius",
    "wcs_path", "report_path", "new_fits_path", "corr_path", "center_ra",
    "center_dec", "pixscale", "orientation", "radius", "error_type", "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--wcs-dir", type=Path, default=DEFAULT_WCS)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--scale-lower", type=float, default=2.0)
    parser.add_argument("--scale-upper", type=float, default=130.0)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-position-hints", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit은 1 이상이어야 합니다.")
    if args.timeout_seconds <= 0 or not 0 < args.scale_lower < args.scale_upper:
        raise ValueError("timeout 또는 화각 범위를 확인하세요.")


def item_id(row: dict[str, str]) -> str:
    digest = hashlib.sha1(row["sample_id"].encode("utf-8")).hexdigest()[:12]
    dataset = "".join(char for char in row["dataset"] if char.isalnum())[:24]
    return f"{dataset}_{digest}"


def position_hint(row: dict[str, str]) -> tuple[float, float, float] | None:
    targets = set(row.get("target_candidates", "").split("|"))
    if "Hassaleh" in targets:
        return 78.0, 38.0, 38.0
    if "Zeta Tauri" in targets:
        return 76.0, 20.0, 38.0
    if "Bellatrix" in targets:
        return 83.0, 0.0, 38.0
    return None


def paths_for(root: Path, row: dict[str, str]) -> dict[str, Path]:
    identity = item_id(row)
    folder = root / row["dataset"] / identity
    return {
        "folder": folder,
        "wcs": folder / f"{identity}.wcs",
        "report": folder / f"{identity}_plate_solve.json",
        "new": folder / f"{identity}.new",
        "corr": folder / f"{identity}.corr",
    }


def staged_image(row: dict[str, str], input_root: Path) -> Path:
    source = Path(row["image_path"])
    target = input_root / row["dataset"] / f"{item_id(row)}{source.suffix.lower()}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        return target
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)
    return target


def read_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def report_value(report: dict[str, Any], *names: str) -> Any:
    solution = report.get("solution", {})
    for name in names:
        if report.get(name) not in (None, ""):
            return report[name]
        if isinstance(solution, dict) and solution.get(name) not in (None, ""):
            return solution[name]
    return ""


def load_previous(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row["item_id"]: row for row in read_csv(path)}


def base_result(row: dict[str, str], previous: dict[str, str] | None) -> dict[str, Any]:
    previous = previous or {}
    status = previous.get("status", "unprocessed")
    if status == "dry_run_pending":
        status = "unprocessed"
    hint = position_hint(row)
    return {
        "item_id": item_id(row), "sample_id": row["sample_id"], "dataset": row["dataset"],
        "source_split": row["source_split"], "image_path": row["image_path"],
        "target_candidates": row.get("target_candidates", ""), "status": status,
        "attempt_count": int(previous.get("attempt_count") or 0),
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


def solve(row: dict[str, str], paths: dict[str, Path], args: argparse.Namespace) -> tuple[str, dict[str, Any], float, bool]:
    image_path = staged_image(row, args.input_dir.resolve())
    if not image_path.is_file():
        return "invalid_input", {"error_type": "FileNotFoundError", "error": str(image_path)}, 0.0, False
    try:
        with Image.open(image_path) as image:
            longest = max(image.size)
    except OSError as error:
        return "invalid_input", {"error_type": type(error).__name__, "error": str(error)}, 0.0, False
    downsample = 4 if longest >= 3000 else (2 if longest >= 1200 else 1)
    command = [
        sys.executable, str(PLATE_SOLVER), str(image_path), "--backend", "local",
        "--no-nova-fallback", "--output-dir", str((args.wcs_dir / row["dataset"]).resolve()),
        "--wsl-distribution", args.wsl_distribution, "--timeout-seconds", str(args.timeout_seconds),
        "--downsample", str(downsample), "--scale-units", "degwidth",
        "--scale-lower", str(args.scale_lower), "--scale-upper", str(args.scale_upper),
    ]
    hint = None if args.no_position_hints else position_hint(row)
    if hint:
        command.extend(["--center-ra", str(hint[0]), "--center-dec", str(hint[1]), "--radius", str(hint[2])])
    if args.force:
        command.append("--force")
    started = time.monotonic()
    completed = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    elapsed = round(time.monotonic() - started, 3)
    report = read_report(paths["report"])
    if paths["wcs"].is_file():
        return "success", report, elapsed, bool(hint)
    error_type = str(report.get("error_type") or "PlateSolveFailed")
    error = str(report.get("error") or completed.stderr.strip() or completed.stdout.strip())[-1000:]
    status = "timeout" if "timeout" in error_type.lower() or "초과" in error else "failed"
    return status, {"error_type": error_type, "error": error}, elapsed, bool(hint)


def summary(queue: list[dict[str, str]], results: dict[str, dict[str, Any]], attempted: int, dry_run: bool) -> dict[str, Any]:
    counts = Counter(results[item_id(row)]["status"] for row in queue)
    return {
        "status": "completed", "queue_images": len(queue), "attempted_this_run": attempted,
        "status_counts": dict(sorted(counts.items())),
        "successful_wcs": counts.get("success", 0) + counts.get("cached_success", 0),
        "failed": counts.get("failed", 0) + counts.get("timeout", 0) + counts.get("invalid_input", 0),
        "remaining_unprocessed": counts.get("unprocessed", 0) + counts.get("dry_run_pending", 0),
        "dry_run": dry_run, "backend": "WSL local Astrometry.net only", "nova_fallback": False,
        "source_images_modified": False, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    queue_path, output = args.queue.resolve(), args.output_dir.resolve()
    results_path, summary_path = output / "plate_solve_results.csv", output / "summary.json"
    if not queue_path.is_file():
        raise FileNotFoundError(f"42번 WCS 대기열이 없습니다: {queue_path}")
    queue = read_csv(queue_path)
    if not queue:
        raise RuntimeError("WCS 대기열이 비어 있습니다.")
    identities = [item_id(row) for row in queue]
    if len(set(identities)) != len(identities):
        raise ValueError("생성된 WCS item_id가 중복됩니다.")
    previous = load_previous(results_path)
    results = {item_id(row): base_result(row, previous.get(item_id(row))) for row in queue}
    attempted = 0
    for index, row in enumerate(queue, 1):
        identity = item_id(row)
        result, paths = results[identity], paths_for(args.wcs_dir.resolve(), row)
        if paths["wcs"].is_file() and not args.force:
            report = read_report(paths["report"])
            result.update({
                "status": "cached_success", "wcs_path": str(paths["wcs"]), "report_path": str(paths["report"]),
                "new_fits_path": str(paths["new"]) if paths["new"].is_file() else "",
                "corr_path": str(paths["corr"]) if paths["corr"].is_file() else "",
                "center_ra": report_value(report, "center_ra", "ra"), "center_dec": report_value(report, "center_dec", "dec"),
                "pixscale": report_value(report, "pixscale", "pixel_scale"), "orientation": report_value(report, "orientation"),
                "radius": report_value(report, "radius"), "error_type": "", "error": "",
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
        print(f"[{index:04d}/{len(queue):04d}] {identity}: {Path(row['image_path']).name}")
        status, details, elapsed, used_hint = solve(row, paths, args)
        report = details if status == "success" else read_report(paths["report"])
        result.update({
            "status": status, "attempt_count": int(result["attempt_count"]) + 1,
            "last_attempt_at_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": elapsed,
            "used_position_hint": used_hint, "wcs_path": str(paths["wcs"]) if paths["wcs"].is_file() else "",
            "report_path": str(paths["report"]), "new_fits_path": str(paths["new"]) if paths["new"].is_file() else "",
            "corr_path": str(paths["corr"]) if paths["corr"].is_file() else "",
            "center_ra": report_value(report, "center_ra", "ra"), "center_dec": report_value(report, "center_dec", "dec"),
            "pixscale": report_value(report, "pixscale", "pixel_scale"), "orientation": report_value(report, "orientation"),
            "radius": report_value(report, "radius"), "error_type": details.get("error_type", "") if status != "success" else "",
            "error": details.get("error", "") if status != "success" else "",
        })
        attempted += 1
        print(f"  결과: {status} ({elapsed:.1f}초)")
        checkpoint(results_path, queue, results)
        write_json(summary_path, summary(queue, results, attempted, False))
    checkpoint(results_path, queue, results)
    ordered = [results[item_id(row)] for row in queue]
    write_csv(output / "successful_wcs.csv", [row for row in ordered if row["status"] in {"success", "cached_success"}], RESULT_FIELDS)
    write_csv(output / "failed_plate_solves.csv", [row for row in ordered if row["status"] in FINAL_FAILURES], RESULT_FIELDS)
    final = summary(queue, results, attempted, args.dry_run)
    write_json(summary_path, final)
    print("Roboflow 43번 Plate Solving 배치 종료")
    print(f"이번 실행 시도: {attempted:,}장")
    print(f"누적 WCS 성공: {final['successful_wcs']:,}/{len(queue):,}장")
    print(f"실패: {final['failed']:,}장 / 미처리: {final['remaining_unprocessed']:,}장")
    print(f"results: {results_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
