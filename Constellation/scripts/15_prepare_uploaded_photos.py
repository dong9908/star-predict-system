"""Prepare uploaded smartphone photos for plate solving and evaluation review."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image

from lib.io_utils import read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "data" / "photo" / "smartphone"
DEFAULT_DETECTION_DIR = PROJECT_ROOT / "data" / "results" / "smartphone_photo_inspection"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "uploaded_smartphone"
DETECTION_SCRIPT = PROJECT_ROOT / "scripts" / "03_star_detection.py"
PIPELINE_DIR = PROJECT_ROOT / "data" / "results" / "pipeline"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
EXIF_ID = {name: tag for tag, name in ExifTags.TAGS.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--detection-dir", type=Path, default=DEFAULT_DETECTION_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--review-csv",
        type=Path,
        help="사람이 판정한 quality_label/notes를 가진 CSV. 없으면 기존 output의 photo_review.csv를 재사용합니다.",
    )
    parser.add_argument("--rerun-detection", action="store_true")
    return parser.parse_args()


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def load_review(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row["filename"]: row for row in read_csv(path) if row.get("filename")}


def exif_summary(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        exif = image.getexif()
        captured = exif.get(EXIF_ID.get("DateTimeOriginal")) or exif.get(EXIF_ID.get("DateTime"))
        make = text(exif.get(EXIF_ID.get("Make")))
        model = text(exif.get(EXIF_ID.get("Model")))
        return {
            "width": image.width,
            "height": image.height,
            "captured_at": text(captured),
            "camera_make": make,
            "camera_model": model,
            # 위치 자체는 평가 준비 파일에 기록하지 않는다.
            "gps_available": bool(exif.get(EXIF_ID.get("GPSInfo"))),
        }


def parse_captured(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def ensure_detection(image: Path, detection_dir: Path, rerun: bool) -> Path:
    result = detection_dir / image.stem / f"{image.stem}_stars.json"
    if result.is_file() and not rerun:
        return result
    completed = subprocess.run(
        [
            sys.executable,
            str(DETECTION_SCRIPT),
            str(image),
            "--output-dir",
            str(detection_dir),
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if completed.returncode != 0 or not result.is_file():
        raise RuntimeError(f"별 검출 실패: {image}")
    return result


def assign_sessions(rows: list[dict[str, Any]]) -> None:
    last_by_camera: dict[str, tuple[datetime, str]] = {}
    counters: dict[str, int] = {}
    for row in sorted(rows, key=lambda item: (item["camera_id"], item["captured_at"], item["filename"])):
        camera = row["camera_id"] or "unknown"
        captured = parse_captured(row["captured_at"])
        previous = last_by_camera.get(camera)
        if captured is None:
            counters[camera] = counters.get(camera, 0) + 1
            session = f"{camera}-unknown-{counters[camera]:02d}"
        elif previous is None or captured - previous[0] > timedelta(minutes=30):
            counters[camera] = counters.get(camera, 0) + 1
            session = f"{camera}-{captured:%Y%m%d}-{counters[camera]:02d}"
        else:
            session = previous[1]
        row["session_id"] = session
        if captured is not None:
            last_by_camera[camera] = (captured, session)


def suggested_label(detected: int, limit_reached: bool) -> str:
    if detected < 7:
        return "too_few_stars"
    if detected < 35:
        return "review_needed"
    if limit_reached:
        return "good_or_false_positive_review"
    return "good_candidate"


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    detection_dir = args.detection_dir.resolve()
    output_dir = args.output_dir.resolve()
    review_path = (args.review_csv or output_dir / "photo_review.csv").resolve()
    review = load_review(review_path)
    images = sorted(path for path in input_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
    if not images:
        raise RuntimeError(f"이미지가 없습니다: {input_dir}")

    rows: list[dict[str, Any]] = []
    for image in images:
        exif = exif_summary(image)
        detection_path = ensure_detection(image, detection_dir, args.rerun_detection)
        detection = json.loads(detection_path.read_text(encoding="utf-8"))
        detected = int(detection.get("detected_stars") or 0)
        limit_reached = bool(detection.get("maximum_star_limit_reached"))
        existing = review.get(image.name, {})
        quality = text(existing.get("quality_label"))
        plate_eligible = quality == "good"
        camera_id = " ".join(part for part in (exif["camera_make"], exif["camera_model"]) if part).strip()
        pipeline_path = PIPELINE_DIR / image.stem / f"{image.stem}_pipeline.json"
        pipeline_status = "not_run"
        failure_code = ""
        predicted_constellations = ""
        if pipeline_path.is_file():
            pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
            outcome = pipeline.get("outcome") or {}
            pipeline_status = text(outcome.get("status")) or "unknown"
            failure_code = text(outcome.get("failure_code"))
            constellations = outcome.get("constellations") or []
            predicted_constellations = "|".join(str(value) for value in constellations)
        if not plate_eligible:
            ground_truth_status = "not_target"
        elif pipeline_status == "recognized":
            ground_truth_status = "wcs_label_ready"
        elif failure_code == "plate_solve_failed":
            ground_truth_status = "plate_solve_retry_needed"
        else:
            ground_truth_status = "pending_plate_solve"
        rows.append(
            {
                "filename": image.name,
                "stem": image.stem,
                "source_path": str(image),
                **exif,
                "camera_id": camera_id,
                "detected_stars": detected,
                "star_limit_reached": limit_reached,
                "automatic_hint": suggested_label(detected, limit_reached),
                "quality_label": quality,
                "review_status": "reviewed" if quality else "pending",
                "plate_solve_eligible": plate_eligible,
                "pipeline_status": pipeline_status,
                "failure_code": failure_code,
                "predicted_constellations": predicted_constellations,
                "ground_truth_status": ground_truth_status,
                "notes": text(existing.get("notes")),
                "detection_json": str(detection_path),
                "pipeline_json": str(pipeline_path) if pipeline_path.is_file() else "",
            }
        )

    assign_sessions(rows)
    fields = [
        "filename", "stem", "source_path", "width", "height", "captured_at",
        "camera_make", "camera_model", "camera_id", "gps_available", "session_id",
        "detected_stars", "star_limit_reached", "automatic_hint", "quality_label",
        "review_status", "plate_solve_eligible", "pipeline_status", "failure_code",
        "predicted_constellations", "ground_truth_status", "notes", "detection_json", "pipeline_json",
    ]
    write_csv(output_dir / "photo_manifest.csv", rows, fields)
    if not review_path.is_file():
        write_csv(review_path, rows, ["filename", "quality_label", "notes"])
    queue = [row for row in rows if row["plate_solve_eligible"]]
    write_csv(
        output_dir / "plate_solve_queue.csv",
        queue,
        ["filename", "stem", "source_path", "session_id", "captured_at", "camera_model", "gps_available", "detected_stars", "pipeline_status", "failure_code", "ground_truth_status"],
    )
    counts: dict[str, int] = {}
    for row in rows:
        label = row["quality_label"] or "pending"
        counts[label] = counts.get(label, 0) + 1
    summary = {
        "input_photos": len(rows),
        "reviewed": sum(row["review_status"] == "reviewed" for row in rows),
        "plate_solve_queue": len(queue),
        "independent_sessions": len({row["session_id"] for row in rows}),
        "eligible_independent_sessions": len({row["session_id"] for row in queue}),
        "recognized": sum(row["pipeline_status"] == "recognized" for row in rows),
        "plate_solve_retry_needed": sum(row["ground_truth_status"] == "plate_solve_retry_needed" for row in rows),
        "quality_counts": counts,
        "privacy": "GPS 좌표는 저장하지 않고 존재 여부만 기록합니다.",
    }
    write_json(output_dir / "summary.json", summary)
    print(f"사진: {len(rows):,}장")
    print(f"검토 완료: {summary['reviewed']:,}장")
    print(f"Plate Solving 대기: {len(queue):,}장")
    print(f"독립 촬영 세션: {summary['independent_sessions']:,}개")
    print(f"성공 후보 독립 세션: {summary['eligible_independent_sessions']:,}개")
    print(f"manifest: {output_dir / 'photo_manifest.csv'}")
    print(f"review: {review_path}")
    print(f"queue: {output_dir / 'plate_solve_queue.csv'}")


if __name__ == "__main__":
    main()
