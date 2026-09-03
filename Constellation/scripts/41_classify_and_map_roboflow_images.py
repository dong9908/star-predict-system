"""Classify all stage-40 Roboflow images into safe downstream queues.

Every image receives one primary use, while an image containing both a direct
target and Orion/Taurus/Auriga context is also written to the WCS queue:
1) direct_label_candidate/direct_and_wcs: a source label names a target;
2) wcs_required: constellation context must be relabelled with WCS;
3) negative_candidate: no target/context annotation, pending review.

Direct labels are converted to the project's eight-class IDs. Polygon labels
are converted to enclosing YOLO boxes. No review decision is auto-approved.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE40 = PROJECT_ROOT / "data" / "results" / "roboflow_training_preparation"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "roboflow_classification_mapping"
TARGET_CLASSES = (
    "Pleiades", "Jupiter", "Betelgeuse", "Aldebaran",
    "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix",
)
TARGET_BY_NORMALIZED = {re.sub(r"[^a-z0-9]+", "", name.casefold()): index for index, name in enumerate(TARGET_CLASSES)}
CONTEXT_BY_NORMALIZED = {
    "orion": "Betelgeuse|Bellatrix",
    "taurus": "Pleiades|Aldebaran|Zeta Tauri|Elnath",
    "auriga": "Elnath|Hassaleh",
}
REVIEW_FIELDS = [
    "review_index", "dataset", "source_split", "sample_id", "image_path", "source_label_path",
    "proposed_use", "automatic_reason", "source_class_names", "target_candidates",
    "converted_label_path", "converted_object_count", "exact_duplicate_group",
    "near_duplicate_group", "license", "source_url", "visual_type", "review_decision", "review_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage40-dir", type=Path, default=DEFAULT_STAGE40)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def parse_names(yaml_path: Path) -> list[str]:
    text = yaml_path.read_text(encoding="utf-8-sig")
    match = re.search(r"(?m)^names:\s*(\[.*\])\s*$", text)
    if not match:
        raise ValueError(f"names를 읽을 수 없습니다: {yaml_path}")
    names = ast.literal_eval(match.group(1))
    if not isinstance(names, list):
        raise ValueError(f"잘못된 names 형식입니다: {yaml_path}")
    return [str(name) for name in names]


def dataset_names(stage40: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for row in read_csv(stage40 / "dataset_summary.csv"):
        result[row["dataset"]] = parse_names(Path(row["yaml_path"]))
    return result


def yolo_box(parts: list[str]) -> tuple[float, float, float, float]:
    values = [float(value) for value in parts[1:]]
    if len(parts) == 5:
        return values[0], values[1], values[2], values[3]
    if len(values) < 6 or len(values) % 2:
        raise ValueError("지원하지 않는 YOLO 라벨 열 수")
    xs, ys = values[0::2], values[1::2]
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return (left + right) / 2, (top + bottom) / 2, right - left, bottom - top


def convert_direct_labels(source: Path, names: list[str], target: Path) -> tuple[int, Counter[int]]:
    lines: list[str] = []
    counts: Counter[int] = Counter()
    for line_number, raw in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        try:
            source_id = int(parts[0])
            source_name = names[source_id]
        except (ValueError, IndexError) as error:
            raise ValueError(f"{source}:{line_number} 클래스 오류") from error
        target_id = TARGET_BY_NORMALIZED.get(normalized(source_name))
        if target_id is None:
            continue
        x, y, width, height = yolo_box(parts)
        if width <= 0 or height <= 0 or not all(0 <= value <= 1 for value in (x, y, width, height)):
            raise ValueError(f"{source}:{line_number} 좌표 오류")
        lines.append(f"{target_id} {x:.8f} {y:.8f} {width:.8f} {height:.8f}")
        counts[target_id] += 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
    return len(lines), counts


def previous_reviews(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row["sample_id"]: row for row in read_csv(path)}


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    stage40, output = args.stage40_dir.resolve(), args.output_dir.resolve()
    inventory_path = stage40 / "image_inventory_review.csv"
    summary_path = stage40 / "summary.json"
    if not inventory_path.is_file() or not summary_path.is_file():
        raise FileNotFoundError("40번 결과가 없습니다. 먼저 40번을 완료하세요.")
    stage40_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if stage40_summary.get("status") != "completed" or int(stage40_summary.get("validation_error_count", -1)) != 0:
        raise RuntimeError("40번 검증이 정상 완료되지 않았습니다.")

    names_by_dataset = dataset_names(stage40)
    inventory = read_csv(inventory_path)
    if len(inventory) != int(stage40_summary["image_count"]):
        raise RuntimeError("40번 summary와 inventory 이미지 수가 다릅니다.")
    output.mkdir(parents=True, exist_ok=True)
    review_path = output / "classification_review.csv"
    old_reviews = previous_reviews(review_path)
    converted_dir = output / "converted_direct_labels"
    converted_dir.mkdir(parents=True, exist_ok=True)
    for old in converted_dir.glob("*.txt"):
        old.unlink()

    review_rows: list[dict[str, Any]] = []
    direct_rows: list[dict[str, Any]] = []
    wcs_rows: list[dict[str, Any]] = []
    negative_rows: list[dict[str, Any]] = []
    converted_objects: Counter[int] = Counter()
    queue_counts: Counter[str] = Counter()
    dataset_queue_counts: Counter[tuple[str, str]] = Counter()

    for index, item in enumerate(inventory, 1):
        source_names = [name for name in item.get("source_class_names", "").split("|") if name]
        direct_names = [name for name in source_names if normalized(name) in TARGET_BY_NORMALIZED]
        context_names = [name for name in source_names if normalized(name) in CONTEXT_BY_NORMALIZED]
        target_candidates: list[str] = []
        if direct_names and context_names:
            proposed_use = "direct_and_wcs"
            automatic_reason = "direct target label can be converted; constellation context also requires WCS"
            for name in direct_names:
                target_candidates.append(TARGET_CLASSES[TARGET_BY_NORMALIZED[normalized(name)]])
            for name in context_names:
                target_candidates.extend(CONTEXT_BY_NORMALIZED[normalized(name)].split("|"))
        elif direct_names:
            proposed_use = "direct_label_candidate"
            automatic_reason = "source label directly matches an eight-class target; visual review required"
            for name in direct_names:
                target_candidates.append(TARGET_CLASSES[TARGET_BY_NORMALIZED[normalized(name)]])
        elif context_names:
            proposed_use = "wcs_required"
            automatic_reason = "constellation-level box cannot represent individual target stars"
            for name in context_names:
                target_candidates.extend(CONTEXT_BY_NORMALIZED[normalized(name)].split("|"))
        else:
            proposed_use = "negative_candidate"
            automatic_reason = "no direct target or Orion/Taurus/Auriga context label; background review required"

        converted_path = ""
        converted_count = 0
        if direct_names:
            short_id = f'{index:05d}_{item["dataset"]}_{item["sha256"][:12]}'
            target = converted_dir / f"{short_id}.txt"
            converted_count, counts = convert_direct_labels(
                Path(item["label_path"]), names_by_dataset[item["dataset"]], target
            )
            if converted_count <= 0:
                raise RuntimeError(f"직접 후보에서 변환 객체가 없습니다: {item['sample_id']}")
            converted_path = str(target)
            converted_objects.update(counts)

        old = old_reviews.get(item["sample_id"], {})
        row = {
            "review_index": index,
            "dataset": item["dataset"],
            "source_split": item["source_split"],
            "sample_id": item["sample_id"],
            "image_path": item["image_path"],
            "source_label_path": item["label_path"],
            "proposed_use": proposed_use,
            "automatic_reason": automatic_reason,
            "source_class_names": item.get("source_class_names", ""),
            "target_candidates": "|".join(dict.fromkeys(target_candidates)),
            "converted_label_path": converted_path,
            "converted_object_count": converted_count,
            "exact_duplicate_group": item.get("exact_duplicate_group", ""),
            "near_duplicate_group": item.get("near_duplicate_group", ""),
            "license": item.get("license", ""),
            "source_url": item.get("source_url", ""),
            "visual_type": old.get("visual_type", ""),
            "review_decision": old.get("review_decision", ""),
            "review_notes": old.get("review_notes", ""),
        }
        review_rows.append(row)
        queue_counts[proposed_use] += 1
        dataset_queue_counts[(item["dataset"], proposed_use)] += 1
        if direct_names:
            direct_rows.append(row)
        if context_names:
            wcs_rows.append(row)
        if not direct_names and not context_names:
            negative_rows.append(row)

    write_csv(review_path, review_rows, REVIEW_FIELDS)
    write_csv(output / "direct_label_candidates.csv", direct_rows, REVIEW_FIELDS)
    write_csv(output / "wcs_candidates.csv", wcs_rows, REVIEW_FIELDS)
    write_csv(output / "negative_candidates.csv", negative_rows, REVIEW_FIELDS)
    distribution_rows = []
    for dataset in sorted(names_by_dataset):
        for queue in ("direct_label_candidate", "direct_and_wcs", "wcs_required", "negative_candidate"):
            distribution_rows.append({"dataset": dataset, "queue": queue, "images": dataset_queue_counts[(dataset, queue)]})
    write_csv(output / "queue_distribution.csv", distribution_rows, ["dataset", "queue", "images"])

    summary = {
        "status": "completed",
        "source_images_modified": False,
        "input_images": len(inventory),
        "classified_images": len(review_rows),
        "all_images_accounted_for": len(inventory) == len(review_rows),
        "queue_counts": dict(queue_counts),
        "converted_direct_objects_by_target": {
            TARGET_CLASSES[class_id]: converted_objects[class_id] for class_id in range(len(TARGET_CLASSES))
        },
        "automatic_approval": False,
        "training_ready": False,
        "review_instructions": {
            "visual_type_values": "real_sky|simulation|diagram|celestial_closeup|invalid",
            "review_decision_values": "accept|reject",
            "direct": "accept only when the box correctly covers the named target",
            "wcs": "accepted real-sky images proceed to plate solving; do not use constellation boxes",
            "negative": "accept only when no eight target object is present",
        },
        "paths": {
            "classification_review": str(review_path),
            "direct_candidates": str(output / "direct_label_candidates.csv"),
            "wcs_candidates": str(output / "wcs_candidates.csv"),
            "negative_candidates": str(output / "negative_candidates.csv"),
            "converted_direct_labels": str(converted_dir),
            "queue_distribution": str(output / "queue_distribution.csv"),
            "stage40_contact_sheets": stage40_summary["paths"]["contact_sheets"],
        },
    }
    write_json(output / "summary.json", summary)
    print("Roboflow 전체 이미지 41번 분류·클래스 매핑 완료")
    print(f"전체 반영: {len(review_rows)}/{len(inventory)}장")
    print(f"직접 라벨 후보: {len(direct_rows)}장")
    print(f"WCS 필요 후보: {len(wcs_rows)}장")
    print(f"음성 후보: {len(negative_rows)}장")
    print("변환 객체:", ", ".join(f"{name}={converted_objects[index]}" for index, name in enumerate(TARGET_CLASSES)))
    print(f"review: {review_path}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
