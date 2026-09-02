"""Classify Openverse images before WCS labelling and YOLO dataset ingestion.

The script never moves, edits, or deletes source images.  It validates image
files, joins Openverse metadata by UUID, extracts EXIF camera information,
computes SHA-256 and perceptual hashes, and produces review contact sheets.
Automatic labels are conservative: uncertain images stay in ``needs_review``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import ExifTags, Image, ImageDraw, ImageFont, ImageOps

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "photo" / "Openverse"
DEFAULT_IMAGES = DEFAULT_ROOT / "images"
DEFAULT_SOURCES = DEFAULT_ROOT / "metadata" / "sources.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "openverse_classification"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

ALLOWED_LABELS = [
    "valid_smartphone_night_sky",
    "valid_night_sky_device_unknown",
    "professional_camera",
    "telescope_or_deep_sky",
    "illustration_or_wallpaper",
    "astrology_or_chart",
    "daytime_or_city",
    "too_low_resolution",
    "duplicate",
    "corrupt",
    "needs_review",
]

NIGHT_TERMS = {
    "night sky", "starry sky", "stars", "milky way", "milkyway",
    "astrophotography", "constellation", "pleiades", "perseus", "perseid",
    "cassiopeia", "taurus", "orion", "auriga", "aldebaran", "betelgeuse",
    "bellatrix", "jupiter", "meteor", "comet", "airglow", "zodiacal light",
}
SMARTPHONE_TERMS = {
    "smartphone", "mobile phone", "shot on iphone", "iphone", "google pixel",
    "pixel phone", "samsung galaxy", "oneplus", "xiaomi", "huawei", "oppo",
    "vivo", "night sight", "mobile astrophotography", "formed on my mobile",
}
ILLUSTRATION_TERMS = {
    "iphone background", "phone background", "wallpaper", "space dust",
    "friendly stars", "nebula explosion", "deep space background", "clip art",
    "illustration", "digital art", "graphic design", "render",
}
ASTROLOGY_TERMS = {
    "astrology", "horoscope", "zodiac chart", "zodiac wheel", "birth chart",
    "astronomical clock", "google sky map", "skymap",
}
DEEP_SKY_TERMS = {
    "hubble", "james webb", "jwst", "caldwell", "messier", "ngc ", "nebula",
    "globular cluster", "deep sky", "telescope image", "observatory image",
    "crab nebula", "ghost nebula", "sombrero galaxy",
}
UNRELATED_TERMS = {
    "museum", "citylight", "city night", "paris by night", "street photography",
    "railway", "bridge inverness", "clock tower", "oilfield", "pumpjack",
    "fireworks", "cosplay", "kit used", "daytime", "social media takeover",
}
PHONE_MAKERS = {
    "apple", "google", "samsung", "xiaomi", "huawei", "oneplus", "oppo",
    "vivo", "motorola", "sony", "lg", "nothing", "realme", "honor", "asus",
}
CAMERA_MAKERS = {
    "canon", "nikon", "fujifilm", "olympus", "panasonic", "pentax", "leica",
    "hasselblad", "phase one", "ricoh", "sigma",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES)
    parser.add_argument("--sources-csv", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--compare-dir", type=Path, action="append", default=[],
        help="Optional existing image directory to check for cross-dataset duplicates (repeatable).",
    )
    parser.add_argument("--min-width", type=int, default=500)
    parser.add_argument("--min-height", type=int, default=500)
    parser.add_argument("--phash-distance", type=int, default=5)
    return parser.parse_args()


def normalize(*values: Any) -> str:
    value = " ".join(str(item or "") for item in values).lower().replace("_", " ")
    return " ".join(value.split())


def has_term(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def perceptual_hash(image: Image.Image) -> str:
    gray = np.asarray(ImageOps.grayscale(image).resize((32, 32)), dtype=np.float32)
    transformed = cv2.dct(gray)[:8, :8]
    values = transformed.flatten()
    median = float(np.median(values[1:]))
    bits = values > median
    number = 0
    for bit in bits:
        number = (number << 1) | int(bit)
    return f"{number:016x}"


def hash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def exif_fields(image: Image.Image) -> dict[str, str]:
    try:
        raw = image.getexif()
    except Exception:
        return {}
    values: dict[str, str] = {}
    for key, value in raw.items():
        name = ExifTags.TAGS.get(key, str(key))
        if name in {"Make", "Model", "DateTimeOriginal", "LensModel", "Software"}:
            values[name] = str(value).strip()
    return values


def lightweight_star_count(image: Image.Image) -> int:
    """Return a conservative point-source count used only for triage."""
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    longest = max(gray.shape)
    if longest > 1600:
        scale = 1600 / longest
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(gray, (0, 0), 1.0)
    large = cv2.GaussianBlur(gray, (0, 0), 3.0)
    dog = cv2.subtract(small, large)
    median = float(np.median(dog))
    mad = float(np.median(np.abs(dog.astype(np.float32) - median)))
    threshold = max(8.0, median + 7.0 * max(mad, 1.0))
    maxima = dog == cv2.dilate(dog, np.ones((5, 5), np.uint8))
    points = np.logical_and(maxima, dog >= threshold)
    count, _, stats, _ = cv2.connectedComponentsWithStats(points.astype(np.uint8), 8)
    if count <= 1:
        return 0
    areas = stats[1:, cv2.CC_STAT_AREA]
    return int(np.count_nonzero(areas <= 9))


def camera_kind(make: str, model: str, text: str) -> str:
    combined = normalize(make, model, text)
    camera_model = normalize(model)
    if any(token in camera_model for token in {"ilce", "alpha", "eos", "dslr", "z 6", "z 7"}):
        return "professional_camera"
    if has_term(combined, SMARTPHONE_TERMS) or any(maker in normalize(make) for maker in PHONE_MAKERS):
        return "smartphone"
    if any(maker in normalize(make) for maker in CAMERA_MAKERS):
        return "professional_camera"
    if make or model:
        return "camera_unknown"
    return "device_unknown"


def automatic_label(
    text: str,
    kind: str,
    width: int,
    height: int,
    stars: int,
    min_width: int,
    min_height: int,
) -> tuple[str, str]:
    if width < 1 or height < 1:
        return "corrupt", "이미지 크기를 확인할 수 없음"
    if width < 320 or height < 320:
        return "too_low_resolution", f"해상도가 너무 작음({width}x{height})"
    if has_term(text, ASTROLOGY_TERMS):
        return "astrology_or_chart", "점성술·차트·Sky Map 관련 메타데이터"
    if has_term(text, ILLUSTRATION_TERMS):
        return "illustration_or_wallpaper", "배경화면·일러스트 관련 메타데이터"
    if has_term(text, DEEP_SKY_TERMS):
        return "telescope_or_deep_sky", "망원경·심우주 대상 관련 메타데이터"
    if has_term(text, UNRELATED_TERMS):
        return "daytime_or_city", "밤하늘 학습과 무관한 장면 관련 메타데이터"
    night_evidence = has_term(text, NIGHT_TERMS)
    if kind == "smartphone" and night_evidence and stars >= 5:
        return "valid_smartphone_night_sky", f"스마트폰 근거와 밤하늘 근거, 점광원 후보 {stars}개"
    if kind == "professional_camera" and night_evidence:
        return "professional_camera", "전문/일반 카메라 EXIF와 밤하늘 근거"
    if night_evidence and stars >= 5:
        if width < min_width or height < min_height:
            return "too_low_resolution", f"밤하늘 후보지만 권장 해상도 미달({width}x{height})"
        return "valid_night_sky_device_unknown", f"밤하늘 근거와 점광원 후보 {stars}개; 기기 미확인"
    if kind == "professional_camera":
        return "professional_camera", "전문/일반 카메라 EXIF 확인"
    return "needs_review", f"자동 확정 근거 부족; 기기={kind}, 점광원 후보={stars}개"


def load_metadata(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    return {str(row.get("id", "")).strip(): row for row in rows if row.get("id")}


def load_reviews(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row.get("filename", ""): row for row in read_csv(path) if row.get("filename")}


def comparison_hashes(directories: list[Path]) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    for directory in directories:
        if not directory.is_dir():
            print(f"주의: 중복 비교 폴더를 찾을 수 없습니다: {directory}")
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                with Image.open(path) as source:
                    results.append((str(path), sha256_file(path), perceptual_hash(source)))
            except Exception:
                continue
    return results


def contact_sheet(rows: list[dict[str, Any]], label: str, output: Path) -> None:
    selected = [row for row in rows if row["final_label"] == label]
    if not selected:
        return
    cell_w, cell_h, columns = 340, 270, 3
    row_count = math.ceil(len(selected) / columns)
    sheet = Image.new("RGB", (cell_w * columns, cell_h * row_count), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(selected):
        x = (index % columns) * cell_w
        y = (index // columns) * cell_h
        try:
            with Image.open(row["source_path"]) as source:
                thumb = ImageOps.contain(source.convert("RGB"), (320, 200))
            sheet.paste(thumb, (x + 10 + (320 - thumb.width) // 2, y + 8))
        except Exception:
            pass
        draw.text((x + 10, y + 214), row["filename"][:38], fill="white", font=font)
        draw.text(
            (x + 10, y + 232),
            f'{row["camera_kind"]} stars={row["star_candidates"]}',
            fill="#fbbf24",
            font=font,
        )
        draw.text((x + 10, y + 248), row["title"][:45], fill="#93c5fd", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=88)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    images_dir = args.images_dir.resolve()
    sources_csv = args.sources_csv.resolve()
    output_dir = args.output_dir.resolve()
    if not images_dir.is_dir():
        raise FileNotFoundError(f"Openverse 이미지 폴더를 찾을 수 없습니다: {images_dir}")
    if not sources_csv.is_file():
        raise FileNotFoundError(f"Openverse 메타데이터를 찾을 수 없습니다: {sources_csv}")

    metadata = load_metadata(sources_csv)
    review_csv = output_dir / "classification_review.csv"
    reviews = load_reviews(review_csv)
    external = comparison_hashes([path.resolve() for path in args.compare_dir])
    images = sorted(path for path in images_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)

    rows: list[dict[str, Any]] = []
    seen_sha: dict[str, str] = {}
    seen_phash: list[tuple[str, str]] = []
    for index, path in enumerate(images, 1):
        item_id = path.stem
        source = metadata.get(item_id, {})
        width = height = 0
        image_format = ""
        make = model = captured_at = lens_model = software = ""
        sha256 = phash = ""
        stars = 0
        error = ""
        try:
            sha256 = sha256_file(path)
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
                image_format = str(image.format or "")
                exif = exif_fields(image)
                make = exif.get("Make", "")
                model = exif.get("Model", "")
                captured_at = exif.get("DateTimeOriginal", "")
                lens_model = exif.get("LensModel", "")
                software = exif.get("Software", "")
                phash = perceptual_hash(image)
                stars = lightweight_star_count(image)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        text = normalize(path.name, source.get("title"), source.get("creator"), source.get("provider"))
        kind = camera_kind(make, model, text)
        auto, reason = (
            ("corrupt", error)
            if error
            else automatic_label(
                text, kind, width, height, stars, args.min_width, args.min_height
            )
        )
        duplicate_of = ""
        duplicate_distance: int | str = ""
        if not error and sha256 in seen_sha:
            duplicate_of, duplicate_distance = seen_sha[sha256], 0
            auto, reason = "duplicate", f"동일 SHA-256: {duplicate_of}"
        elif not error:
            for previous_name, previous_hash in seen_phash:
                distance = hash_distance(phash, previous_hash)
                if distance <= args.phash_distance:
                    duplicate_of, duplicate_distance = previous_name, distance
                    auto, reason = "duplicate", f"유사 이미지 pHash 거리 {distance}: {previous_name}"
                    break
        if not error and not duplicate_of:
            for external_path, external_sha, external_phash in external:
                distance = 0 if sha256 == external_sha else hash_distance(phash, external_phash)
                if distance <= args.phash_distance:
                    duplicate_of, duplicate_distance = external_path, distance
                    auto, reason = "duplicate", f"기존 데이터와 중복/유사, pHash 거리 {distance}"
                    break
        if not error:
            seen_sha.setdefault(sha256, path.name)
            seen_phash.append((path.name, phash))

        previous = reviews.get(path.name, {})
        review_label = previous.get("review_label", "").strip()
        if review_label and review_label not in ALLOWED_LABELS:
            review_label = ""
        final_label = review_label or auto
        rows.append({
            "item_id": item_id,
            "filename": path.name,
            "source_path": str(path),
            "title": source.get("title", ""),
            "creator": source.get("creator", ""),
            "license": source.get("license", ""),
            "license_version": source.get("license_version", ""),
            "license_url": source.get("license_url", ""),
            "source": source.get("source", ""),
            "provider": source.get("provider", ""),
            "landing_url": source.get("foreign_landing_url", ""),
            "width": width,
            "height": height,
            "image_format": image_format,
            "file_size_bytes": path.stat().st_size,
            "camera_make": make,
            "camera_model": model,
            "camera_kind": kind,
            "captured_at": captured_at,
            "lens_model": lens_model,
            "software": software,
            "star_candidates": stars,
            "sha256": sha256,
            "phash": phash,
            "duplicate_of": duplicate_of,
            "duplicate_distance": duplicate_distance,
            "automatic_label": auto,
            "automatic_reason": reason,
            "review_label": review_label,
            "review_notes": previous.get("review_notes", ""),
            "final_label": final_label,
            "read_error": error,
        })
        print(f"[{index:03d}/{len(images):03d}] {auto}: {path.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    write_csv(output_dir / "classification.csv", rows, fields)
    write_csv(review_csv, rows, ["filename", "automatic_label", "review_label", "review_notes"])
    counts = Counter(row["final_label"] for row in rows)
    camera_counts = Counter(row["camera_kind"] for row in rows)
    summary = {
        "total_images": len(rows),
        "metadata_rows": len(metadata),
        "metadata_without_image": len(set(metadata) - {path.stem for path in images}),
        "counts": dict(sorted(counts.items())),
        "camera_kinds": dict(sorted(camera_counts.items())),
        "duplicate_images": counts.get("duplicate", 0),
        "corrupt_images": counts.get("corrupt", 0),
        "manual_review_remaining": counts.get("needs_review", 0),
        "source_images_modified": False,
        "automatic_labels_are_training_ready": False,
        "next_step": "Review contact sheets and fill review_label before WCS/YOLO labelling.",
        "allowed_review_labels": ALLOWED_LABELS,
    }
    write_json(output_dir / "summary.json", summary)
    for label in ALLOWED_LABELS:
        contact_sheet(rows, label, output_dir / "contact_sheets" / f"{label}.jpg")

    print("분류 완료")
    for label, count in sorted(counts.items()):
        print(f"{label}: {count:,}장")
    print(f"classification: {output_dir / 'classification.csv'}")
    print(f"review: {review_csv}")
    print(f"summary: {output_dir / 'summary.json'}")
    print(f"contact_sheets: {output_dir / 'contact_sheets'}")


if __name__ == "__main__":
    main()
