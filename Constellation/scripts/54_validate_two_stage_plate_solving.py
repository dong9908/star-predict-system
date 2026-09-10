"""Validate the production-shaped two-stage solver on Validation images only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "photo" / "Representative12"
MANIFEST = ROOT / "data" / "results" / "representative12_evaluation" / "dataset_manifest.csv"
OUTPUT = ROOT / "data" / "results" / "plate_solving_two_stage_integrated_validation"
SOLVER = ROOT / "scripts" / "48_realtime_plate_solve.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--images-per-category", type=int, default=2)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def truth(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def choose(path: Path, limit: int) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(path):
        if (row.get("split") == "validation" and row.get("category") != "Negative"
                and truth(row.get("valid")) and not truth(row.get("duplicate"))):
            grouped[row["category"]].append(row)
    return [row for name in sorted(grouped) for row in sorted(grouped[name], key=lambda x: x["sha256"])[:limit]]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if args.images_per_category < 1:
        raise ValueError("--images-per-category는 1 이상이어야 합니다.")
    selected = choose(args.manifest, args.images_per_category)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "stage": 54, "split": "validation", "test_images_used": 0,
        "images": len(selected),
        "stage1": {"scale_lower": 5, "scale_upper": 160, "downsample": 4, "timeout": 90},
        "stage2": {"profile": "sky85_downsample2", "max_side": 1600, "downsample": 2, "timeout": 75},
    }
    (args.output_dir / "validation_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"54번 통합 2단계 Validation: 이미지={len(selected)}, Test 이미지=0장")
    if args.dry_run:
        print(f"plan: {(args.output_dir / 'validation_plan.json').resolve()}")
        return

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(selected, 1):
        source = args.dataset_dir / item["relative_path"]
        print(f"[{index}/{len(selected)}] {item['category']} / {source.name}")
        command = [
            sys.executable, str(SOLVER), str(source), "--output-dir", str(args.output_dir / "cache"),
            "--timeout-seconds", "90", "--scale-lower", "5", "--scale-upper", "160",
            "--downsample", "4", "--two-stage-retry", "--second-stage-timeout-seconds", "75",
            "--wsl-distribution", args.wsl_distribution,
        ]
        if args.retry_failed:
            command.append("--retry-failed")
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        elapsed = round(time.monotonic() - started, 3)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        result_path = args.output_dir / "cache" / digest / "result.json"
        payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
        rows.append({
            "category": item["category"], "relative_path": item["relative_path"], "sha256": digest,
            "status": payload.get("status", "failed"), "solved_stage": payload.get("solved_stage", ""),
            "elapsed_seconds": elapsed, "solver_elapsed_seconds": payload.get("elapsed_seconds", ""),
            "returncode": completed.returncode,
        })
        write_csv(args.output_dir / "validation_results.csv", rows)

    solved1 = sum(row["status"] == "success" and row["solved_stage"] == 1 for row in rows)
    solved2 = sum(row["status"] == "success" and row["solved_stage"] == 2 for row in rows)
    report = {
        **plan, "stage1_solved": solved1, "stage2_recovered": solved2,
        "combined_solved": solved1 + solved2,
        "combined_solve_rate": round((solved1 + solved2) / len(rows) * 100, 2) if rows else 0,
        "average_total_seconds": round(mean(float(row["solver_elapsed_seconds"] or 0) for row in rows), 2) if rows else 0,
    }
    report_path = args.output_dir / "validation_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"1차 성공={solved1}, 2차 추가 성공={solved2}, 통합 성공률={report['combined_solve_rate']}%")
    print(f"report: {report_path.resolve()}")


if __name__ == "__main__":
    main()
