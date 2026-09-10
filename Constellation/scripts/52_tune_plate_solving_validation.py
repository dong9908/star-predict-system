"""Compare plate-solving profiles on a balanced Validation subset.

Each profile uses its own SHA cache, so results from different solver settings
never overwrite one another. Test images are intentionally excluded.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "data" / "photo" / "Representative12"
MANIFEST = PROJECT_ROOT / "data" / "results" / "representative12_evaluation" / "dataset_manifest.csv"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "plate_solving_tuning"
PLATE_SCRIPT = PROJECT_ROOT / "scripts" / "48_realtime_plate_solve.py"

PROFILES = {
    "baseline": {"timeout": 90, "scale_lower": 20, "scale_upper": 120, "downsample": None},
    "fast_downsample4": {"timeout": 60, "scale_lower": 20, "scale_upper": 120, "downsample": 4},
    "broad_downsample4": {"timeout": 90, "scale_lower": 5, "scale_upper": 160, "downsample": 4},
    "fast_downsample8": {"timeout": 60, "scale_lower": 20, "scale_upper": 120, "downsample": 8},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--profiles", nargs="+", choices=sorted(PROFILES), default=list(PROFILES))
    parser.add_argument("--images-per-category", type=int, default=2)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def choose_images(manifest: Path, per_category: int) -> list[dict[str, str]]:
    if not manifest.is_file():
        raise FileNotFoundError(f"50번 manifest가 없습니다: {manifest}")
    with manifest.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if (
            row.get("split") == "validation"
            and row.get("category") != "Negative"
            and as_bool(row.get("valid"))
            and not as_bool(row.get("duplicate"))
        ):
            groups[row["category"]].append(row)
    selected: list[dict[str, str]] = []
    for category in sorted(groups):
        selected.extend(sorted(groups[category], key=lambda row: row["sha256"])[:per_category])
    return selected


def run_one(row: dict[str, str], profile_name: str, args: argparse.Namespace) -> dict[str, Any]:
    profile = PROFILES[profile_name]
    image = args.dataset_dir / row["relative_path"]
    cache_root = args.output_dir / "cache" / profile_name
    result_path = cache_root / row["sha256"] / "result.json"
    command = [
        sys.executable, str(PLATE_SCRIPT), str(image),
        "--output-dir", str(cache_root),
        "--timeout-seconds", str(profile["timeout"]),
        "--scale-lower", str(profile["scale_lower"]),
        "--scale-upper", str(profile["scale_upper"]),
        "--wsl-distribution", args.wsl_distribution,
    ]
    if profile["downsample"]:
        command.extend(["--downsample", str(profile["downsample"])])
    if args.retry_failed:
        command.append("--retry-failed")
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    elapsed = round(time.monotonic() - started, 3)
    payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    return {
        "profile": profile_name,
        "category": row["category"],
        "relative_path": row["relative_path"],
        "sha256": row["sha256"],
        "status": payload.get("status", "failed"),
        "cached": payload.get("cached", False),
        "elapsed_seconds": elapsed,
        "solver_elapsed_seconds": payload.get("elapsed_seconds"),
        "failure_type": (payload.get("failure") or {}).get("error_type", "") if completed.returncode else "",
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_existing_results(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {"profiles": {}}
    for profile_name in PROFILES:
        items = [row for row in rows if row["profile"] == profile_name]
        if not items:
            continue
        solved = [row for row in items if row["status"] == "success"]
        elapsed = [
            float(row.get("solver_elapsed_seconds") or row["elapsed_seconds"])
            for row in items
        ]
        report["profiles"][profile_name] = {
            "images": len(items),
            "solved": len(solved),
            "solve_rate": round(len(solved) / len(items) * 100, 2),
            "average_seconds": round(mean(elapsed), 2),
            "median_seconds": round(median(elapsed), 2),
            "total_minutes": round(sum(elapsed) / 60, 2),
        }
    ranked = sorted(
        report["profiles"],
        key=lambda name: (
            -report["profiles"][name]["solve_rate"],
            report["profiles"][name]["average_seconds"],
        ),
    )
    report["recommended_profile"] = ranked[0] if ranked else None
    return report


def main() -> None:
    args = parse_args()
    if args.images_per_category < 1:
        raise ValueError("--images-per-category는 1 이상이어야 합니다.")
    selected = choose_images(args.manifest, args.images_per_category)
    plan = {
        "split": "validation",
        "test_images_used": 0,
        "profiles": {name: PROFILES[name] for name in args.profiles},
        "images": len(selected),
        "runs": len(selected) * len(args.profiles),
        "categories": sorted({row["category"] for row in selected}),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "experiment_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"52번 Validation 최적화: 이미지={plan['images']}, 설정={len(args.profiles)}, 실행={plan['runs']}")
    print("Test 이미지 사용: 0장")
    if args.dry_run:
        print(f"plan: {(args.output_dir / 'experiment_plan.json').resolve()}")
        return

    results_path = args.output_dir / "tuning_results.csv"
    results = read_existing_results(results_path)
    total = plan["runs"]
    completed_in_run = 0
    for profile_name in args.profiles:
        for row in selected:
            completed_in_run += 1
            print(f"[{completed_in_run}/{total}] {profile_name} / {row['category']} / {Path(row['relative_path']).name}")
            current = run_one(row, profile_name, args)
            key = (profile_name, row["sha256"])
            results = [item for item in results if (item["profile"], item["sha256"]) != key]
            results.append(current)
            write_csv(results_path, results)

    report = summarize(results)
    report["plan"] = plan
    report_path = args.output_dir / "tuning_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, values in report["profiles"].items():
        print(f"{name}: 성공률={values['solve_rate']}%, 평균={values['average_seconds']}초")
    print(f"추천 설정: {report['recommended_profile']}")
    print(f"report: {report_path.resolve()}")


if __name__ == "__main__":
    main()
