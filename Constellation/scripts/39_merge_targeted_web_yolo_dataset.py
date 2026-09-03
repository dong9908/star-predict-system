"""Merge stage-38 approved TargetedWeb labels into the current YOLO dataset.

All approved TargetedWeb samples are added to train only. The existing
validation and independent test splits are copied unchanged so model-to-model
comparisons remain valid. Exact image duplicates are rejected by SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_astro_8"
DEFAULT_STAGE37 = PROJECT_ROOT / "data" / "results" / "targeted_web_wcs_labels"
DEFAULT_REVIEW = PROJECT_ROOT / "data" / "results" / "targeted_web_label_review"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_astro_targeted_8"
SPLITS = ("train", "validation", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dataset", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--stage37-dir", type=Path, default=DEFAULT_STAGE37)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--link-mode", choices=("hardlink", "copy", "symlink"), default="hardlink")
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
        target.unlink()
    if mode == "hardlink":
        os.link(source, target)
    elif mode == "symlink":
        target.symlink_to(source)
    else:
        shutil.copy2(source, target)
    return "created"


def parse_label(path: Path, class_count: int, allow_empty: bool) -> tuple[Counter[int], list[str]]:
    counts: Counter[int] = Counter()
    errors: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 5:
            errors.append(f"line_{line_number}_columns")
            continue
        try:
            class_id = int(parts[0])
            values = [float(value) for value in parts[1:]]
        except ValueError:
            errors.append(f"line_{line_number}_number")
            continue
        if not 0 <= class_id < class_count:
            errors.append(f"line_{line_number}_class")
        if not all(0 <= value <= 1 for value in values) or values[2] <= 0 or values[3] <= 0:
            errors.append(f"line_{line_number}_range")
        counts[class_id] += 1
    if not counts and not allow_empty:
        errors.append("empty_label_not_allowed")
    return counts, errors


def classes_from_yaml(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    return [
        line.split(":", 1)[1].strip()
        for line in lines
        if line.strip()[:1].isdigit() and ":" in line
    ]


def dataset_yaml(output: Path, classes: list[str]) -> str:
    lines = [
        f"path: {output.as_posix()}",
        "train: images/train",
        "val: images/validation",
        "test: images/test",
        f"nc: {len(classes)}",
        "names:",
    ]
    lines.extend(f"  {index}: {name}" for index, name in enumerate(classes))
    return "\n".join(lines) + "\n"


def images_for_split(base: Path, split: str) -> list[Path]:
    folder = base / "images" / split
    if not folder.is_dir():
        raise FileNotFoundError(f"기존 이미지 폴더가 없습니다: {folder}")
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    base, stage37 = args.base_dataset.resolve(), args.stage37_dir.resolve()
    review, output = args.review_dir.resolve(), args.output_dir.resolve()
    required = [
        base / "dataset.yaml",
        stage37 / "manifest.csv",
        review / "summary.json",
        review / "accepted_labels",
    ]
    for path in required:
        if not path.exists():
            raise FileNotFoundError(f"필수 입력이 없습니다: {path}")
    if output == base:
        raise ValueError("출력 데이터셋은 기존 데이터셋과 달라야 합니다.")

    review_summary = json.loads((review / "summary.json").read_text(encoding="utf-8"))
    if not review_summary.get("training_ready"):
        raise RuntimeError("38번 검토가 끝나지 않았습니다. pending 판정을 모두 처리하세요.")
    if int(review_summary.get("accepted_objects", 0)) <= 0:
        raise RuntimeError("38번에서 승인된 객체가 없습니다.")

    classes = classes_from_yaml(base / "dataset.yaml")
    if len(classes) != 8:
        raise ValueError(f"기존 dataset.yaml에서 8개 클래스를 읽지 못했습니다: {classes}")

    base_index_path = base / "dataset_index.csv"
    base_index = {
        (row.get("split", ""), row.get("sample_id", "")): row
        for row in read_csv(base_index_path)
    } if base_index_path.is_file() else {}
    manifests = {row["item_id"]: row for row in read_csv(stage37 / "manifest.csv")}
    accepted_labels = sorted((review / "accepted_labels").glob("*.txt"))

    rows: list[dict[str, Any]] = []
    links: Counter[str] = Counter()
    class_objects: Counter[tuple[str, int]] = Counter()
    class_images: Counter[tuple[str, int]] = Counter()
    source_counts: Counter[str] = Counter()
    known_hashes: dict[str, str] = {}

    def add_sample(
        sample_id: str,
        split: str,
        source_name: str,
        image: Path,
        label: Path,
        background: bool,
        source_page_url: str = "",
        license_name: str = "",
        creator: str = "",
    ) -> None:
        counts, errors = parse_label(label, len(classes), allow_empty=background)
        if errors:
            raise ValueError(f"YOLO 라벨 오류 {label}: {'|'.join(errors)}")
        image_target = output / "images" / split / f"{sample_id}{image.suffix.lower()}"
        label_target = output / "labels" / split / f"{sample_id}.txt"
        links[materialize(image, image_target, args.link_mode, args.replace_existing)] += 1
        links[materialize(label, label_target, args.link_mode, args.replace_existing)] += 1
        for class_id, count in counts.items():
            class_objects[(split, class_id)] += count
            class_images[(split, class_id)] += 1
        source_counts[source_name] += 1
        rows.append(
            {
                "sample_id": sample_id,
                "split": split,
                "dataset_source": source_name,
                "image_path": str(image_target),
                "label_path": str(label_target),
                "source_image": str(image),
                "source_label": str(label),
                "object_count": sum(counts.values()),
                "class_ids": "|".join(str(value) for value in sorted(counts)),
                "background": background,
                "sha256": file_sha256(image),
                "source_page_url": source_page_url,
                "license": license_name,
                "creator": creator,
                "link_mode": args.link_mode,
            }
        )

    print("기존 데이터셋을 연결하고 SHA-256 중복을 확인하는 중...")
    for split in SPLITS:
        for image in images_for_split(base, split):
            label = base / "labels" / split / f"{image.stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(f"기존 라벨이 없습니다: {label}")
            digest = file_sha256(image)
            known_hashes.setdefault(digest, f"{split}/{image.name}")
            old = base_index.get((split, image.stem), {})
            add_sample(
                image.stem,
                split,
                old.get("dataset_source", "base_existing"),
                image,
                label,
                not bool(label.read_text(encoding="utf-8-sig").strip()),
                old.get("source_page_url", ""),
                old.get("license", ""),
                old.get("creator", ""),
            )

    added: list[dict[str, Any]] = []
    skipped_duplicates: list[dict[str, Any]] = []
    for label in accepted_labels:
        item_id = label.stem
        manifest = manifests.get(item_id)
        if not manifest:
            raise KeyError(f"37번 manifest에서 승인 항목을 찾을 수 없습니다: {item_id}")
        image = Path(manifest["image_path"])
        if not image.is_file():
            raise FileNotFoundError(f"TargetedWeb 사진이 없습니다: {image}")
        background = not bool(label.read_text(encoding="utf-8-sig").strip())
        digest = file_sha256(image)
        if digest in known_hashes:
            skipped_duplicates.append(
                {
                    "item_id": item_id,
                    "source_image": str(image),
                    "duplicate_of": known_hashes[digest],
                    "sha256": digest,
                }
            )
            continue
        sample_id = f"targeted_{item_id}"
        add_sample(
            sample_id,
            "train",
            "targeted_web_reviewed",
            image,
            label,
            background,
            manifest.get("source_page_url", ""),
            manifest.get("license", ""),
            manifest.get("creator", ""),
        )
        known_hashes[digest] = f"train/{sample_id}{image.suffix.lower()}"
        added.append(rows[-1])

    output.mkdir(parents=True, exist_ok=True)
    (output / "dataset.yaml").write_text(dataset_yaml(output, classes), encoding="utf-8")
    write_csv(output / "dataset_index.csv", rows, list(rows[0].keys()))
    write_csv(output / "targeted_web_added.csv", added, list(rows[0].keys()))
    duplicate_fields = ["item_id", "source_image", "duplicate_of", "sha256"]
    write_csv(output / "targeted_web_duplicates_skipped.csv", skipped_duplicates, duplicate_fields)
    distribution = []
    for split in SPLITS:
        for class_id, class_name in enumerate(classes):
            distribution.append(
                {
                    "split": split,
                    "class_id": class_id,
                    "class_name": class_name,
                    "objects": class_objects[(split, class_id)],
                    "images_with_class": class_images[(split, class_id)],
                }
            )
    write_csv(output / "class_distribution.csv", distribution, list(distribution[0].keys()))
    split_counts = Counter(row["split"] for row in rows)
    targeted_objects: Counter[int] = Counter()
    for row in added:
        counts, _ = parse_label(Path(row["label_path"]), len(classes), allow_empty=truthy(row["background"]))
        targeted_objects.update(counts)
    summary = {
        "status": "completed",
        "output_dataset": str(output),
        "base_dataset": str(base),
        "classes": classes,
        "split_counts": dict(split_counts),
        "source_counts": dict(source_counts),
        "targeted_reviewed_labels": len(accepted_labels),
        "targeted_added": len(added),
        "targeted_positive": sum(not truthy(row["background"]) for row in added),
        "targeted_background": sum(truthy(row["background"]) for row in added),
        "targeted_duplicates_skipped": len(skipped_duplicates),
        "targeted_objects_by_class": {
            classes[class_id]: targeted_objects[class_id] for class_id in range(len(classes))
        },
        "targeted_split": "train_only",
        "validation_unchanged": True,
        "test_unchanged": True,
        "exact_duplicate_check": "sha256_across_all_splits",
        "link_mode": args.link_mode,
        "link_status": dict(links),
        "source_datasets_modified": False,
    }
    write_json(output / "summary.json", summary)
    print("TargetedWeb YOLO 데이터셋 병합 완료")
    print(
        f"추가: {len(added)}장 (양성 {summary['targeted_positive']}, "
        f"음성 {summary['targeted_background']})"
    )
    print(f"중복 제외: {len(skipped_duplicates)}장")
    print(
        f"전체 Train/Validation/Test: "
        f"{split_counts['train']}/{split_counts['validation']}/{split_counts['test']}"
    )
    print(f"dataset: {output / 'dataset.yaml'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
