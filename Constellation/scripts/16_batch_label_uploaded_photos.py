"""Plate-solve reviewed smartphone photos and build a resumable ground-truth set."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from lib.io_utils import as_bool, read_csv, read_json, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "evaluation" / "uploaded_smartphone" / "photo_manifest.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "uploaded_smartphone" / "labeled"
PIPELINE_SCRIPT = PROJECT_ROOT / "scripts" / "10_end_to_end_pipeline.py"
PIPELINE_ROOT = PROJECT_ROOT / "data" / "results" / "pipeline"
FINAL_ROOT = PROJECT_ROOT / "data" / "results" / "final_recognition"
OVERLAY_ROOT = PROJECT_ROOT / "data" / "results" / "wcs_constellation_overlay"
WCS_ROOT = PROJECT_ROOT / "data" / "wcs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--all-frames", action="store_true", help="세션 대표가 아닌 good 사진 전체 처리")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--plate-timeout-seconds", type=int, default=300)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--force-plate-solving", action="store_true")
    parser.add_argument("--pause-seconds", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def select_targets(rows: list[dict[str, str]], all_frames: bool) -> list[dict[str, str]]:
    eligible = [
        row for row in rows
        if row.get("quality_label") == "good" and as_bool(row.get("plate_solve_eligible"))
    ]
    eligible.sort(
        key=lambda row: (
            row.get("session_id", ""),
            -int(row.get("detected_stars") or 0),
            row.get("filename", ""),
        )
    )
    if all_frames:
        return eligible
    representatives: dict[str, dict[str, str]] = {}
    for row in eligible:
        representatives.setdefault(row.get("session_id") or row["stem"], row)
    return list(representatives.values())


def artifact_paths(stem: str) -> dict[str, Path]:
    return {
        "pipeline": PIPELINE_ROOT / stem / f"{stem}_pipeline.json",
        "final": FINAL_ROOT / stem / f"{stem}_final.json",
        "overlay": OVERLAY_ROOT / stem / f"{stem}_wcs_constellations.json",
        "wcs": WCS_ROOT / stem / f"{stem}.wcs",
    }


def outcome_for(row: dict[str, str]) -> dict[str, Any]:
    stem = row["stem"]
    paths = artifact_paths(stem)
    pipeline = read_json(paths["pipeline"], {}) or {}
    final = read_json(paths["final"], {}) or {}
    outcome = pipeline.get("outcome") or {}
    decision = final.get("decision") or {}
    failure = final.get("failure_assessment") or {}
    constellations = outcome.get("constellations") or []
    if not constellations:
        candidate = final.get("candidate") or {}
        if decision.get("status") == "confirmed" and candidate.get("iau"):
            constellations = [candidate["iau"]]
    recognized = outcome.get("status") == "recognized" and paths["wcs"].is_file()
    return {
        "pipeline_status": outcome.get("status") or "not_run",
        "failure_code": "" if recognized else (outcome.get("failure_code") or failure.get("primary_code") or ""),
        "recognized": recognized,
        "constellations": [str(value) for value in constellations],
        "pipeline_json": str(paths["pipeline"]) if paths["pipeline"].is_file() else "",
        "final_json": str(paths["final"]) if paths["final"].is_file() else "",
        "overlay_json": str(paths["overlay"]) if paths["overlay"].is_file() else "",
        "wcs": str(paths["wcs"]) if paths["wcs"].is_file() else "",
    }


def run_pipeline(row: dict[str, str], args: argparse.Namespace, log_path: Path) -> int:
    command = [
        sys.executable,
        str(PIPELINE_SCRIPT),
        row["source_path"],
        "--plate-timeout-seconds",
        str(args.plate_timeout_seconds),
    ]
    if args.force_plate_solving:
        command.append("--force-plate-solving")
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        completed.stdout + ("\n[stderr]\n" + completed.stderr if completed.stderr else ""),
        encoding="utf-8",
    )
    return completed.returncode


def main() -> None:
    args = parse_args()
    manifest = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    rows = load_csv(manifest)
    targets = select_targets(rows, args.all_frames)
    if args.limit is not None:
        targets = targets[: max(0, args.limit)]
    output_dir.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []
    for index, row in enumerate(targets, start=1):
        before = outcome_for(row)
        should_run = not before["recognized"]
        if before["pipeline_status"] == "failed" and not args.retry_failed:
            should_run = False
        action = "dry_run" if args.dry_run else "run"
        if not should_run:
            action = "reuse" if before["recognized"] else "skipped_failed"
        print(f"[{index}/{len(targets)}] {row['filename']} - {action}")
        return_code: int | None = None
        if should_run and not args.dry_run:
            return_code = run_pipeline(
                row,
                args,
                output_dir / "logs" / f"{row['stem']}.log",
            )
            if args.pause_seconds > 0 and index < len(targets):
                time.sleep(args.pause_seconds)
        result = outcome_for(row)
        attempts.append(
            {
                "sample_id": row["stem"],
                "filename": row["filename"],
                "session_id": row.get("session_id", ""),
                "source_path": row["source_path"],
                "quality_label": row.get("quality_label", ""),
                "captured_at": row.get("captured_at", ""),
                "camera_model": row.get("camera_model", ""),
                "gps_available": row.get("gps_available", ""),
                "detected_stars": row.get("detected_stars", ""),
                "action": action,
                "return_code": "" if return_code is None else return_code,
                "pipeline_status": result["pipeline_status"],
                "failure_code": result["failure_code"],
                "recognized": result["recognized"],
                "expected_iau": "|".join(result["constellations"]),
                "verification": "wcs_confirmed" if result["recognized"] else "not_verified",
                "pipeline_json": result["pipeline_json"],
                "final_json": result["final_json"],
                "overlay_json": result["overlay_json"],
                "wcs": result["wcs"],
            }
        )

    fields = [
        "sample_id", "filename", "session_id", "source_path", "quality_label",
        "captured_at", "camera_model", "gps_available", "detected_stars", "action",
        "return_code", "pipeline_status", "failure_code", "recognized", "expected_iau",
        "verification", "pipeline_json", "final_json", "overlay_json", "wcs",
    ]
    write_csv(output_dir / "batch_status.csv", attempts, fields)
    verified = [row for row in attempts if row["recognized"]]
    write_csv(output_dir / "ground_truth.csv", verified, fields)
    summary = {
        "mode": "all_good_frames" if args.all_frames else "one_representative_per_session",
        "targets": len(targets),
        "attempted_now": sum(row["action"] == "run" for row in attempts),
        "processed_results": sum(row["pipeline_status"] != "not_run" for row in attempts),
        "recognized": len(verified),
        "failed": sum(row["pipeline_status"] == "failed" for row in attempts),
        "pending": sum(row["pipeline_status"] == "not_run" for row in attempts),
        "completion_rate": round(len(verified) / len(targets), 4) if targets else 0.0,
        "privacy": "원본 EXIF/GPS를 보존하되 Nova에는 07단계의 메타데이터 제거 임시 복사본만 업로드합니다.",
    }
    write_json(output_dir / "summary.json", summary)
    print(f"대상: {len(targets)}장 / WCS 정답 완료: {len(verified)}장")
    print(f"batch_status: {output_dir / 'batch_status.csv'}")
    print(f"ground_truth: {output_dir / 'ground_truth.csv'}")
    print(f"summary: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
