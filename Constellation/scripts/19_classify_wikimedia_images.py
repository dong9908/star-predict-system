"""Classify collected Wikimedia images without modifying their source files."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "photo" / "WikimediaCommons"
DEFAULT_IMAGES = DEFAULT_ROOT / "images"
DEFAULT_SOURCES = DEFAULT_ROOT / "metadata" / "sources.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "wikimedia_classification"
DETECTOR = PROJECT_ROOT / "scripts" / "03_star_detection.py"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

POSITIVE_TERMS = {
    "night sky", "starry sky", "milky way", "milkyway", "astrophotography",
    "aurora", "northern lights", "stars above", "celestial", "geminid",
    "meteor", "comet", "constellation", "wynaad night sky", "sky with",
    "밤하늘", "별 사진", "星空", "天体写真", "星空 摄影", "ciel étoilé",
    "cielo estrellado", "sternenhimmel", "cielo stellato", "céu estrelado",
}
FAILURE_TERMS = {
    "cloudy night", "night clouds", "light pollution", "moon glare", "foggy",
    "blurry stars", "overexposed night", "underexposed night", "star trails",
    "aurora", "northern lights", "cielo de estrellas", "meadowland park",
}
UNRELATED_TERMS = {
    "selena gomez", "cosplay", "back panel", "railway station", "fire station",
    "capitol theatre", "fireworks", "city night view", "smokey sunset",
    "clouds and steel", "stadium", "dome 2016", "historic church",
    "goto chiron", "tasmanian aurora", "terang fajar", "bremerhaven",
    "ナゴヤドーム",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--sources-csv", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--rerun-detection", action="store_true")
    return parser.parse_args()


def normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").split())


def contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def detection_for(image: Path, item_id: str, output_dir: Path, rerun: bool) -> dict[str, Any]:
    result = output_dir / "star_detection" / item_id / f"{item_id}_stars.json"
    if not result.is_file() or rerun:
        completed = subprocess.run(
            [
                sys.executable, str(DETECTOR), str(image), "--output-dir",
                str(output_dir / "star_detection"), "--output-name", item_id,
            ],
            cwd=PROJECT_ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
        )
        if completed.returncode != 0 or not result.is_file():
            return {"detected_stars": 0, "maximum_star_limit_reached": False, "error": "star_detection_failed"}
    return json.loads(result.read_text(encoding="utf-8"))


def automatic_label(text: str, stars: int, detection_failed: bool) -> tuple[str, str]:
    if detection_failed:
        return "manual_review", "별 검출 실행 실패"
    if contains_any(text, UNRELATED_TERMS):
        return "rejected_unrelated", "제목 또는 설명에 비관련 대상 키워드가 있음"
    if contains_any(text, FAILURE_TERMS):
        return "failure_negative", "실패 조건 키워드가 있어 실패 판정 학습 후보"
    if contains_any(text, POSITIVE_TERMS):
        if stars < 7:
            return "failure_negative", f"밤하늘 관련 메타데이터가 있으나 별 후보가 {stars}개"
        return "accepted_night_sky", f"밤하늘 관련 메타데이터와 별 후보 {stars}개 확인"
    if stars < 7:
        return "rejected_unrelated", f"밤하늘 근거가 없고 별 후보가 {stars}개"
    return "manual_review", f"별 후보 {stars}개가 있지만 밤하늘 메타데이터 근거가 불충분"


def load_reviews(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row["filename"]: row for row in read_csv(path) if row.get("filename")}


def contact_sheet(rows: list[dict[str, Any]], label: str, images_dir: Path, output: Path) -> None:
    selected = [row for row in rows if row["final_label"] == label]
    if not selected:
        return
    cell_w, cell_h, columns = 320, 260, 3
    rows_count = (len(selected) + columns - 1) // columns
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows_count), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(selected):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        with Image.open(images_dir / row["filename"]) as source:
            thumb = ImageOps.contain(source.convert("RGB"), (300, 195))
        sheet.paste(thumb, (x + 10 + (300 - thumb.width) // 2, y + 8))
        title = f'{row["item_id"]} stars={row["detected_stars"]}'
        filename = row["filename"][:45]
        draw.text((x + 10, y + 208), title, fill="#fbbf24", font=font)
        draw.text((x + 10, y + 226), filename, fill="white", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=88)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    images_dir = args.images_dir.resolve()
    sources_csv = args.sources_csv.resolve()
    output_dir = args.output_dir.resolve()
    review_csv = output_dir / "classification_review.csv"
    metadata = {row.get("filename", ""): row for row in read_csv(sources_csv)}
    reviews = load_reviews(review_csv)
    images = sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
    rows: list[dict[str, Any]] = []
    for index, image in enumerate(images, 1):
        item_id = f"W{index:04d}"
        source = metadata.get(image.name, {})
        detection = detection_for(image, item_id, output_dir, args.rerun_detection)
        stars = int(detection.get("detected_stars") or 0)
        combined = normalize(" ".join([image.name, source.get("title", ""), source.get("description", ""), source.get("search_query", "")]))
        metadata_rejection = source.get("rejection_reason", "")
        if "not_verified_smartphone" in metadata_rejection:
            auto, reason = "rejected_unrelated", "스마트폰 촬영 자료로 확인되지 않음"
        else:
            auto, reason = automatic_label(combined, stars, bool(detection.get("error")))
        previous = reviews.get(image.name, {})
        review_label = previous.get("review_label", "").strip()
        final_label = review_label or auto
        rows.append({
            "item_id": item_id, "filename": image.name, "source_path": str(image),
            "automatic_label": auto, "automatic_reason": reason,
            "review_label": review_label, "final_label": final_label,
            "review_notes": previous.get("review_notes", ""),
            "detected_stars": stars,
            "star_limit_reached": bool(detection.get("maximum_star_limit_reached")),
            "camera_make": source.get("camera_make", ""), "camera_model": source.get("camera_model", ""),
            "license": source.get("license", ""), "author": source.get("author", ""),
            "file_page_url": source.get("file_page_url", ""),
            "metadata_rejection_reason": metadata_rejection,
            "detection_json": str(output_dir / "star_detection" / item_id / f"{item_id}_stars.json"),
        })
        print(f"[{index:02d}/{len(images):02d}] {item_id} {auto}: {image.name}")

    fields = list(rows[0].keys()) if rows else []
    write_csv(output_dir / "classification.csv", rows, fields)
    write_csv(review_csv, rows, ["filename", "review_label", "review_notes"])
    counts = Counter(row["final_label"] for row in rows)
    summary = {
        "total_images": len(rows), "counts": dict(sorted(counts.items())),
        "manual_review_remaining": counts.get("manual_review", 0),
        "source_images_modified": False,
        "allowed_review_labels": ["accepted_night_sky", "failure_negative", "rejected_unrelated", "manual_review"],
    }
    write_json(output_dir / "summary.json", summary)
    for label in summary["allowed_review_labels"]:
        contact_sheet(rows, label, images_dir, output_dir / "contact_sheets" / f"{label}.jpg")
    print("분류 완료")
    for label, count in sorted(counts.items()):
        print(f"{label}: {count:,}장")
    print(f"classification: {output_dir / 'classification.csv'}")
    print(f"review: {review_csv}")
    print(f"summary: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
