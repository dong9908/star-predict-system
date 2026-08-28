"""Materialize the MobilTelesco 8-class manifest as a YOLO dataset."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from lib.io_utils import as_bool, configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "data" / "processed" / "mobiltelesco" / "manifest_supervised_8_classes.csv"
)
DEFAULT_CLASSES = PROJECT_ROOT / "data" / "processed" / "mobiltelesco" / "classes_8_classes.txt"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "yolo_mobiltelesco_8"
SPLIT_DIR = {"train": "train", "validation": "validation", "test": "test"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--classes", type=Path, default=DEFAULT_CLASSES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--link-mode", choices=("hardlink", "copy", "symlink"), default="copy")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace existing materialized files (also breaks old hardlinks safely)",
    )
    return parser.parse_args()


def sample_id(relative_path: str) -> str:
    digest = hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:14]
    return f"m8_{digest}"


def materialize(source: Path, target: Path, mode: str, replace_existing: bool) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        try:
            same_file = os.path.samefile(source, target)
            if same_file and not (mode == "copy" and replace_existing):
                return "reused"
        except OSError:
            same_file = False
        if not replace_existing:
            raise FileExistsError(
                f"Target already exists: {target}. Use --replace-existing to rebuild it."
            )
        if mode == "copy":
            # Copy to a sibling temporary path first. os.replace then changes only
            # the dataset directory entry, safely breaking a pre-existing hardlink.
            temporary = target.with_name(f".{target.name}.copying")
            if temporary.exists() or temporary.is_symlink():
                temporary.unlink()
            shutil.copy2(source, temporary)
            os.replace(temporary, target)
            return "replaced"
        target.unlink()
    if mode == "hardlink":
        os.link(source, target)
    elif mode == "symlink":
        target.symlink_to(source)
    else:
        shutil.copy2(source, target)
    return "created"


def parse_label(path: Path, class_count: int) -> tuple[Counter[int], list[str]]:
    counts: Counter[int] = Counter()
    errors: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        fields = raw.split()
        if len(fields) != 5:
            errors.append(f"line_{line_number}_columns")
            continue
        try:
            class_id = int(fields[0])
            coords = [float(value) for value in fields[1:]]
        except ValueError:
            errors.append(f"line_{line_number}_number")
            continue
        if not 0 <= class_id < class_count:
            errors.append(f"line_{line_number}_class")
        if any(value < 0 or value > 1 for value in coords):
            errors.append(f"line_{line_number}_range")
        if coords[2] <= 0 or coords[3] <= 0:
            errors.append(f"line_{line_number}_size")
        counts[class_id] += 1
    if not counts:
        errors.append("empty_label")
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


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    manifest_path = args.manifest.resolve()
    classes_path = args.classes.resolve()
    output_dir = args.output_dir.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    if not classes_path.is_file():
        raise FileNotFoundError(f"Classes file not found: {classes_path}")

    classes = [line.strip() for line in classes_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(classes) != 8:
        raise ValueError(f"Expected 8 classes, found {len(classes)}: {classes_path}")
    rows = read_csv(manifest_path)
    if not rows:
        raise RuntimeError("Manifest is empty.")

    seen_ids: set[str] = set()
    capture_splits: dict[str, set[str]] = defaultdict(set)
    session_splits: dict[str, set[str]] = defaultdict(set)
    output_rows: list[dict[str, Any]] = []
    class_objects: dict[tuple[str, int], int] = Counter()
    class_images: dict[tuple[str, int], int] = Counter()
    link_status: Counter[str] = Counter()

    for index, row in enumerate(rows, 1):
        split = row.get("split", "")
        if split not in SPLIT_DIR:
            raise ValueError(f"Unknown split '{split}' in {row.get('relative_path')}")
        if row.get("label_scheme") != "8_classes" or not as_bool(row.get("label_valid")):
            raise ValueError(f"Invalid 8-class manifest row: {row.get('relative_path')}")
        image_source = Path(row["absolute_path"])
        label_source = Path(row["label_path"])
        if not image_source.is_file():
            raise FileNotFoundError(f"Image missing: {image_source}")
        if not label_source.is_file():
            raise FileNotFoundError(f"Label missing: {label_source}")

        identifier = sample_id(row["relative_path"])
        if identifier in seen_ids:
            raise RuntimeError(f"Generated sample ID collision: {identifier}")
        seen_ids.add(identifier)
        image_target = output_dir / "images" / SPLIT_DIR[split] / f"{identifier}{image_source.suffix.lower()}"
        label_target = output_dir / "labels" / SPLIT_DIR[split] / f"{identifier}.txt"
        link_status[materialize(image_source, image_target, args.link_mode, args.replace_existing)] += 1
        link_status[materialize(label_source, label_target, args.link_mode, args.replace_existing)] += 1

        counts, errors = parse_label(label_source, len(classes))
        if errors:
            raise ValueError(f"Invalid YOLO label {label_source}: {'|'.join(errors)}")
        for class_id, count in counts.items():
            class_objects[(split, class_id)] += count
            class_images[(split, class_id)] += 1
        capture_splits[row["capture_key"]].add(split)
        session_splits[row["session_id"]].add(split)
        output_rows.append({
            "sample_id": identifier,
            "split": split,
            "image_path": str(image_target),
            "label_path": str(label_target),
            "source_image": str(image_source),
            "source_label": str(label_source),
            "source_relative_path": row["relative_path"],
            "capture_key": row["capture_key"],
            "session_id": row["session_id"],
            "object_count": sum(counts.values()),
            "class_ids": "|".join(str(value) for value in sorted(counts)),
            "link_mode": args.link_mode,
        })
        if index % 200 == 0 or index == len(rows):
            print(f"prepared: {index:,}/{len(rows):,}")

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dataset.yaml").write_text(yaml_text(output_dir, classes), encoding="utf-8")
    mapping_fields = [
        "sample_id", "split", "image_path", "label_path", "source_image", "source_label",
        "source_relative_path", "capture_key", "session_id", "object_count", "class_ids", "link_mode",
    ]
    write_csv(output_dir / "dataset_index.csv", output_rows, mapping_fields)

    distribution_rows = []
    for split in SPLIT_DIR:
        for class_id, name in enumerate(classes):
            distribution_rows.append({
                "split": split,
                "class_id": class_id,
                "class_name": name,
                "objects": class_objects[(split, class_id)],
                "images_with_class": class_images[(split, class_id)],
            })
    write_csv(
        output_dir / "class_distribution.csv",
        distribution_rows,
        ["split", "class_id", "class_name", "objects", "images_with_class"],
    )

    split_counts = Counter(row["split"] for row in output_rows)
    image_counts = {
        split: len(list((output_dir / "images" / folder).glob("*")))
        for split, folder in SPLIT_DIR.items()
    }
    label_counts = {
        split: len(list((output_dir / "labels" / folder).glob("*.txt")))
        for split, folder in SPLIT_DIR.items()
    }
    summary = {
        "source_manifest": str(manifest_path),
        "output_dir": str(output_dir),
        "link_mode": args.link_mode,
        "classes": classes,
        "samples": len(output_rows),
        "split_counts": dict(split_counts),
        "image_counts": image_counts,
        "label_counts": label_counts,
        "total_objects": sum(row["object_count"] for row in output_rows),
        "capture_split_leaks": sum(len(values) > 1 for values in capture_splits.values()),
        "session_split_leaks": sum(len(values) > 1 for values in session_splits.values()),
        "link_status": dict(link_status),
        "source_files_modified": False,
        "outputs_independent_from_source": args.link_mode == "copy",
    }
    write_json(output_dir / "summary.json", summary)
    print("YOLO dataset preparation complete")
    print(f"samples: {summary['samples']:,}")
    print(f"splits: {summary['split_counts']}")
    print(f"objects: {summary['total_objects']:,}")
    print(f"capture split leaks: {summary['capture_split_leaks']}")
    print(f"session split leaks: {summary['session_split_leaks']}")
    print(f"yaml: {output_dir / 'dataset.yaml'}")
    print(f"index: {output_dir / 'dataset_index.csv'}")
    print(f"summary: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
