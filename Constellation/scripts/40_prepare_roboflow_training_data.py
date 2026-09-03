"""Inventory and review every downloaded Roboflow image before YOLO merging.

This stage is intentionally read-only with respect to source datasets.  It
validates image/label pairs, normalizes source class names, computes SHA-256
and perceptual dHash values, detects exact and near duplicates, and creates
review CSV/contact sheets.  It does not promote third-party labels directly
into the eight-class training dataset.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from lib.io_utils import configure_utf8_console, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "photo" / "Roboflow"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "roboflow_training_preparation"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
TARGET_CLASSES = (
    "Pleiades", "Jupiter", "Betelgeuse", "Aldebaran",
    "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix",
)
TARGET_IDS = {name.lower(): index for index, name in enumerate(TARGET_CLASSES)}
CONTEXT_CLASSES = {
    "orion": "Betelgeuse|Bellatrix",
    "taurus": "Pleiades|Aldebaran|Zeta Tauri|Elnath",
    "auriga": "Elnath|Hassaleh",
}
IMAGE_FIELDS = [
    "review_index", "dataset", "source_split", "sample_id", "image_path",
    "label_path", "width", "height", "image_status", "label_status",
    "object_count", "source_class_ids", "source_class_names",
    "candidate_kind", "target_candidates", "sha256", "dhash",
    "exact_duplicate_group", "near_duplicate_group", "near_duplicate_distance",
    "license", "source_url", "visual_type", "review_decision", "review_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--near-duplicate-distance", type=int, default=4)
    parser.add_argument("--sheet-columns", type=int, default=8)
    parser.add_argument("--sheet-rows", type=int, default=6)
    parser.add_argument("--skip-contact-sheets", action="store_true")
    return parser.parse_args()


def normalize_class(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def parse_yaml(path: Path) -> tuple[list[str], str, str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.search(r"(?m)^names:\s*(\[.*\])\s*$", text)
    if not match:
        raise ValueError(f"names 목록을 읽을 수 없습니다: {path}")
    names = ast.literal_eval(match.group(1))
    if not isinstance(names, list) or not all(isinstance(item, str) for item in names):
        raise ValueError(f"잘못된 names 목록입니다: {path}")
    license_match = re.search(r"(?m)^\s*license:\s*(.+?)\s*$", text)
    url_match = re.search(r"(?m)^\s*url:\s*(.+?)\s*$", text)
    return names, license_match.group(1).strip() if license_match else "", url_match.group(1).strip() if url_match else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def dhash(image: Image.Image) -> int:
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    gray = ImageOps.grayscale(image).resize((9, 8), resampling)
    pixels = list(gray.get_flattened_data()) if hasattr(gray, "get_flattened_data") else list(gray.getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return value


def parse_label(path: Path, names: list[str]) -> tuple[list[int], Counter[int], list[str]]:
    ids: list[int] = []
    counts: Counter[int] = Counter()
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as error:
        return ids, counts, [f"read_error:{error}"]
    for line_number, raw in enumerate(lines, 1):
        if not raw.strip():
            continue
        parts = raw.split()
        is_box = len(parts) == 5
        is_polygon = len(parts) >= 7 and (len(parts) - 1) % 2 == 0
        if not is_box and not is_polygon:
            errors.append(f"line_{line_number}_columns")
            continue
        try:
            class_id = int(parts[0])
            coordinates = [float(value) for value in parts[1:]]
        except ValueError:
            errors.append(f"line_{line_number}_number")
            continue
        if not 0 <= class_id < len(names):
            errors.append(f"line_{line_number}_class")
            continue
        if not all(0 <= value <= 1 for value in coordinates):
            errors.append(f"line_{line_number}_range")
            continue
        if is_box and (coordinates[2] <= 0 or coordinates[3] <= 0):
            errors.append(f"line_{line_number}_range")
            continue
        ids.append(class_id)
        counts[class_id] += 1
    return ids, counts, errors


def locate_yaml(root: Path) -> Path:
    candidates = sorted(root.rglob("data.yaml")) + sorted(root.rglob("dataset.yaml"))
    if not candidates:
        raise FileNotFoundError(f"data.yaml이 없습니다: {root}")
    return candidates[0]


def split_from_path(path: Path) -> str:
    lowered = [part.lower() for part in path.parts]
    for value in ("train", "valid", "validation", "test"):
        if value in lowered:
            return "validation" if value == "valid" else value
    return "unknown"


def label_for_image(image: Path) -> Path:
    parts = list(image.parts)
    lowered = [part.lower() for part in parts]
    if "images" in lowered:
        parts[lowered.index("images")] = "labels"
    return Path(*parts).with_suffix(".txt")


def candidate_info(class_names: list[str]) -> tuple[str, str]:
    direct: set[str] = set()
    context: set[str] = set()
    for source_name in class_names:
        normalized = normalize_class(source_name)
        for target in TARGET_CLASSES:
            if normalized == normalize_class(target):
                direct.add(target)
        key = source_name.strip().casefold().replace("_", " ")
        key = re.sub(r"\s+", " ", key)
        if key in CONTEXT_CLASSES:
            context.update(CONTEXT_CLASSES[key].split("|"))
    if direct:
        return "direct_target", "|".join(sorted(direct, key=TARGET_CLASSES.index))
    if context:
        return "constellation_context", "|".join(sorted(context, key=TARGET_CLASSES.index))
    return "non_target_review", ""


class BKTree:
    def __init__(self) -> None:
        self.root: tuple[int, int, dict[int, Any]] | None = None

    @staticmethod
    def distance(left: int, right: int) -> int:
        return (left ^ right).bit_count()

    def add(self, value: int, index: int) -> None:
        if self.root is None:
            self.root = (value, index, {})
            return
        node = self.root
        while True:
            distance = self.distance(value, node[0])
            children = node[2]
            if distance not in children:
                children[distance] = (value, index, {})
                return
            node = children[distance]

    def find(self, value: int, threshold: int) -> list[tuple[int, int]]:
        if self.root is None:
            return []
        results: list[tuple[int, int]] = []
        stack = [self.root]
        while stack:
            node_value, index, children = stack.pop()
            distance = self.distance(value, node_value)
            if distance <= threshold:
                results.append((distance, index))
            low, high = distance - threshold, distance + threshold
            stack.extend(child for edge, child in children.items() if low <= edge <= high)
        return results


def assign_duplicate_groups(rows: list[dict[str, Any]], threshold: int) -> tuple[int, int]:
    exact: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        if row["sha256"]:
            exact[row["sha256"]].append(index)
    exact_groups = [indices for indices in exact.values() if len(indices) > 1]
    for group_number, indices in enumerate(exact_groups, 1):
        for index in indices:
            rows[index]["exact_duplicate_group"] = f"exact_{group_number:05d}"

    tree = BKTree()
    near_group = 0
    for index, row in enumerate(rows):
        if not row["dhash"]:
            continue
        value = int(row["dhash"], 16)
        matches = [(distance, other) for distance, other in tree.find(value, threshold) if rows[other]["sha256"] != row["sha256"]]
        if matches:
            distance, other = min(matches)
            group = rows[other]["near_duplicate_group"]
            if not group:
                near_group += 1
                group = f"near_{near_group:05d}"
                rows[other]["near_duplicate_group"] = group
                rows[other]["near_duplicate_distance"] = distance
            row["near_duplicate_group"] = group
            row["near_duplicate_distance"] = distance
        tree.add(value, index)
    return len(exact_groups), near_group


def contact_sheets(rows: list[dict[str, Any]], output: Path, columns: int, sheet_rows: int) -> int:
    per_page = columns * sheet_rows
    cell_w, cell_h = 180, 165
    font = ImageFont.load_default()
    page_count = 0
    for dataset in sorted({row["dataset"] for row in rows}):
        items = [row for row in rows if row["dataset"] == dataset]
        target = output / dataset
        target.mkdir(parents=True, exist_ok=True)
        for start in range(0, len(items), per_page):
            page_count += 1
            page_items = items[start:start + per_page]
            sheet = Image.new("RGB", (columns * cell_w, sheet_rows * cell_h), "#111827")
            draw = ImageDraw.Draw(sheet)
            for offset, row in enumerate(page_items):
                left, top = (offset % columns) * cell_w, (offset // columns) * cell_h
                try:
                    with Image.open(row["image_path"]) as source:
                        thumb = ImageOps.contain(source.convert("RGB"), (170, 120))
                    sheet.paste(thumb, (left + (cell_w - thumb.width) // 2, top + 3))
                except Exception:
                    draw.rectangle((left + 5, top + 5, left + 175, top + 120), fill="#7f1d1d")
                color = "#22c55e" if row["candidate_kind"] == "direct_target" else ("#facc15" if row["candidate_kind"] == "constellation_context" else "white")
                text = f'#{row["review_index"]} {row["source_split"]}\n{row["candidate_kind"]}\n{row["source_class_names"][:26]}'
                draw.multiline_text((left + 5, top + 124), text, fill=color, font=font, spacing=1)
            sheet.save(target / f"page_{start // per_page + 1:04d}.jpg", quality=88)
    return page_count


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if not 0 <= args.near_duplicate_distance <= 16:
        raise ValueError("--near-duplicate-distance는 0~16이어야 합니다.")
    if args.sheet_columns < 1 or args.sheet_rows < 1:
        raise ValueError("연락처 시트 행과 열은 1 이상이어야 합니다.")
    input_dir, output = args.input_dir.resolve(), args.output_dir.resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Roboflow 입력 폴더가 없습니다: {input_dir}")

    rows: list[dict[str, Any]] = []
    dataset_summaries: list[dict[str, Any]] = []
    class_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    datasets = sorted(path for path in input_dir.iterdir() if path.is_dir())
    print(f"Roboflow 데이터셋 {len(datasets)}개 조사 시작")
    for dataset_root in datasets:
        extracted = dataset_root / "extracted" if (dataset_root / "extracted").is_dir() else dataset_root
        yaml_path = locate_yaml(extracted)
        names, license_name, source_url = parse_yaml(yaml_path)
        images = sorted(path for path in extracted.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
        dataset_objects: Counter[int] = Counter()
        dataset_errors = 0
        print(f"[{dataset_root.name}] {len(images)}장 처리 중...")
        for image in images:
            label = label_for_image(image)
            image_status, width, height, digest, image_hash = "ok", 0, 0, "", ""
            try:
                with Image.open(image) as opened:
                    opened.load()
                    width, height = opened.size
                    image_hash = f"{dhash(opened.convert('RGB')):016x}"
                digest = sha256(image)
            except (OSError, UnidentifiedImageError, ValueError) as error:
                image_status = f"error:{type(error).__name__}"
                errors.append({"dataset": dataset_root.name, "path": str(image), "kind": "image", "detail": str(error)})
                dataset_errors += 1
            ids: list[int] = []
            counts: Counter[int] = Counter()
            label_errors: list[str] = []
            if label.is_file():
                ids, counts, label_errors = parse_label(label, names)
            else:
                label_errors = ["missing_label"]
            if label_errors:
                errors.append({"dataset": dataset_root.name, "path": str(label), "kind": "label", "detail": "|".join(label_errors)})
                dataset_errors += 1
            dataset_objects.update(counts)
            present_names = [names[class_id] for class_id in sorted(counts)]
            kind, targets = candidate_info(present_names)
            rows.append({
                "review_index": len(rows) + 1,
                "dataset": dataset_root.name,
                "source_split": split_from_path(image),
                "sample_id": f"{dataset_root.name}_{image.stem}",
                "image_path": str(image),
                "label_path": str(label),
                "width": width,
                "height": height,
                "image_status": image_status,
                "label_status": "ok" if not label_errors else "|".join(label_errors),
                "object_count": sum(counts.values()),
                "source_class_ids": "|".join(str(value) for value in sorted(counts)),
                "source_class_names": "|".join(present_names),
                "candidate_kind": kind,
                "target_candidates": targets,
                "sha256": digest,
                "dhash": image_hash,
                "exact_duplicate_group": "",
                "near_duplicate_group": "",
                "near_duplicate_distance": "",
                "license": license_name,
                "source_url": source_url,
                "visual_type": "",
                "review_decision": "",
                "review_notes": "",
            })
        for class_id, class_name in enumerate(names):
            class_rows.append({
                "dataset": dataset_root.name,
                "source_class_id": class_id,
                "source_class_name": class_name,
                "object_count": dataset_objects[class_id],
                "normalized_name": normalize_class(class_name),
                "direct_target_id": TARGET_IDS.get(class_name.casefold(), ""),
                "context_targets": CONTEXT_CLASSES.get(class_name.casefold().replace("_", " "), ""),
            })
        dataset_summaries.append({
            "dataset": dataset_root.name,
            "images": len(images),
            "labels_found": sum(label_for_image(image).is_file() for image in images),
            "objects": sum(dataset_objects.values()),
            "classes": len(names),
            "errors": dataset_errors,
            "license": license_name,
            "source_url": source_url,
            "yaml_path": str(yaml_path),
        })

    print("정확·유사 이미지 중복 검사 중...")
    exact_groups, near_groups = assign_duplicate_groups(rows, args.near_duplicate_distance)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "image_inventory_review.csv", rows, IMAGE_FIELDS)
    write_csv(output / "dataset_summary.csv", dataset_summaries, list(dataset_summaries[0].keys()))
    write_csv(output / "class_mapping_candidates.csv", class_rows, list(class_rows[0].keys()))
    error_fields = ["dataset", "path", "kind", "detail"]
    write_csv(output / "validation_errors.csv", errors, error_fields)
    duplicate_rows = [row for row in rows if row["exact_duplicate_group"] or row["near_duplicate_group"]]
    write_csv(output / "duplicate_candidates.csv", duplicate_rows, IMAGE_FIELDS)
    contact_page_count = 0
    if not args.skip_contact_sheets:
        print("전체 이미지 연락처 시트 생성 중...")
        contact_page_count = contact_sheets(rows, output / "contact_sheets", args.sheet_columns, args.sheet_rows)

    kinds = Counter(row["candidate_kind"] for row in rows)
    split_counts = Counter(row["source_split"] for row in rows)
    summary = {
        "status": "completed",
        "source_datasets_modified": False,
        "dataset_count": len(dataset_summaries),
        "image_count": len(rows),
        "label_count": sum(item["labels_found"] for item in dataset_summaries),
        "object_count": sum(item["objects"] for item in dataset_summaries),
        "validation_error_count": len(errors),
        "candidate_kind_counts": dict(kinds),
        "source_split_counts": dict(split_counts),
        "exact_duplicate_groups": exact_groups,
        "near_duplicate_groups": near_groups,
        "near_duplicate_hamming_threshold": args.near_duplicate_distance,
        "contact_sheet_pages": contact_page_count,
        "training_ready": False,
        "next_action": "Review visual_type/review_decision. Do not merge source class IDs directly.",
        "paths": {
            "inventory_review": str(output / "image_inventory_review.csv"),
            "dataset_summary": str(output / "dataset_summary.csv"),
            "class_mapping_candidates": str(output / "class_mapping_candidates.csv"),
            "duplicates": str(output / "duplicate_candidates.csv"),
            "validation_errors": str(output / "validation_errors.csv"),
            "contact_sheets": str(output / "contact_sheets"),
        },
    }
    write_json(output / "summary.json", summary)
    print("Roboflow 전체 데이터 준비 자료 생성 완료")
    print(f"데이터셋: {len(dataset_summaries)}개 / 이미지: {len(rows)}장 / 라벨: {summary['label_count']}개")
    print(f"직접 목표 후보: {kinds['direct_target']}장 / 별자리 문맥 후보: {kinds['constellation_context']}장")
    print(f"정확 중복 그룹: {exact_groups} / 유사 중복 그룹: {near_groups}")
    print(f"검증 오류: {len(errors)} / 연락처 시트: {contact_page_count}페이지")
    print(f"review: {output / 'image_inventory_review.csv'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
