"""Batch plate-solve AstroSmartphone capture representatives with resume support.

The runner is local-only: it invokes stage 07 with the WSL Astrometry.net
backend and explicitly disables Nova fallback.  Results are checkpointed after
every image so interruption is safe.  Successful WCS files are always reused;
previous failures are skipped unless ``--retry-failed`` is requested.
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
DEFAULT_QUEUE = PROJECT_ROOT / "data" / "results" / "astro_smartphone_inventory" / "plate_solve_queue.csv"
DEFAULT_WCS = PROJECT_ROOT / "data" / "wcs" / "astro_smartphone"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_plate_solving"
PLATE_SOLVER = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
RESULT_FIELDS = [
    "capture_group_id", "session_id", "device_folder", "filename", "source_path",
    "captured_at", "gps_available", "width", "height", "resolution_kind",
    "status", "attempt_count", "last_attempt_at_utc", "elapsed_seconds",
    "wcs_path", "report_path", "new_fits_path", "corr_path", "error_type", "error",
]
FINAL_FAILURES = {"failed", "timeout", "invalid_input"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--wcs-dir", type=Path, default=DEFAULT_WCS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, help="Maximum number of images to attempt this run")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--scale-lower", type=float, default=35.0)
    parser.add_argument("--scale-upper", type=float, default=120.0)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-solve even successful cached WCS files")
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


def product_paths(wcs_root: Path, row: dict[str, str]) -> dict[str, Path]:
    image = Path(row["source_path"])
    device_root = wcs_root / safe_component(row.get("device_folder", "unknown"))
    folder = device_root / image.stem
    return {
        "device_root": device_root,
        "folder": folder,
        "wcs": folder / f"{image.stem}.wcs",
        "report": folder / f"{image.stem}_plate_solve.json",
        "new_fits": folder / f"{image.stem}.new",
        "corr": folder / f"{image.stem}.corr",
    }


def load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row.get("capture_group_id", ""): row for row in read_csv(path) if row.get("capture_group_id")}


def base_result(row: dict[str, str], previous: dict[str, str] | None = None) -> dict[str, Any]:
    previous = previous or {}
    previous_status = previous.get("status", "unprocessed")
    if previous_status == "dry_run_pending":
        previous_status = "unprocessed"
    return {
        "capture_group_id": row.get("capture_group_id", ""),
        "session_id": row.get("session_id", ""),
        "device_folder": row.get("device_folder", ""),
        "filename": row.get("filename", ""),
        "source_path": row.get("source_path", ""),
        "captured_at": row.get("captured_at", ""),
        "gps_available": row.get("gps_available", ""),
        "width": row.get("width", ""),
        "height": row.get("height", ""),
        "resolution_kind": row.get("resolution_kind", ""),
        "status": previous_status,
        "attempt_count": int(previous.get("attempt_count") or 0),
        "last_attempt_at_utc": previous.get("last_attempt_at_utc", ""),
        "elapsed_seconds": previous.get("elapsed_seconds", ""),
        "wcs_path": previous.get("wcs_path", ""),
        "report_path": previous.get("report_path", ""),
        "new_fits_path": previous.get("new_fits_path", ""),
        "corr_path": previous.get("corr_path", ""),
        "error_type": previous.get("error_type", ""),
        "error": previous.get("error", ""),
    }


def checkpoint(path: Path, queue: list[dict[str, str]], results: dict[str, dict[str, Any]]) -> None:
    ordered = [results[row["capture_group_id"]] for row in queue]
    write_csv(path, ordered, RESULT_FIELDS)


def read_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def solve_one(row: dict[str, str], paths: dict[str, Path], args: argparse.Namespace) -> tuple[str, dict[str, Any], float]:
    image = Path(row["source_path"])
    if not image.is_file():
        return "invalid_input", {"error_type": "FileNotFoundError", "error": f"사진이 없습니다: {image}"}, 0.0
    longest = max(int(row.get("width") or 0), int(row.get("height") or 0))
    downsample = 4 if longest >= 3000 else 2
    command = [
        sys.executable, str(PLATE_SOLVER), str(image),
        "--backend", "local", "--no-nova-fallback",
        "--output-dir", str(paths["device_root"]),
        "--timeout-seconds", str(args.timeout_seconds),
        "--downsample", str(downsample),
        "--scale-units", "degwidth",
        "--scale-lower", str(args.scale_lower),
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
    report = read_report(paths["report"])
    if paths["wcs"].is_file():
        return "success", report, elapsed
    error_type = str(report.get("error_type") or "PlateSolveFailed")
    error = str(report.get("error") or completed.stderr.strip() or completed.stdout.strip())[-1000:]
    status = "timeout" if "timeout" in error_type.lower() or "초과" in error else "failed"
    return status, {"error_type": error_type, "error": error}, elapsed


def create_summary(queue: list[dict[str, str]], results: dict[str, dict[str, Any]], attempted_this_run: int, dry_run: bool) -> dict[str, Any]:
    rows = [results[row["capture_group_id"]] for row in queue]
    counts = Counter(str(row["status"]) for row in rows)
    success_sessions = {row["session_id"] for row in rows if row["status"] in {"success", "cached_success"}}
    return {
        "queue_images": len(queue),
        "attempted_this_run": attempted_this_run,
        "status_counts": dict(sorted(counts.items())),
        "successful_wcs": counts.get("success", 0) + counts.get("cached_success", 0),
        "successful_sessions": len(success_sessions),
        "remaining_unprocessed": counts.get("unprocessed", 0),
        "dry_run": dry_run,
        "backend": "WSL local Astrometry.net only",
        "nova_fallback": False,
        "privacy": "No image is uploaded to an external service.",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    queue_path = args.queue.resolve()
    wcs_root = args.wcs_dir.resolve()
    output = args.output_dir.resolve()
    results_path = output / "plate_solve_results.csv"
    summary_path = output / "summary.json"
    if not queue_path.is_file():
        raise FileNotFoundError(f"29번 Plate Solving 대기열이 없습니다: {queue_path}")
    queue = read_csv(queue_path)
    if not queue:
        raise RuntimeError("Plate Solving 대기열이 비어 있습니다.")
    if len({row.get("capture_group_id", "") for row in queue}) != len(queue):
        raise ValueError("대기열의 capture_group_id가 비어 있거나 중복됩니다.")

    previous = load_existing(results_path)
    results = {row["capture_group_id"]: base_result(row, previous.get(row["capture_group_id"])) for row in queue}
    attempted = 0
    for index, row in enumerate(queue, 1):
        capture_id = row["capture_group_id"]
        result = results[capture_id]
        paths = product_paths(wcs_root, row)
        if paths["wcs"].is_file() and not args.force:
            result.update({
                "status": "cached_success", "wcs_path": str(paths["wcs"]),
                "report_path": str(paths["report"]), "new_fits_path": str(paths["new_fits"]),
                "corr_path": str(paths["corr"]), "error_type": "", "error": "",
            })
            continue
        if result["status"] in FINAL_FAILURES and not args.retry_failed and not args.force:
            continue
        if args.limit is not None and attempted >= args.limit:
            continue
        if args.dry_run:
            attempted += 1
            continue
        print(f"[{index:03d}/{len(queue):03d}] {capture_id}: {row['filename']}")
        status, details, elapsed = solve_one(row, paths, args)
        result.update({
            "status": status,
            "attempt_count": int(result["attempt_count"]) + 1,
            "last_attempt_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "wcs_path": str(paths["wcs"]) if paths["wcs"].is_file() else "",
            "report_path": str(paths["report"]),
            "new_fits_path": str(paths["new_fits"]) if paths["new_fits"].is_file() else "",
            "corr_path": str(paths["corr"]) if paths["corr"].is_file() else "",
            "error_type": details.get("error_type", ""),
            "error": details.get("error", ""),
        })
        attempted += 1
        print(f"  결과: {status} ({elapsed:.1f}초)")
        checkpoint(results_path, queue, results)
        write_json(summary_path, create_summary(queue, results, attempted, False))

    checkpoint(results_path, queue, results)
    summary = create_summary(queue, results, attempted, args.dry_run)
    write_json(summary_path, summary)
    print("AstroSmartphone 대표 사진 Plate Solving 배치 종료")
    print(f"이번 실행 시도: {attempted:,}장")
    print(f"누적 WCS 성공: {summary['successful_wcs']:,}/{len(queue):,}장")
    print(f"미처리: {summary['remaining_unprocessed']:,}장")
    print(f"results: {results_path}")
    print(f"summary: {summary_path}")


if __name__ == "__main__":
    main()
