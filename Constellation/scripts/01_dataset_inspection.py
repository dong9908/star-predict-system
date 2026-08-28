"""Create a reproducible, stratified inspection sample of the image dataset."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from statistics import mean
from typing import Any

import pandas as pd
from PIL import ExifTags, Image, ImageStat


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "data" / "photo" / "AstroSmartphoneDataset"
DEFAULT_RESULTS = PROJECT_ROOT / "data" / "results"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "sample" / "sample_manifest.csv"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
FILENAME_TIME = re.compile(r"PXL_(\d{8})_(\d{9})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--sample-size", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--min-per-folder",
        type=int,
        default=20,
        help="Minimum sample count per device/resolution folder when possible",
    )
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def discover_images(dataset: Path) -> list[Path]:
    if not dataset.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {dataset}")
    return sorted(
        path
        for path in dataset.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def allocate_stratified_counts(
    groups: dict[str, list[Path]], target: int, min_per_folder: int
) -> dict[str, int]:
    total = sum(len(paths) for paths in groups.values())
    target = min(target, total)
    minimums = {name: min(len(paths), min_per_folder) for name, paths in groups.items()}
    if sum(minimums.values()) > target:
        minimums = {name: 0 for name in groups}

    counts = dict(minimums)
    remaining = target - sum(counts.values())
    capacities = {name: len(groups[name]) - counts[name] for name in groups}
    capacity_total = sum(capacities.values())
    exact_extra = {
        name: (remaining * capacities[name] / capacity_total if capacity_total else 0)
        for name in groups
    }
    for name, value in exact_extra.items():
        counts[name] += min(capacities[name], int(value))

    remaining = target - sum(counts.values())
    order = sorted(
        groups,
        key=lambda name: (
            exact_extra[name] - (counts[name] - minimums[name]),
            capacities[name],
        ),
        reverse=True,
    )
    for name in order:
        if remaining == 0:
            break
        if counts[name] < len(groups[name]):
            counts[name] += 1
            remaining -= 1
    return counts


def sample_images(
    images: list[Path], sample_size: int, seed: int, min_per_folder: int
) -> list[Path]:
    if sample_size <= 0:
        raise ValueError("sample-size must be greater than zero")
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in images:
        groups[path.parent.name].append(path)

    rng = random.Random(seed)
    counts = allocate_stratified_counts(groups, sample_size, min_per_folder)
    selected: list[Path] = []
    for name in sorted(groups):
        selected.extend(rng.sample(groups[name], counts[name]))
    return sorted(selected)


def normalize_exif_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip("\x00")
    if isinstance(value, tuple):
        return ";".join(str(normalize_exif_value(item)) for item in value)
    if isinstance(value, Fraction):
        return float(value)
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denominator = value.denominator
        return float(value.numerator / denominator) if denominator else None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def filename_datetime(name: str) -> str | None:
    match = FILENAME_TIME.search(name)
    if not match:
        return None
    try:
        return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S%f").isoformat(timespec="milliseconds")
    except ValueError:
        return None


def inspect_image(path: Path, dataset: Path) -> dict[str, Any]:
    stat = path.stat()
    with Image.open(path) as image:
        image.load()
        rgb = image.convert("RGB")
        channels = ImageStat.Stat(rgb).mean
        gray = image.convert("L")
        gray_stat = ImageStat.Stat(gray)
        exif = {
            ExifTags.TAGS.get(tag_id, str(tag_id)): normalize_exif_value(value)
            for tag_id, value in image.getexif().items()
        }
        row = {
            "relative_path": path.relative_to(dataset).as_posix(),
            "folder": path.parent.name,
            "filename": path.name,
            "extension": path.suffix.lower(),
            "file_size_bytes": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 4),
            "width": image.width,
            "height": image.height,
            "megapixels": round(image.width * image.height / 1_000_000, 3),
            "mode": image.mode,
            "format": image.format,
            "brightness_mean": round(gray_stat.mean[0], 3),
            "brightness_stddev": round(gray_stat.stddev[0], 3),
            "red_mean": round(channels[0], 3),
            "green_mean": round(channels[1], 3),
            "blue_mean": round(channels[2], 3),
            "exif_present": bool(exif),
            "camera_make": exif.get("Make"),
            "camera_model": exif.get("Model"),
            "datetime_original": exif.get("DateTimeOriginal") or exif.get("DateTime"),
            "filename_datetime": filename_datetime(path.name),
            "iso": exif.get("ISOSpeedRatings") or exif.get("PhotographicSensitivity"),
            "exposure_time": exif.get("ExposureTime"),
            "f_number": exif.get("FNumber"),
            "focal_length": exif.get("FocalLength"),
            "gps_present": "GPSInfo" in exif,
            "exif_tag_count": len(exif),
        }
    return row


def build_summary(
    images: list[Path],
    rows: list[dict[str, Any]],
    dataset: Path,
    seed: int,
    min_per_folder: int,
) -> dict[str, Any]:
    folder_counts = Counter(path.parent.name for path in images)
    sample_counts = Counter(row["folder"] for row in rows)
    dimensions = Counter(f"{row['width']}x{row['height']}" for row in rows)
    return {
        "dataset_path": str(dataset.resolve()),
        "total_images": len(images),
        "total_size_bytes": sum(path.stat().st_size for path in images),
        "sample_size": len(rows),
        "random_seed": seed,
        "minimum_per_folder": min_per_folder,
        "dataset_folder_counts": dict(sorted(folder_counts.items())),
        "sample_folder_counts": dict(sorted(sample_counts.items())),
        "sample_dimension_counts": dict(dimensions.most_common()),
        "sample_exif_present": sum(bool(row["exif_present"]) for row in rows),
        "sample_gps_present": sum(bool(row["gps_present"]) for row in rows),
        "sample_brightness_mean": round(mean(row["brightness_mean"] for row in rows), 3),
    }


def main() -> None:
    args = parse_args()
    dataset = args.dataset.resolve()
    images = discover_images(dataset)
    if not images:
        raise RuntimeError(f"No supported images found in: {dataset}")

    selected = sample_images(images, args.sample_size, args.seed, args.min_per_folder)
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(selected, start=1):
        rows.append(inspect_image(path, dataset))
        if index % 25 == 0 or index == len(selected):
            print(f"Inspected {index}/{len(selected)} images")

    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.results_dir / "image_analysis_sample.csv"
    summary_path = args.results_dir / "dataset_summary.json"

    frame = pd.DataFrame(rows)
    frame.to_csv(csv_path, index=False, encoding="utf-8-sig")
    frame[["relative_path", "folder", "filename"]].to_csv(
        args.manifest, index=False, encoding="utf-8-sig"
    )
    summary = build_summary(images, rows, dataset, args.seed, args.min_per_folder)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"CSV: {csv_path}")
    print(f"Summary: {summary_path}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
