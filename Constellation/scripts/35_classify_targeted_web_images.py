"""Classify images collected by stage 34 without modifying source files.

The classifier joins the unified source metadata, validates every image,
extracts EXIF, estimates point-source counts, detects exact/near duplicates,
and creates contact sheets for manual review.  Automatic labels are triage
labels only; ambiguous images remain ``needs_review``.
"""

from __future__ import annotations

import argparse
import hashlib
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import ExifTags, Image, ImageDraw, ImageFont, ImageOps

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "data" / "photo" / "TargetedWeb"
DEFAULT_IMAGES = DEFAULT_ROOT / "images"
DEFAULT_SOURCES = DEFAULT_ROOT / "metadata" / "sources.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "targeted_web_classification"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

ALLOWED_LABELS = [
    "valid_smartphone_night_sky",
    "valid_night_sky_device_unknown",
    "failure_negative",
    "professional_camera",
    "telescope_or_deep_sky",
    "illustration_or_chart",
    "unrelated_or_daytime",
    "too_low_resolution",
    "duplicate",
    "corrupt",
    "needs_review",
]

NIGHT_TERMS = {
    "night sky", "starry sky", "star field", "stars", "milky way", "milkyway",
    "astrophotography", "constellation", "pleiades", "jupiter", "betelgeuse",
    "aldebaran", "zeta tauri", "elnath", "hassaleh", "iota aurigae",
    "bellatrix", "taurus", "orion", "auriga", "meteor", "airglow",
}
SMARTPHONE_TERMS = {
    "smartphone", "mobile phone", "shot on iphone", "iphone", "google pixel",
    "pixel phone", "samsung galaxy", "oneplus", "xiaomi", "huawei", "oppo",
    "vivo", "motorola", "xperia", "night sight", "mobile astrophotography",
}
FAILURE_TERMS = {
    "cloudy", "clouds", "fog", "foggy", "haze", "light pollution", "city glow",
    "moon glare", "overexposed", "underexposed", "motion blur", "blurry",
    "star trail", "star trails", "obstruction", "building", "trees",
}
ILLUSTRATION_TERMS = {
    "wallpaper", "illustration", "digital art", "clip art", "render", "graphic",
    "astrology", "horoscope", "zodiac chart", "zodiac wheel", "birth chart",
    "sky map", "skymap", "stellarium screenshot", "diagram",
}
DEEP_SKY_TERMS = {
    "hubble", "james webb", "jwst", "messier", "ngc ", "nebula", "galaxy",
    "globular cluster", "deep sky", "telescope image", "observatory image",
}
UNRELATED_TERMS = {
    "museum", "cosplay", "railway", "clock tower", "fireworks", "daytime",
    "sunset", "street photography", "city night", "phone case", "book cover",
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
        help="기존 데이터와 중복 비교할 이미지 폴더(반복 지정 가능)",
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
    coefficients = cv2.dct(gray)[:8, :8].flatten()
    median = float(np.median(coefficients[1:]))
    number = 0
    for bit in coefficients > median:
        number = (number << 1) | int(bit)
    return f"{number:016x}"


def hash_distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def exif_fields(image: Image.Image) -> dict[str, str]:
    try:
        raw = image.getexif()
    except Exception:
        return {}
    fields: dict[str, str] = {}
    for key, value in raw.items():
        name = ExifTags.TAGS.get(key, str(key))
        if name in {"Make", "Model", "DateTimeOriginal", "LensModel", "Software"}:
            fields[name] = str(value).strip()
    return fields


def lightweight_star_count(image: Image.Image) -> int:
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    longest = max(gray.shape)
    if longest > 1600:
        scale = 1600 / longest
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    fine = cv2.GaussianBlur(gray, (0, 0), 1.0)
    broad = cv2.GaussianBlur(gray, (0, 0), 3.0)
    dog = cv2.subtract(fine, broad)
    median = float(np.median(dog))
    mad = float(np.median(np.abs(dog.astype(np.float32) - median)))
    threshold = max(8.0, median + 7.0 * max(mad, 1.0))
    maxima = dog == cv2.dilate(dog, np.ones((5, 5), np.uint8))
    mask = np.logical_and(maxima, dog >= threshold).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if count <= 1:
        return 0
    return int(np.count_nonzero(stats[1:, cv2.CC_STAT_AREA] <= 9))


def camera_kind(make: str, model: str, metadata_status: str, text: str) -> str:
    combined = normalize(make, model, text)
    make_value = normalize(make)
    if metadata_status == "professional_or_telescope":
        return "professional_camera"
    if metadata_status == "smartphone_probable":
        return "smartphone_probable"
    if any(token in combined for token in ("ilce", "canon eos", "dslr", "nikon d")):
        return "professional_camera"
    if has_term(combined, SMARTPHONE_TERMS) or any(maker in make_value for maker in PHONE_MAKERS):
        return "smartphone_probable"
    if any(maker in make_value for maker in CAMERA_MAKERS):
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
    if width < min_width or height < min_height:
        return "too_low_resolution", f"해상도 미달({width}x{height})"
    if has_term(text, ILLUSTRATION_TERMS):
        return "illustration_or_chart", "그림·배경화면·천문 차트 관련 메타데이터"
    if has_term(text, DEEP_SKY_TERMS):
        return "telescope_or_deep_sky", "망원경·심우주 대상 관련 메타데이터"
    if has_term(text, UNRELATED_TERMS):
        return "unrelated_or_daytime", "밤하늘 학습과 관련 없는 메타데이터"
    night = has_term(text, NIGHT_TERMS)
    failure = has_term(text, FAILURE_TERMS)
    if night and failure:
        return "failure_negative", f"밤하늘 실패 조건 메타데이터; 점광원 후보 {stars}개"
    if kind == "professional_camera" and night:
        return "professional_camera", "전문 카메라 또는 망원경 근거"
    if kind == "smartphone_probable" and night and stars >= 5:
        return "valid_smartphone_night_sky", f"스마트폰·밤하늘 근거와 점광원 후보 {stars}개"
    if night and stars >= 5:
        return "valid_night_sky_device_unknown", f"밤하늘 근거와 점광원 후보 {stars}개; 기기 미확인"
    if night and stars < 5:
        return "failure_negative", f"밤하늘 메타데이터가 있지만 점광원 후보가 {stars}개"
    if kind == "professional_camera":
        return "professional_camera", "전문 카메라 메타데이터"
    return "needs_review", f"자동 확정 근거 부족; 기기={kind}, 점광원 후보={stars}개"


def metadata_by_filename(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    return {
        str(row.get("local_filename", "")).strip(): row
        for row in rows
        if row.get("local_filename")
    }


def load_reviews(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row.get("filename", ""): row for row in read_csv(path) if row.get("filename")}


def comparison_hashes(directories: list[Path]) -> list[tuple[str, str, str]]:
    values: list[tuple[str, str, str]] = []
    for directory in directories:
        if not directory.is_dir():
            print(f"주의: 중복 비교 폴더를 찾을 수 없습니다: {directory}")
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            try:
                with Image.open(path) as image:
                    values.append((str(path), sha256_file(path), perceptual_hash(image)))
            except Exception:
                continue
    return values


def contact_sheet(rows: list[dict[str, Any]], label: str, output: Path) -> None:
    selected = [row for row in rows if row["final_label"] == label]
    if not selected:
        return
    cell_w, cell_h, columns = 360, 290, 3
    sheet = Image.new("RGB", (cell_w * columns, cell_h * math.ceil(len(selected) / columns)), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(selected):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        try:
            with Image.open(row["source_path"]) as source:
                thumbnail = ImageOps.contain(source.convert("RGB"), (340, 205))
            sheet.paste(thumbnail, (x + 10 + (340 - thumbnail.width) // 2, y + 8))
        except Exception:
            pass
        draw.text((x + 10, y + 220), row["filename"][:45], fill="white", font=font)
        draw.text(
            (x + 10, y + 238),
            f'{row["provider"]} / {row["query_group"]} / stars={row["star_candidates"]}',
            fill="#fbbf24", font=font,
        )
        draw.text((x + 10, y + 256), row["camera_kind"][:48], fill="#86efac", font=font)
        draw.text((x + 10, y + 272), row["title"][:52], fill="#93c5fd", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=88)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    images_dir = args.images_dir.resolve()
    sources_csv = args.sources_csv.resolve()
    output_dir = args.output_dir.resolve()
    if not images_dir.is_dir():
        raise FileNotFoundError(f"TargetedWeb 이미지 폴더를 찾을 수 없습니다: {images_dir}")
    if not sources_csv.is_file():
        raise FileNotFoundError(f"TargetedWeb 메타데이터를 찾을 수 없습니다: {sources_csv}")

    metadata = metadata_by_filename(sources_csv)
    review_csv = output_dir / "classification_review.csv"
    previous_reviews = load_reviews(review_csv)
    external_hashes = comparison_hashes([path.resolve() for path in args.compare_dir])
    images = sorted(
        path for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    rows: list[dict[str, Any]] = []
    seen_sha: dict[str, str] = {}
    seen_phash: list[tuple[str, str]] = []
    for index, path in enumerate(images, 1):
        source = metadata.get(path.name, {})
        width = height = stars = 0
        image_format = make = model = captured_at = lens = software = ""
        sha256 = phash = read_error = ""
        try:
            sha256 = sha256_file(path)
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                width, height = image.size
                image_format = str(image.format or "")
                exif = exif_fields(image)
                make, model = exif.get("Make", ""), exif.get("Model", "")
                captured_at = exif.get("DateTimeOriginal", "")
                lens, software = exif.get("LensModel", ""), exif.get("Software", "")
                phash = perceptual_hash(image)
                stars = lightweight_star_count(image)
        except Exception as error:
            read_error = f"{type(error).__name__}: {error}"

        # Search queries are useful evidence that an image may show the night
        # sky, but they are not evidence about the camera that created it.
        # Keep camera evidence separate to avoid labelling every result from a
        # "smartphone" query as a verified/probable smartphone photograph.
        text = normalize(
            path.name, source.get("title"), source.get("search_query"),
            source.get("query_group"), source.get("provider"), source.get("device_status"),
        )
        camera_evidence = normalize(
            path.name, source.get("title"), source.get("creator"),
            source.get("camera_make"), source.get("camera_model"),
        )
        kind = camera_kind(
            make or str(source.get("camera_make", "")),
            model or str(source.get("camera_model", "")),
            str(source.get("device_status", "")),
            camera_evidence,
        )
        automatic, reason = (
            ("corrupt", read_error)
            if read_error
            else automatic_label(text, kind, width, height, stars, args.min_width, args.min_height)
        )
        duplicate_of: str = ""
        duplicate_distance: int | str = ""
        if not read_error and sha256 in seen_sha:
            duplicate_of, duplicate_distance = seen_sha[sha256], 0
            automatic, reason = "duplicate", f"동일 SHA-256: {duplicate_of}"
        elif not read_error:
            for prior_name, prior_phash in seen_phash:
                distance = hash_distance(phash, prior_phash)
                if distance <= args.phash_distance:
                    duplicate_of, duplicate_distance = prior_name, distance
                    automatic, reason = "duplicate", f"유사 이미지 pHash 거리 {distance}: {prior_name}"
                    break
        if not read_error and not duplicate_of:
            for external_path, external_sha, external_phash in external_hashes:
                distance = 0 if sha256 == external_sha else hash_distance(phash, external_phash)
                if distance <= args.phash_distance:
                    duplicate_of, duplicate_distance = external_path, distance
                    automatic, reason = "duplicate", f"기존 데이터와 유사, pHash 거리 {distance}"
                    break
        if not read_error:
            seen_sha.setdefault(sha256, path.name)
            seen_phash.append((path.name, phash))

        previous = previous_reviews.get(path.name, {})
        review_label = previous.get("review_label", "").strip()
        if review_label not in ALLOWED_LABELS:
            review_label = ""
        final_label = review_label or automatic
        rows.append({
            "filename": path.name, "source_path": str(path),
            "provider": source.get("provider", ""), "provider_id": source.get("provider_id", ""),
            "query_group": source.get("query_group", ""), "search_query": source.get("search_query", ""),
            "title": source.get("title", ""), "creator": source.get("creator", ""),
            "license": source.get("license", ""), "license_url": source.get("license_url", ""),
            "source_page_url": source.get("source_page_url", ""),
            "metadata_device_status": source.get("device_status", ""),
            "width": width, "height": height, "image_format": image_format,
            "file_size_bytes": path.stat().st_size, "camera_make": make,
            "camera_model": model, "camera_kind": kind, "captured_at": captured_at,
            "lens_model": lens, "software": software, "star_candidates": stars,
            "sha256": sha256, "phash": phash, "duplicate_of": duplicate_of,
            "duplicate_distance": duplicate_distance, "automatic_label": automatic,
            "automatic_reason": reason, "review_label": review_label,
            "review_notes": previous.get("review_notes", ""), "final_label": final_label,
            "read_error": read_error,
        })
        print(f"[{index:03d}/{len(images):03d}] {automatic}: {path.name}")

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    write_csv(output_dir / "classification.csv", rows, fields)
    write_csv(
        review_csv, rows,
        ["filename", "provider", "query_group", "automatic_label", "automatic_reason", "review_label", "review_notes"],
    )
    counts = Counter(row["final_label"] for row in rows)
    provider_counts = Counter(row["provider"] for row in rows)
    group_counts = Counter(row["query_group"] for row in rows)
    summary = {
        "status": "completed", "total_images": len(rows),
        "source_metadata_rows": len(read_csv(sources_csv)),
        "images_with_metadata": sum(bool(row["provider"]) for row in rows),
        "counts": dict(sorted(counts.items())),
        "providers": dict(sorted(provider_counts.items())),
        "query_groups": dict(sorted(group_counts.items())),
        "manual_review_remaining": counts.get("needs_review", 0),
        "usable_positive_candidates": (
            counts.get("valid_smartphone_night_sky", 0)
            + counts.get("valid_night_sky_device_unknown", 0)
        ),
        "failure_negative_candidates": counts.get("failure_negative", 0),
        "source_images_modified": False,
        "automatic_labels_are_training_ready": False,
        "allowed_review_labels": ALLOWED_LABELS,
        "next_step": "Review contact sheets and fill review_label, then rerun stage 35.",
    }
    write_json(output_dir / "summary.json", summary)
    for label in ALLOWED_LABELS:
        contact_sheet(rows, label, output_dir / "contact_sheets" / f"{label}.jpg")

    print("TargetedWeb 분류 완료")
    for label, count in sorted(counts.items()):
        print(f"{label}: {count:,}장")
    print(f"classification: {output_dir / 'classification.csv'}")
    print(f"review: {review_csv}")
    print(f"summary: {output_dir / 'summary.json'}")
    print(f"contact_sheets: {output_dir / 'contact_sheets'}")


if __name__ == "__main__":
    main()
