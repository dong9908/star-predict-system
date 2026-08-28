"""Build a leakage-safe training manifest for the MobilTelesco dataset."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

from lib.io_utils import configure_utf8_console, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "photo" / "MobilTelesco" / "extracted" / "MobilTelesco"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "mobiltelesco"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".dng"}
DATE_PATTERN = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{4}$")
RUN_PATTERN = re.compile(r"run\s*\d+$", re.IGNORECASE)
BURST_PATTERN = re.compile(r"^(IMG\d{14})_BURST", re.IGNORECASE)
DEFAULT_CLASSES_8 = [
    "Pleiades", "Jupiter", "Betelgeuse", "Aldebaran",
    "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument("--train-ratio", type=float, default=0.70)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--skip-hash", action="store_true", help="JPG exact hash calculation skip")
    return parser.parse_args()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_part(parts: tuple[str, ...], predicate) -> str:
    return next((part for part in parts if predicate(part)), "")


def label_scheme(parts: tuple[str, ...]) -> str:
    if "25-Classes" in parts:
        return "25_classes"
    if "8-Classes" in parts:
        return "8_classes"
    return "none"


def exposure_seconds(parts: tuple[str, ...]) -> int | str:
    if "20sEXP" in parts:
        return 20
    if "30sEXP" in parts:
        return 30
    return ""


def burst_group(stem: str) -> str:
    match = BURST_PATTERN.match(stem)
    return match.group(1).upper() if match else stem.upper()


def read_classes(dataset_root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"8_classes": DEFAULT_CLASSES_8}
    candidates = sorted(dataset_root.rglob("classes.txt"))
    for path in candidates:
        scheme = label_scheme(path.relative_to(dataset_root).parts)
        values = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        if scheme != "none" and len(values) > len(result.get(scheme, [])):
            result[scheme] = values
    return result


def parse_yolo_label(path: Path | None, class_count: int) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"label_exists": False, "label_objects": 0, "label_class_ids": "", "label_valid": False, "label_errors": "missing_label"}
    ids: list[int] = []
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
        ids.append(class_id)
    return {
        "label_exists": True,
        "label_objects": len(ids),
        "label_class_ids": "|".join(str(value) for value in sorted(set(ids))),
        "label_valid": not errors and bool(ids),
        "label_errors": "|".join(errors),
    }


def image_dimensions(path: Path) -> tuple[int | str, int | str]:
    if path.suffix.lower() not in {".jpg", ".jpeg"}:
        return "", ""
    try:
        with Image.open(path) as image:
            return image.width, image.height
    except OSError:
        return "", ""


def raw_session(relative: Path, group: str) -> str:
    parts = relative.parts
    date = find_part(parts, lambda value: bool(DATE_PATTERN.match(value))) or "unknown_date"
    run = find_part(parts, lambda value: bool(RUN_PATTERN.search(value)))
    exposure = exposure_seconds(parts)
    if run:
        return f"{date}__{exposure or 'unknown'}s__{run.lower()}"
    return f"{date}__{exposure or 'unknown'}s__{group.lower()}"


def stable_session_split(sessions: list[str], seed: int, train_ratio: float, val_ratio: float) -> dict[str, str]:
    ranked = sorted(sessions, key=lambda value: hashlib.sha256(f"{seed}:{value}".encode()).hexdigest())
    count = len(ranked)
    train_count = round(count * train_ratio)
    val_count = round(count * val_ratio)
    if count >= 3:
        train_count = max(1, min(train_count, count - 2))
        val_count = max(1, min(val_count, count - train_count - 1))
    result: dict[str, str] = {}
    for index, session in enumerate(ranked):
        result[session] = "train" if index < train_count else "validation" if index < train_count + val_count else "test"
    return result


def training_role(row: dict[str, Any]) -> str:
    if row["is_dark"]:
        return "exclude_dark_calibration"
    if row["is_skymap"]:
        return "auxiliary_skymap"
    if row["extension"] == ".dng":
        return "raw_light_conversion_candidate"
    if row["label_scheme"] == "8_classes" and row["label_valid"]:
        return "supervised_detection_8"
    if row["label_scheme"] == "25_classes" and row["label_valid"]:
        return "supervised_detection_25"
    if row["dataset_section"] == "Unlabelled" and row["is_compressed"]:
        return "unlabelled_pretraining"
    return "exclude_or_review"


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.train_ratio <= 0 or args.val_ratio <= 0 or args.train_ratio + args.val_ratio >= 1:
        raise ValueError("train/validation ratios must be positive and sum to less than 1.")
    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"MobilTelesco root not found: {dataset_root}")

    classes = read_classes(dataset_root)
    paths = sorted(path for path in dataset_root.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
    rows: list[dict[str, Any]] = []
    unlabelled_session_by_capture: dict[str, str] = {}

    for path in paths:
        relative = path.relative_to(dataset_root)
        parts = relative.parts
        capture_key = path.stem.lower()
        group = burst_group(path.stem)
        section = parts[0] if parts else ""
        session = raw_session(relative, group)
        if section == "Unlabelled":
            unlabelled_session_by_capture.setdefault(capture_key, session)
        rows.append({
            "relative_path": relative.as_posix(),
            "absolute_path": str(path),
            "filename": path.name,
            "capture_key": capture_key,
            "burst_group": group,
            "dataset_section": section,
            "label_scheme": label_scheme(parts),
            "date_folder": find_part(parts, lambda value: bool(DATE_PATTERN.match(value))),
            "run_name": find_part(parts, lambda value: bool(RUN_PATTERN.search(value))),
            "exposure_seconds": exposure_seconds(parts),
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "is_compressed": "Compressed" in parts,
            "is_dark": any(part.lower() == "darks" for part in parts),
            "is_light": any(part.lower() == "lights" for part in parts),
            "is_skymap": any(part.lower() == "skymap" for part in parts),
            "is_rawonly": "RAWonly" in parts,
            "session_id": session,
        })

    for row in rows:
        if row["dataset_section"] == "Labelled" and row["capture_key"] in unlabelled_session_by_capture:
            row["session_id"] = unlabelled_session_by_capture[row["capture_key"]]

    capture_counts = Counter(str(row["capture_key"]) for row in rows)
    hashes: dict[str, list[int]] = defaultdict(list)
    print(f"files scanned: {len(rows):,}")
    for index, row in enumerate(rows):
        path = Path(row["absolute_path"])
        row["capture_representation_count"] = capture_counts[str(row["capture_key"])]
        row["has_jpg_pair"] = False
        row["has_dng_pair"] = False
        width, height = image_dimensions(path)
        row["width"] = width
        row["height"] = height
        scheme = str(row["label_scheme"])
        label_path = path.with_suffix(".txt") if scheme != "none" else None
        row["label_path"] = str(label_path) if label_path and label_path.is_file() else ""
        row.update(parse_yolo_label(label_path, len(classes.get(scheme, []))))
        row["sha256"] = ""
        if not args.skip_hash and row["extension"] in {".jpg", ".jpeg"}:
            row["sha256"] = file_hash(path)
            hashes[row["sha256"]].append(index)
        if (index + 1) % 250 == 0 or index + 1 == len(rows):
            print(f"processed: {index + 1:,}/{len(rows):,}")

    formats_by_capture: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        formats_by_capture[str(row["capture_key"])].add(str(row["extension"]))
    for row in rows:
        formats = formats_by_capture[str(row["capture_key"])]
        row["has_jpg_pair"] = bool(formats & {".jpg", ".jpeg"})
        row["has_dng_pair"] = ".dng" in formats

    for indices in hashes.values():
        ordered = sorted(
            indices,
            key=lambda idx: (
                0 if rows[idx]["label_scheme"] == "25_classes" else
                1 if rows[idx]["label_scheme"] == "8_classes" else 2,
                rows[idx]["relative_path"],
            ),
        )
        group_id = f"dup_{rows[ordered[0]]['sha256'][:12]}"
        for position, idx in enumerate(ordered):
            rows[idx]["exact_duplicate_group"] = group_id
            rows[idx]["exact_duplicate_count"] = len(indices)
            rows[idx]["preferred_exact_copy"] = position == 0
    for row in rows:
        row.setdefault("exact_duplicate_group", "")
        row.setdefault("exact_duplicate_count", 1)
        row.setdefault("preferred_exact_copy", True)
        row["training_role"] = training_role(row)
        row["supervised_eligible"] = row["training_role"].startswith("supervised_detection_")
        row["pretraining_eligible"] = row["training_role"] == "unlabelled_pretraining"

    # Sessions connected by a shared capture key or exact image hash form one
    # split unit. This prevents duplicates stored in different folders from
    # leaking between train, validation and test.
    all_sessions = sorted({str(row["session_id"]) for row in rows})
    parent = {session: session for session in all_sessions}

    def find(session: str) -> str:
        while parent[session] != session:
            parent[session] = parent[parent[session]]
            session = parent[session]
        return session

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    sessions_by_capture: dict[str, set[str]] = defaultdict(set)
    sessions_by_hash: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        session = str(row["session_id"])
        # Calibration darks and generated skymaps may be byte-identical across
        # many nights. They are not model inputs, so they must not collapse all
        # observing sessions into one split unit.
        split_relevant = not row["is_dark"] and not row["is_skymap"]
        if split_relevant:
            sessions_by_capture[str(row["capture_key"])].add(session)
        if split_relevant and row["sha256"]:
            sessions_by_hash[str(row["sha256"])].add(session)
    for values in list(sessions_by_capture.values()) + list(sessions_by_hash.values()):
        ordered = sorted(values)
        for other in ordered[1:]:
            union(ordered[0], other)
    split_units = sorted({find(session) for session in all_sessions})
    unit_split = stable_session_split(split_units, args.seed, args.train_ratio, args.val_ratio)
    session_split = {session: unit_split[find(session)] for session in all_sessions}
    for row in rows:
        row["split_unit_id"] = find(str(row["session_id"]))
        row["split"] = session_split[str(row["session_id"])]

    fields = [
        "relative_path", "absolute_path", "filename", "capture_key", "burst_group",
        "dataset_section", "label_scheme", "date_folder", "run_name", "session_id", "split_unit_id", "split",
        "exposure_seconds", "extension", "size_bytes", "width", "height", "is_compressed",
        "is_dark", "is_light", "is_skymap", "is_rawonly", "has_jpg_pair", "has_dng_pair",
        "capture_representation_count", "sha256", "exact_duplicate_group", "exact_duplicate_count",
        "preferred_exact_copy", "label_path", "label_exists", "label_objects", "label_class_ids",
        "label_valid", "label_errors", "training_role", "supervised_eligible", "pretraining_eligible",
    ]
    write_csv(output_dir / "manifest_all.csv", rows, fields)
    selected = [
        row for row in rows
        if row["supervised_eligible"] or row["pretraining_eligible"] or row["training_role"] == "raw_light_conversion_candidate"
    ]
    write_csv(output_dir / "manifest_training_candidates.csv", selected, fields)
    task_manifests = {
        "manifest_supervised_8_classes.csv": [row for row in rows if row["training_role"] == "supervised_detection_8"],
        "manifest_supervised_25_classes.csv": [row for row in rows if row["training_role"] == "supervised_detection_25"],
        "manifest_unlabelled_pretraining.csv": [row for row in rows if row["training_role"] == "unlabelled_pretraining"],
        "manifest_raw_dng_conversion.csv": [row for row in rows if row["training_role"] == "raw_light_conversion_candidate"],
        "manifest_excluded_auxiliary.csv": [
            row for row in rows
            if row["training_role"] in {"exclude_dark_calibration", "auxiliary_skymap", "exclude_or_review"}
        ],
    }
    for filename, task_rows in task_manifests.items():
        write_csv(output_dir / filename, task_rows, fields)

    session_rows = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["session_id"])].append(row)
    for session, items in sorted(grouped.items()):
        session_rows.append({
            "session_id": session,
            "split_unit_id": find(session),
            "split": session_split[session],
            "files": len(items),
            "capture_keys": len({str(item["capture_key"]) for item in items}),
            "labelled_files": sum(bool(item["label_exists"]) for item in items),
            "dates": "|".join(sorted({str(item["date_folder"]) for item in items if item["date_folder"]})),
            "runs": "|".join(sorted({str(item["run_name"]) for item in items if item["run_name"]})),
        })
    write_csv(output_dir / "sessions.csv", session_rows, ["session_id", "split_unit_id", "split", "files", "capture_keys", "labelled_files", "dates", "runs"])

    output_dir.mkdir(parents=True, exist_ok=True)
    for scheme, values in classes.items():
        (output_dir / f"classes_{scheme}.txt").write_text("\n".join(values) + "\n", encoding="utf-8")

    hash_groups = [indices for indices in hashes.values() if len(indices) > 1]
    split_by_capture: dict[str, set[str]] = defaultdict(set)
    split_by_hash: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        split_relevant = not row["is_dark"] and not row["is_skymap"]
        if split_relevant:
            split_by_capture[str(row["capture_key"])].add(str(row["split"]))
        if split_relevant and row["sha256"]:
            split_by_hash[str(row["sha256"])].add(str(row["split"]))
    summary = {
        "dataset_root": str(dataset_root),
        "total_image_files": len(rows),
        "jpg_files": sum(row["extension"] in {".jpg", ".jpeg"} for row in rows),
        "dng_files": sum(row["extension"] == ".dng" for row in rows),
        "unique_capture_keys": len(capture_counts),
        "sessions": len(grouped),
        "split_units": len(split_units),
        "session_split_counts": dict(Counter(session_split.values())),
        "file_split_counts": dict(Counter(str(row["split"]) for row in rows)),
        "training_role_counts": dict(Counter(str(row["training_role"]) for row in rows)),
        "task_manifest_counts": {name: len(values) for name, values in task_manifests.items()},
        "label_scheme_counts": dict(Counter(str(row["label_scheme"]) for row in rows)),
        "valid_labelled_images": sum(bool(row["label_valid"]) for row in rows),
        "invalid_or_missing_labelled_images": sum(row["label_scheme"] != "none" and not row["label_valid"] for row in rows),
        "dark_files": sum(bool(row["is_dark"]) for row in rows),
        "skymap_files": sum(bool(row["is_skymap"]) for row in rows),
        "jpg_dng_paired_capture_keys": sum(".dng" in values and bool(values & {".jpg", ".jpeg"}) for values in formats_by_capture.values()),
        "exact_duplicate_hash_groups": len(hash_groups),
        "exact_duplicate_jpg_files": sum(len(indices) for indices in hash_groups),
        "capture_split_leaks": sum(len(values) > 1 for values in split_by_capture.values()),
        "exact_hash_split_leaks": sum(len(values) > 1 for values in split_by_hash.values()),
        "split_policy": "All representations of the same capture and session stay in one split.",
        "source_files_modified": False,
    }
    write_json(output_dir / "summary.json", summary)
    print("manifest complete")
    print(f"sessions: {summary['sessions']:,}")
    print(f"capture keys: {summary['unique_capture_keys']:,}")
    print(f"valid labelled images: {summary['valid_labelled_images']:,}")
    print(f"capture split leaks: {summary['capture_split_leaks']}")
    print(f"exact hash split leaks: {summary['exact_hash_split_leaks']}")
    print(f"manifest: {output_dir / 'manifest_all.csv'}")
    print(f"training candidates: {output_dir / 'manifest_training_candidates.csv'}")
    print(f"sessions: {output_dir / 'sessions.csv'}")
    print(f"summary: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
