"""Audit and evaluate the Representative12 dataset with cached plate solving.

The parent folder is treated as the expected label. Positive images are plate
solved by stage 48 and, unless --skip-overlay is used, checked by the WCS
constellation overlay. Negative images measure false-positive behavior.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "photo" / "Representative12"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "representative12_evaluation"
REALTIME_ROOT = PROJECT_ROOT / "data" / "results" / "realtime_plate_solving"
PLATE_SCRIPT = PROJECT_ROOT / "scripts" / "48_realtime_plate_solve.py"
DETECTION_SCRIPT = PROJECT_ROOT / "scripts" / "03_star_detection.py"
OVERLAY_SCRIPT = PROJECT_ROOT / "scripts" / "11_wcs_constellation_overlay.py"
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
EXPECTED_IAU = {
    "Auriga": "Aur", "Cassiopeia": "Cas", "Cygnus": "Cyg",
    "Eridanus": "Eri", "Gemini": "Gem", "Leo": "Leo",
    "Orion": "Ori", "Sagittarius": "Sgr", "Scorpius": "Sco",
    "Taurus": "Tau", "UrsaMajor": "UMa", "UrsaMinor": "UMi",
    "Negative": "",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--category", choices=sorted(EXPECTED_IAU), help="한 폴더만 평가")
    parser.add_argument("--split", choices=("train", "validation", "test"), help="해당 분할만 처리")
    parser.add_argument("--limit", type=int, help="품질 통과 이미지 중 최대 처리 수")
    parser.add_argument("--audit-only", action="store_true", help="품질·중복·분할만 생성")
    parser.add_argument("--skip-overlay", action="store_true", help="Plate Solving 성공률만 평가")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--scale-lower", type=float, default=20.0)
    parser.add_argument("--scale-upper", type=float, default=120.0)
    parser.add_argument("--wsl-distribution", default="Ubuntu")
    parser.add_argument("--minimum-side", type=int, default=600)
    parser.add_argument("--train-percent", type=int, default=70)
    parser.add_argument("--validation-percent", type=int, default=15)
    return parser.parse_args()


def validate(args: argparse.Namespace) -> None:
    if not args.dataset_dir.is_dir():
        raise FileNotFoundError(f"Representative12 폴더가 없습니다: {args.dataset_dir}")
    if args.timeout_seconds < 30:
        raise ValueError("--timeout-seconds는 30 이상이어야 합니다.")
    if args.train_percent < 1 or args.validation_percent < 1:
        raise ValueError("분할 비율은 1 이상이어야 합니다.")
    if args.train_percent + args.validation_percent >= 100:
        raise ValueError("train + validation 비율은 100 미만이어야 합니다.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def deterministic_split(digest: str, train: int, validation: int) -> str:
    bucket = int(digest[:8], 16) % 100
    if bucket < train:
        return "train"
    if bucket < train + validation:
        return "validation"
    return "test"


def inspect_image(path: Path, minimum_side: int) -> dict[str, Any]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            transposed = ImageOps.exif_transpose(image)
            width, height = transposed.size
    except (UnidentifiedImageError, OSError, ValueError) as error:
        return {"valid": False, "width": 0, "height": 0, "quality_issue": type(error).__name__}
    issue = "" if min(width, height) >= minimum_side else "low_resolution"
    return {"valid": not issue, "width": width, "height": height, "quality_issue": issue}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def build_manifest(args: argparse.Namespace) -> list[dict[str, Any]]:
    categories = [args.category] if args.category else list(EXPECTED_IAU)
    files: list[tuple[str, Path]] = []
    for category in categories:
        root = args.dataset_dir / category
        if root.is_dir():
            files.extend((category, path) for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED)
    files.sort(key=lambda item: (item[0], str(item[1]).casefold()))

    first_by_hash: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for index, (category, path) in enumerate(files, 1):
        digest = sha256_file(path)
        inspection = inspect_image(path, args.minimum_side)
        relative = path.relative_to(args.dataset_dir).as_posix()
        duplicate_of = first_by_hash.get(digest, "")
        first_by_hash.setdefault(digest, relative)
        rows.append({
            "index": index,
            "category": category,
            "expected_iau": EXPECTED_IAU[category],
            "is_negative": category == "Negative",
            "relative_path": relative,
            "sha256": digest,
            "bytes": path.stat().st_size,
            "width": inspection["width"],
            "height": inspection["height"],
            "valid": inspection["valid"],
            "quality_issue": inspection["quality_issue"],
            "duplicate": bool(duplicate_of),
            "duplicate_of": duplicate_of,
            "split": deterministic_split(digest, args.train_percent, args.validation_percent),
        })
    return rows


def run_command(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout, check=False,
    )


def plate_solve(path: Path, args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    digest = sha256_file(path)
    result_path = REALTIME_ROOT / digest / "result.json"
    was_cached = result_path.is_file() and not args.retry_failed
    command = [
        sys.executable, str(PLATE_SCRIPT), str(path),
        "--output-dir", str(REALTIME_ROOT),
        "--timeout-seconds", str(args.timeout_seconds),
        "--scale-lower", str(args.scale_lower), "--scale-upper", str(args.scale_upper),
        "--wsl-distribution", args.wsl_distribution,
    ]
    if args.retry_failed:
        command.append("--retry-failed")
    try:
        completed = run_command(command, PROJECT_ROOT, args.timeout_seconds + 60)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "failure": {"error_type": "BatchTimeout"}}, False
    if not result_path.is_file():
        return {
            "status": "failed",
            "failure": {"error_type": "MissingResult", "message": (completed.stderr or completed.stdout)[-500:]},
        }, False
    return json.loads(result_path.read_text(encoding="utf-8")), was_cached


def evaluate_overlay(path: Path, digest: str, wcs_path: Path, output: Path) -> tuple[list[str], str]:
    detection_root = output / "star_detection"
    overlay_root = output / "wcs_overlay"
    staged = output / "_inputs" / f"{digest}{path.suffix.lower()}"
    staged.parent.mkdir(parents=True, exist_ok=True)
    if not staged.is_file():
        staged.write_bytes(path.read_bytes())
    detection_json = detection_root / digest / f"{digest}_stars.json"
    overlay_json = overlay_root / digest / f"{digest}_wcs_constellations.json"
    if not overlay_json.is_file():
        commands = [
            [sys.executable, str(DETECTION_SCRIPT), str(staged), "--output-dir", str(detection_root),
             "--sky-fraction", "1.0", "--max-stars", "250"],
            [sys.executable, str(OVERLAY_SCRIPT), str(staged), "--wcs", str(wcs_path),
             "--star-detection", str(detection_json), "--output-dir", str(overlay_root),
             "--max-constellations", "12"],
        ]
        for command in commands:
            try:
                completed = run_command(command, PROJECT_ROOT, 45)
            except subprocess.TimeoutExpired:
                return [], "OverlayTimeout"
            if completed.returncode != 0:
                return [], "OverlayProcessError"
    if not overlay_json.is_file():
        return [], "MissingOverlayResult"
    payload = json.loads(overlay_json.read_text(encoding="utf-8"))
    return [str(item.get("iau")) for item in payload.get("selected", []) if item.get("iau")], ""


def summarize(manifest: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    unique_valid = [row for row in manifest if row["valid"] and not row["duplicate"]]
    evaluated = [row for row in results if row["plate_status"]]
    positives = [row for row in evaluated if not row["is_negative"]]
    negatives = [row for row in evaluated if row["is_negative"]]
    overlay_positives = [row for row in positives if row["overlay_evaluated"]]
    overlay_negatives = [row for row in negatives if row["overlay_evaluated"]]

    per_category: dict[str, dict[str, Any]] = {}
    for category in EXPECTED_IAU:
        rows = [row for row in evaluated if row["category"] == category]
        if not rows:
            continue
        solved = sum(row["plate_status"] == "success" for row in rows)
        checked = [row for row in rows if row["overlay_evaluated"]]
        hits = sum(bool(row["expected_hit"]) for row in checked)
        per_category[category] = {
            "images": len(rows), "plate_solved": solved,
            "plate_solve_rate": round(solved / len(rows) * 100, 2),
            "overlay_checked": len(checked), "expected_hits": hits,
            "expected_hit_rate": round(hits / len(checked) * 100, 2) if checked else None,
        }

    return {
        "dataset": {
            "images": len(manifest), "unique_valid_images": len(unique_valid),
            "duplicates": sum(row["duplicate"] for row in manifest),
            "invalid_or_low_resolution": sum(not row["valid"] for row in manifest),
            "split_counts": dict(Counter(row["split"] for row in unique_valid)),
        },
        "evaluation": {
            "processed": len(evaluated),
            "plate_solved": sum(row["plate_status"] == "success" for row in evaluated),
            "plate_solve_rate": round(sum(row["plate_status"] == "success" for row in evaluated) / len(evaluated) * 100, 2) if evaluated else None,
            "positive_overlay_checked": len(overlay_positives),
            "positive_expected_hits": sum(bool(row["expected_hit"]) for row in overlay_positives),
            "positive_top12_hit_rate": round(sum(bool(row["expected_hit"]) for row in overlay_positives) / len(overlay_positives) * 100, 2) if overlay_positives else None,
            "negative_overlay_checked": len(overlay_negatives),
            "negative_false_positives": sum(bool(row["predicted_iau"]) for row in overlay_negatives),
            "negative_false_positive_rate": round(sum(bool(row["predicted_iau"]) for row in overlay_negatives) / len(overlay_negatives) * 100, 2) if overlay_negatives else None,
            "average_seconds": round(sum(float(row["elapsed_seconds"] or 0) for row in evaluated) / len(evaluated), 3) if evaluated else None,
            "failure_types": dict(Counter(row["failure_type"] for row in evaluated if row["failure_type"])),
        },
        "per_category": per_category,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    validate(args)
    output = args.output_dir.resolve()
    manifest = build_manifest(args)
    write_csv(output / "dataset_manifest.csv", manifest)
    write_json(output / "dataset_manifest.json", manifest)
    print(
        f"50번 데이터 점검: 전체={len(manifest)}, "
        f"중복={sum(row['duplicate'] for row in manifest)}, "
        f"품질제외={sum(not row['valid'] for row in manifest)}"
    )

    candidates = [row for row in manifest if row["valid"] and not row["duplicate"]]
    if args.split:
        candidates = [row for row in candidates if row["split"] == args.split]
    if args.limit is not None:
        candidates = candidates[:max(0, args.limit)]
    results: list[dict[str, Any]] = []
    if not args.audit_only:
        for number, item in enumerate(candidates, 1):
            source = args.dataset_dir / item["relative_path"]
            print(f"[{number}/{len(candidates)}] {item['category']} / {source.name}")
            started = time.monotonic()
            plate, cached = plate_solve(source, args)
            plate_status = str(plate.get("status") or "failed")
            predicted: list[str] = []
            overlay_error = ""
            overlay_evaluated = False
            if plate_status == "success" and not args.skip_overlay:
                relative_wcs = str((plate.get("artifacts") or {}).get("wcs") or "")
                wcs_path = REALTIME_ROOT / relative_wcs
                if wcs_path.is_file():
                    predicted, overlay_error = evaluate_overlay(source, item["sha256"], wcs_path, output)
                    overlay_evaluated = not overlay_error
                else:
                    overlay_error = "MissingWcsArtifact"
            failure = plate.get("failure") or {}
            results.append({
                **item,
                "plate_status": plate_status,
                "cached": cached,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "solver_elapsed_seconds": plate.get("elapsed_seconds"),
                "failure_type": failure.get("error_type") or (overlay_error if plate_status == "success" else "PlateSolveFailed"),
                "overlay_evaluated": overlay_evaluated,
                "predicted_iau": "|".join(predicted),
                "expected_hit": bool(item["expected_iau"] and item["expected_iau"] in predicted),
            })
            write_csv(output / "evaluation_results.csv", results)

    report = summarize(manifest, results)
    report["parameters"] = {
        "audit_only": args.audit_only, "skip_overlay": args.skip_overlay,
        "category": args.category, "split": args.split,
        "limit": args.limit, "timeout_seconds": args.timeout_seconds,
        "scale_lower": args.scale_lower, "scale_upper": args.scale_upper,
        "minimum_side": args.minimum_side,
    }
    write_json(output / "evaluation_report.json", report)
    summary = [
        "대표 별자리 12종 평가 결과",
        f"전체 이미지: {report['dataset']['images']}",
        f"유효한 고유 이미지: {report['dataset']['unique_valid_images']}",
        f"중복: {report['dataset']['duplicates']}",
        f"품질 제외: {report['dataset']['invalid_or_low_resolution']}",
        f"처리 완료: {report['evaluation']['processed']}",
        f"Plate Solving 성공률: {report['evaluation']['plate_solve_rate']}",
        f"대표 12종 Top-12 포함률: {report['evaluation']['positive_top12_hit_rate']}",
        f"Negative 오검출률: {report['evaluation']['negative_false_positive_rate']}",
    ]
    (output / "evaluation_summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    print(f"manifest: {output / 'dataset_manifest.csv'}")
    print(f"report: {output / 'evaluation_report.json'}")


if __name__ == "__main__":
    main()
