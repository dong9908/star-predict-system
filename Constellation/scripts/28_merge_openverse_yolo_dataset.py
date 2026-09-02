"""Merge reviewed Openverse WCS labels into the existing 8-class YOLO dataset.

The source MobilTelesco dataset is never modified.  Its train/validation/test
split is preserved exactly, while accepted Openverse samples are added only to
train.  This keeps the original validation and test sets comparable with the
previous model.  Hardlinks are used by default to avoid duplicating images.
"""

from __future__ import annotations

import argparse
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from lib.io_utils import as_bool, configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_8"
DEFAULT_ACCEPTED = PROJECT_ROOT / "data" / "results" / "openverse_wcs_labels" / "accepted_manifest.csv"
DEFAULT_CLASSIFICATION = PROJECT_ROOT / "data" / "results" / "openverse_classification" / "classification.csv"
DEFAULT_CLASSES = PROJECT_ROOT / "data" / "processed" / "mobiltelesco" / "classes_8_classes.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_8"
SPLITS = ("train", "validation", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dataset", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--accepted-manifest", type=Path, default=DEFAULT_ACCEPTED)
    parser.add_argument("--openverse-classification", type=Path, default=DEFAULT_CLASSIFICATION)
    parser.add_argument("--classes", type=Path, default=DEFAULT_CLASSES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--link-mode", choices=("hardlink", "copy", "symlink"), default="hardlink")
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def materialize(source: Path, target: Path, mode: str, replace: bool) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        try:
            if os.path.samefile(source, target):
                return "reused"
        except OSError:
            pass
        if not replace:
            if target.stat().st_size == source.stat().st_size:
                return "reused_existing"
            raise FileExistsError(f"대상 파일이 이미 존재합니다: {target}. --replace-existing을 사용하세요.")
        if target.is_dir():
            raise IsADirectoryError(target)
        target.unlink()
    if mode == "hardlink":
        os.link(source, target)
    elif mode == "symlink":
        target.symlink_to(source)
    else:
        shutil.copy2(source, target)
    return "created"


def parse_yolo_label(path: Path, class_count: int, allow_empty: bool) -> tuple[Counter[int], list[str]]:
    counts: Counter[int] = Counter()
    errors: list[str] = []
    text = path.read_text(encoding="utf-8-sig")
    for line_number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 5:
            errors.append(f"line_{line_number}_columns")
            continue
        try:
            class_id = int(parts[0])
            x, y, width, height = (float(value) for value in parts[1:])
        except ValueError:
            errors.append(f"line_{line_number}_number")
            continue
        if not 0 <= class_id < class_count:
            errors.append(f"line_{line_number}_class")
        if not all(0.0 <= value <= 1.0 for value in (x, y, width, height)):
            errors.append(f"line_{line_number}_range")
        if width <= 0 or height <= 0:
            errors.append(f"line_{line_number}_size")
        counts[class_id] += 1
    if not counts and not allow_empty:
        errors.append("empty_label_not_allowed")
    return counts, errors


def yaml_text(output_dir: Path, classes: list[str]) -> str:
    lines = [
        f"path: {output_dir.as_posix()}",
        "train: images/train",
        "val: images/validation",
        "test: images/test",
        f"nc: {len(classes)}",
        "names:",
    ]
    lines.extend(f"  {index}: {name}" for index, name in enumerate(classes))
    return "\n".join(lines) + "\n"


def source_images(base: Path, split: str) -> list[Path]:
    directory = base / "images" / split
    if not directory.is_dir():
        raise FileNotFoundError(f"기존 YOLO 이미지 폴더가 없습니다: {directory}")
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    base = args.base_dataset.resolve()
    accepted_path = args.accepted_manifest.resolve()
    classification_path = args.openverse_classification.resolve()
    classes_path = args.classes.resolve()
    output = args.output_dir.resolve()
    for required in (accepted_path, classification_path, classes_path):
        if not required.is_file():
            raise FileNotFoundError(f"필수 파일을 찾을 수 없습니다: {required}")
    if output == base:
        raise ValueError("출력 폴더는 기존 데이터셋과 달라야 합니다.")

    classes = [line.strip() for line in classes_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(classes) != 8:
        raise ValueError(f"8개 클래스가 필요하지만 {len(classes)}개입니다: {classes}")
    accepted = read_csv(accepted_path)
    if not accepted:
        raise RuntimeError("승인된 Openverse 데이터가 없습니다.")
    if any(row.get("review_decision") != "accept" for row in accepted):
        raise ValueError("accepted_manifest.csv에 accept가 아닌 행이 포함돼 있습니다.")
    classification = {row.get("item_id", ""): row for row in read_csv(classification_path)}

    rows: list[dict[str, Any]] = []
    distribution: Counter[tuple[str, int]] = Counter()
    images_per_class: Counter[tuple[str, int]] = Counter()
    source_counts: Counter[str] = Counter()
    link_counts: Counter[str] = Counter()

    for split in SPLITS:
        for image in source_images(base, split):
            label = base / "labels" / split / f"{image.stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(f"기존 YOLO 라벨이 없습니다: {label}")
            counts, errors = parse_yolo_label(label, len(classes), allow_empty=True)
            if errors:
                raise ValueError(f"기존 라벨 오류 {label}: {'|'.join(errors)}")
            image_target = output / "images" / split / image.name
            label_target = output / "labels" / split / label.name
            link_counts[materialize(image, image_target, args.link_mode, args.replace_existing)] += 1
            link_counts[materialize(label, label_target, args.link_mode, args.replace_existing)] += 1
            for class_id, count in counts.items():
                distribution[(split, class_id)] += count
                images_per_class[(split, class_id)] += 1
            source_counts["mobiltelesco"] += 1
            rows.append({
                "sample_id": image.stem, "split": split, "dataset_source": "mobiltelesco",
                "image_path": str(image_target), "label_path": str(label_target),
                "source_image": str(image), "source_label": str(label),
                "object_count": sum(counts.values()),
                "class_ids": "|".join(str(value) for value in sorted(counts)),
                "background": not bool(counts), "item_id": "", "title": "",
                "creator": "", "license": "", "license_url": "", "landing_url": "",
                "review_decision": "existing_dataset", "link_mode": args.link_mode,
            })

    existing_ids = {row["sample_id"] for row in rows}
    for row in accepted:
        item_id = row["item_id"]
        sample_id = f"ov_{item_id}"
        if sample_id in existing_ids:
            raise RuntimeError(f"샘플 ID가 중복됩니다: {sample_id}")
        image = Path(row["image_path"])
        label = Path(row["label_path"])
        if not image.is_file():
            raise FileNotFoundError(f"Openverse 이미지가 없습니다: {image}")
        if not label.is_file():
            raise FileNotFoundError(f"Openverse YOLO 라벨이 없습니다: {label}")
        background = as_bool(row.get("background_verified"))
        counts, errors = parse_yolo_label(label, len(classes), allow_empty=background)
        if errors:
            raise ValueError(f"Openverse 라벨 오류 {label}: {'|'.join(errors)}")
        if background and counts:
            raise ValueError(f"음성 이미지에 객체 라벨이 있습니다: {label}")
        if not background and not counts:
            raise ValueError(f"양성 이미지의 라벨이 비어 있습니다: {label}")
        image_target = output / "images" / "train" / f"{sample_id}{image.suffix.lower()}"
        label_target = output / "labels" / "train" / f"{sample_id}.txt"
        link_counts[materialize(image, image_target, args.link_mode, args.replace_existing)] += 1
        link_counts[materialize(label, label_target, args.link_mode, args.replace_existing)] += 1
        for class_id, count in counts.items():
            distribution[("train", class_id)] += count
            images_per_class[("train", class_id)] += 1
        metadata = classification.get(item_id, {})
        source_counts["openverse"] += 1
        rows.append({
            "sample_id": sample_id, "split": "train", "dataset_source": "openverse",
            "image_path": str(image_target), "label_path": str(label_target),
            "source_image": str(image), "source_label": str(label),
            "object_count": sum(counts.values()),
            "class_ids": "|".join(str(value) for value in sorted(counts)),
            "background": background, "item_id": item_id, "title": row.get("title", ""),
            "creator": metadata.get("creator", ""), "license": metadata.get("license", ""),
            "license_url": metadata.get("license_url", ""),
            "landing_url": metadata.get("landing_url", ""),
            "review_decision": row.get("review_decision", ""), "link_mode": args.link_mode,
        })

    output.mkdir(parents=True, exist_ok=True)
    (output / "dataset.yaml").write_text(yaml_text(output, classes), encoding="utf-8")
    fields = list(rows[0].keys())
    write_csv(output / "dataset_index.csv", rows, fields)
    openverse_rows = [row for row in rows if row["dataset_source"] == "openverse"]
    write_csv(output / "openverse_added.csv", openverse_rows, fields)

    distribution_rows = []
    for split in SPLITS:
        for class_id, class_name in enumerate(classes):
            distribution_rows.append({
                "split": split, "class_id": class_id, "class_name": class_name,
                "objects": distribution[(split, class_id)],
                "images_with_class": images_per_class[(split, class_id)],
            })
    write_csv(
        output / "class_distribution.csv", distribution_rows,
        ["split", "class_id", "class_name", "objects", "images_with_class"],
    )
    split_counts = Counter(row["split"] for row in rows)
    summary = {
        "output_dataset": str(output), "classes": classes,
        "split_counts": dict(split_counts), "source_counts": dict(source_counts),
        "openverse_added": len(openverse_rows),
        "openverse_positive": sum(not row["background"] for row in openverse_rows),
        "openverse_background": sum(bool(row["background"]) for row in openverse_rows),
        "validation_test_unchanged": True,
        "link_mode": args.link_mode, "link_status": dict(link_counts),
        "source_datasets_modified": False,
    }
    write_json(output / "summary.json", summary)
    print("YOLO 데이터셋 병합 완료")
    print(f"기존 MobilTelesco: {source_counts['mobiltelesco']:,}장")
    print(f"추가 Openverse: {source_counts['openverse']:,}장 (양성 {summary['openverse_positive']}, 음성 {summary['openverse_background']})")
    print(f"Train/Validation/Test: {split_counts['train']:,}/{split_counts['validation']:,}/{split_counts['test']:,}")
    print("Validation/Test 변경: 없음")
    print(f"dataset_yaml: {output / 'dataset.yaml'}")
    print(f"dataset_index: {output / 'dataset_index.csv'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
