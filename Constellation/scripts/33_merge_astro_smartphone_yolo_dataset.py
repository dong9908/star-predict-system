"""Merge reviewed AstroSmartphone WCS labels into the current 8-class YOLO set.

The existing MobilTelesco+Openverse dataset is copied by hardlink and remains
unchanged.  AstroSmartphone candidates are assigned by the stage-31 observing-
session split: train candidates go only to train and test candidates go only to
test.  Verified WCS negatives receive an empty YOLO label.  Images containing a
target but having no accepted object are excluded rather than mislabeled as
background.
"""

from __future__ import annotations

import argparse
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_8"
DEFAULT_COVERAGE = PROJECT_ROOT / "data" / "results" / "astro_smartphone_target_coverage" / "image_target_coverage.csv"
DEFAULT_REVIEW = PROJECT_ROOT / "data" / "results" / "astro_smartphone_label_review"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_openverse_astro_8"
SPLITS = ("train", "validation", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dataset", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--review-dir", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--link-mode", choices=("hardlink", "copy", "symlink"), default="hardlink")
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


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


def dataset_yaml(output: Path, classes: list[str]) -> str:
    lines = [
        f"path: {output.as_posix()}", "train: images/train", "val: images/validation",
        "test: images/test", f"nc: {len(classes)}", "names:",
    ]
    lines.extend(f"  {index}: {name}" for index, name in enumerate(classes))
    return "\n".join(lines) + "\n"


def base_images(base: Path, split: str) -> list[Path]:
    folder = base / "images" / split
    if not folder.is_dir():
        raise FileNotFoundError(f"기존 이미지 폴더가 없습니다: {folder}")
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    base, coverage_path = args.base_dataset.resolve(), args.coverage.resolve()
    review, output = args.review_dir.resolve(), args.output_dir.resolve()
    summary_path = review / "summary.json"
    labels_dir = review / "accepted_labels"
    for required in (coverage_path, summary_path, base / "dataset.yaml"):
        if not required.is_file():
            raise FileNotFoundError(f"필수 파일이 없습니다: {required}")
    if not labels_dir.is_dir():
        raise FileNotFoundError(f"승인 라벨 폴더가 없습니다: {labels_dir}")
    import json
    review_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not review_summary.get("training_ready"):
        raise RuntimeError("32번 검토가 끝나지 않았습니다. pending 판정을 모두 처리하세요.")
    if int(review_summary.get("accepted_objects", 0)) <= 0:
        raise RuntimeError("승인된 객체가 없습니다.")
    if output == base:
        raise ValueError("출력 데이터셋은 기존 데이터셋과 달라야 합니다.")

    yaml_lines = (base / "dataset.yaml").read_text(encoding="utf-8-sig").splitlines()
    classes = [line.split(":", 1)[1].strip() for line in yaml_lines if line.strip()[:1].isdigit() and ":" in line]
    if len(classes) != 8:
        raise ValueError(f"기존 dataset.yaml에서 8개 클래스를 읽지 못했습니다: {classes}")

    rows: list[dict[str, Any]] = []
    links: Counter[str] = Counter()
    class_objects: Counter[tuple[str, int]] = Counter()
    class_images: Counter[tuple[str, int]] = Counter()
    source_counts: Counter[str] = Counter()

    def add_row(sample_id: str, split: str, source_name: str, image: Path, label: Path, background: bool, session_id: str = "") -> None:
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
        rows.append({
            "sample_id": sample_id, "split": split, "dataset_source": source_name,
            "session_id": session_id, "image_path": str(image_target), "label_path": str(label_target),
            "source_image": str(image), "source_label": str(label), "object_count": sum(counts.values()),
            "class_ids": "|".join(str(value) for value in sorted(counts)), "background": background,
            "link_mode": args.link_mode,
        })

    for split in SPLITS:
        for image in base_images(base, split):
            label = base / "labels" / split / f"{image.stem}.txt"
            if not label.is_file():
                raise FileNotFoundError(f"기존 라벨이 없습니다: {label}")
            add_row(image.stem, split, "base_mobiltelesco_openverse", image, label, not bool(label.read_text(encoding="utf-8-sig").strip()))

    accepted = {path.stem: path for path in labels_dir.glob("*.txt")}
    coverage = read_csv(coverage_path)
    astro_sessions: dict[str, set[str]] = {"train": set(), "test": set()}
    excluded = 0
    temp_empty = output / ".build" / "empty.txt"
    temp_empty.parent.mkdir(parents=True, exist_ok=True)
    temp_empty.write_text("", encoding="utf-8")
    for row in coverage:
        capture_id = row["capture_group_id"]
        label = accepted.get(capture_id)
        negative = truthy(row.get("verified_negative_candidate"))
        if label is None and not negative:
            excluded += 1
            continue
        split = "test" if row.get("split_candidate") == "test_candidate" else "train"
        session_id = row.get("session_id", "")
        astro_sessions[split].add(session_id)
        image = Path(row["source_path"])
        if not image.is_file():
            raise FileNotFoundError(f"AstroSmartphone 사진이 없습니다: {image}")
        add_row(f"astro_{capture_id}", split, "astro_smartphone", image, label or temp_empty, label is None, session_id)

    overlap = astro_sessions["train"] & astro_sessions["test"]
    if overlap:
        raise RuntimeError(f"AstroSmartphone 세션 누수가 발견됐습니다: {sorted(overlap)[:5]}")
    if temp_empty.exists():
        temp_empty.unlink()
    try:
        temp_empty.parent.rmdir()
    except OSError:
        pass

    output.mkdir(parents=True, exist_ok=True)
    (output / "dataset.yaml").write_text(dataset_yaml(output, classes), encoding="utf-8")
    write_csv(output / "dataset_index.csv", rows, list(rows[0].keys()))
    astro_rows = [row for row in rows if row["dataset_source"] == "astro_smartphone"]
    write_csv(output / "astro_smartphone_added.csv", astro_rows, list(rows[0].keys()))
    distribution = []
    for split in SPLITS:
        for class_id, class_name in enumerate(classes):
            distribution.append({"split": split, "class_id": class_id, "class_name": class_name, "objects": class_objects[(split, class_id)], "images_with_class": class_images[(split, class_id)]})
    write_csv(output / "class_distribution.csv", distribution, list(distribution[0].keys()))
    split_counts = Counter(row["split"] for row in rows)
    summary = {
        "output_dataset": str(output), "classes": classes, "split_counts": dict(split_counts),
        "source_counts": dict(source_counts), "astro_added": len(astro_rows),
        "astro_positive": sum(not truthy(row["background"]) for row in astro_rows),
        "astro_background": sum(truthy(row["background"]) for row in astro_rows),
        "astro_train": sum(row["split"] == "train" for row in astro_rows),
        "astro_test": sum(row["split"] == "test" for row in astro_rows),
        "astro_train_sessions": len(astro_sessions["train"]), "astro_test_sessions": len(astro_sessions["test"]),
        "astro_session_overlap": 0, "excluded_target_images_without_accepted_label": excluded,
        "base_validation_unchanged": True, "link_mode": args.link_mode,
        "link_status": dict(links), "source_datasets_modified": False,
    }
    write_json(output / "summary.json", summary)
    print("AstroSmartphone YOLO 데이터셋 병합 완료")
    print(f"추가: {len(astro_rows)}장 (양성 {summary['astro_positive']}, 음성 {summary['astro_background']})")
    print(f"Astro Train/Test: {summary['astro_train']}/{summary['astro_test']}장")
    print(f"세션 누수: {summary['astro_session_overlap']}")
    print(f"전체 Train/Validation/Test: {split_counts['train']}/{split_counts['validation']}/{split_counts['test']}")
    print(f"dataset: {output / 'dataset.yaml'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
