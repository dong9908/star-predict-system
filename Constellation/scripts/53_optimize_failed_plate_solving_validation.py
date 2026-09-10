"""Optimize a two-stage plate-solving retry on Validation images only.

Stage 1 reuses (or runs) the broad_downsample4 result.  Only failed images are
preprocessed and sent to Stage 2, so successful images do not pay the retry
cost.  Test images are intentionally excluded from this experiment.
"""

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
from statistics import mean, median
from typing import Any

from PIL import Image, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "data" / "photo" / "Representative12"
MANIFEST = PROJECT_ROOT / "data" / "results" / "representative12_evaluation" / "dataset_manifest.csv"
STAGE52_RESULTS = PROJECT_ROOT / "data" / "results" / "plate_solving_tuning" / "tuning_results.csv"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "plate_solving_two_stage_validation"
PLATE_SCRIPT = PROJECT_ROOT / "scripts" / "48_realtime_plate_solve.py"

STAGE1 = {"timeout": 90, "scale_lower": 5, "scale_upper": 160, "downsample": 4}
RETRY_PROFILES = {
    "resize1600_downsample2": {
        "crop_top": 1.0, "max_side": 1600, "timeout": 75, "downsample": 2,
    },
    "sky85_downsample2": {
        "crop_top": 0.85, "max_side": 1600, "timeout": 75, "downsample": 2,
    },
    "sky70_downsample2": {
        "crop_top": 0.70, "max_side": 1600, "timeout": 75, "downsample": 2,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET)
    parser.add_argument("--stage52-results", type=Path, default=STAGE52_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--profiles", nargs="+", choices=sorted(RETRY_PROFILES), default=list(RETRY_PROFILES))
    parser.add_argument("--images-per-category", type=int, default=2)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def choose_images(manifest: Path, per_category: int) -> list[dict[str, str]]:
    if not manifest.is_file():
        raise FileNotFoundError(f"50번 manifest가 없습니다: {manifest}")
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(manifest):
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


def stage1_index(path: Path) -> dict[str, dict[str, str]]:
    return {
        row["sha256"]: row
        for row in read_csv(path)
        if row.get("profile") == "broad_downsample4"
    }


def run_solver(image: Path, cache_root: Path, profile: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    command = [
        sys.executable, str(PLATE_SCRIPT), str(image),
        "--output-dir", str(cache_root),
        "--timeout-seconds", str(profile["timeout"]),
        "--scale-lower", "5", "--scale-upper", "160",
        "--downsample", str(profile["downsample"]),
        "--wsl-distribution", args.wsl_distribution,
    ]
    if args.retry_failed:
        command.append("--retry-failed")
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    elapsed = round(time.monotonic() - started, 3)
    image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    result_path = cache_root / image_hash / "result.json"
    payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {}
    failure = payload.get("failure") or {}
    return {
        "status": payload.get("status", "failed"),
        "cached": payload.get("cached", False),
        "elapsed_seconds": elapsed,
        "solver_elapsed_seconds": payload.get("elapsed_seconds"),
        "failure_type": failure.get("error_type", "") if completed.returncode else "",
    }


def prepare_image(source: Path, target: Path, crop_top: float, max_side: int) -> dict[str, int]:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        original_width, original_height = image.size
        crop_height = max(1, round(original_height * crop_top))
        image = image.crop((0, 0, original_width, crop_height))
        if max(image.size) > max_side:
            scale = max_side / max(image.size)
            image = image.resize(
                (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
                Image.Resampling.LANCZOS,
            )
        image.save(target, "JPEG", quality=95, subsampling=0)
    return {
        "original_width": original_width,
        "original_height": original_height,
        "prepared_width": image.width,
        "prepared_height": image.height,
    }


def summarize(rows: list[dict[str, Any]], stage1_rows: list[dict[str, Any]], selected_count: int) -> dict[str, Any]:
    stage1_solved = sum(row["status"] == "success" for row in stage1_rows)
    report: dict[str, Any] = {
        "validation_images": selected_count,
        "test_images_used": 0,
        "stage1": {
            "profile": "broad_downsample4",
            "solved": stage1_solved,
            "solve_rate": round(stage1_solved / selected_count * 100, 2) if selected_count else 0,
        },
        "retry_profiles": {},
    }
    for profile_name in RETRY_PROFILES:
        items = [row for row in rows if row["profile"] == profile_name]
        if not items:
            continue
        retry_solved = sum(row["status"] == "success" for row in items)
        combined = stage1_solved + retry_solved
        elapsed = [float(row.get("solver_elapsed_seconds") or row["elapsed_seconds"]) for row in items]
        report["retry_profiles"][profile_name] = {
            "retried": len(items),
            "retry_solved": retry_solved,
            "retry_solve_rate": round(retry_solved / len(items) * 100, 2) if items else 0,
            "combined_solved": combined,
            "combined_solve_rate": round(combined / selected_count * 100, 2) if selected_count else 0,
            "average_retry_seconds": round(mean(elapsed), 2) if elapsed else 0,
            "median_retry_seconds": round(median(elapsed), 2) if elapsed else 0,
        }
    ranked = sorted(
        report["retry_profiles"],
        key=lambda name: (
            -report["retry_profiles"][name]["combined_solve_rate"],
            report["retry_profiles"][name]["average_retry_seconds"],
        ),
    )
    report["recommended_retry_profile"] = ranked[0] if ranked else None
    return report


def main() -> None:
    args = parse_args()
    if args.images_per_category < 1:
        raise ValueError("--images-per-category는 1 이상이어야 합니다.")
    selected = choose_images(args.manifest, args.images_per_category)
    previous = stage1_index(args.stage52_results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "split": "validation",
        "test_images_used": 0,
        "images": len(selected),
        "stage1": STAGE1,
        "retry_profiles": {name: RETRY_PROFILES[name] for name in args.profiles},
        "stage1_cache_source": str(args.stage52_results),
    }
    (args.output_dir / "experiment_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stage1_rows: list[dict[str, Any]] = []
    for row in selected:
        cached = previous.get(row["sha256"])
        if cached:
            stage1_rows.append({"sha256": row["sha256"], "status": cached.get("status", "failed")})
        else:
            if args.dry_run:
                stage1_rows.append({"sha256": row["sha256"], "status": "not_run"})
                continue
            result = run_solver(
                args.dataset_dir / row["relative_path"],
                args.output_dir / "cache" / "broad_downsample4",
                STAGE1, args,
            )
            stage1_rows.append({"sha256": row["sha256"], "status": result["status"]})

    failed_hashes = {row["sha256"] for row in stage1_rows if row["status"] != "success"}
    retry_runs = len(failed_hashes) * len(args.profiles)
    print(f"53번 2단계 Validation 최적화: 전체={len(selected)}, 1차 실패={len(failed_hashes)}, 2차 실행={retry_runs}")
    print("Test 이미지 사용: 0장")
    if args.dry_run:
        print(f"plan: {(args.output_dir / 'experiment_plan.json').resolve()}")
        return

    results_path = args.output_dir / "retry_results.csv"
    results: list[dict[str, Any]] = read_csv(results_path)
    failed_rows = [row for row in selected if row["sha256"] in failed_hashes]
    completed_count = 0
    for profile_name in args.profiles:
        profile = RETRY_PROFILES[profile_name]
        for row in failed_rows:
            completed_count += 1
            source = args.dataset_dir / row["relative_path"]
            prepared = args.output_dir / "prepared" / profile_name / f"{row['sha256']}.jpg"
            dimensions = prepare_image(source, prepared, profile["crop_top"], profile["max_side"])
            print(f"[{completed_count}/{retry_runs}] {profile_name} / {row['category']} / {source.name}")
            solved = run_solver(prepared, args.output_dir / "cache" / profile_name, profile, args)
            current = {
                "profile": profile_name,
                "category": row["category"],
                "relative_path": row["relative_path"],
                "sha256": row["sha256"],
                **dimensions,
                **solved,
            }
            results = [item for item in results if not (item["profile"] == profile_name and item["sha256"] == row["sha256"])]
            results.append(current)
            write_csv(results_path, results)

    report = summarize(results, stage1_rows, len(selected))
    report["plan"] = plan
    report_path = args.output_dir / "two_stage_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, values in report["retry_profiles"].items():
        print(f"{name}: 통합 성공률={values['combined_solve_rate']}%, 재시도 평균={values['average_retry_seconds']}초")
    print(f"추천 2차 설정: {report['recommended_retry_profile']}")
    print(f"report: {report_path.resolve()}")


if __name__ == "__main__":
    main()
