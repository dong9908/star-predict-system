"""Select balanced Roboflow candidates from stage 41 without data leakage.

All stage-41 images remain represented in selection_review.csv. Direct labels
are capped per target to prevent Pleiades from dominating training, WCS images
are routed to a separate queue, and negative candidates are sampled across
datasets. Near-duplicate groups contribute one automatic representative; the
remaining members stay in reserve and are never deleted.
"""

from __future__ import annotations

import argparse
import shutil
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE41 = PROJECT_ROOT / "data" / "results" / "roboflow_classification_mapping"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "roboflow_training_selection"
TARGET_CLASSES = (
    "Pleiades", "Jupiter", "Betelgeuse", "Aldebaran",
    "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix",
)
OUTPUT_FIELDS = [
    "selection_index", "dataset", "source_split", "sample_id", "image_path",
    "source_label_path", "converted_label_path", "proposed_use", "target_candidates",
    "near_duplicate_group", "duplicate_representative", "automatic_selection",
    "selection_reason", "visual_type", "review_decision", "review_notes",
    "license", "source_url",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage41-dir", type=Path, default=DEFAULT_STAGE41)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-direct-per-class", type=int, default=300)
    parser.add_argument("--max-negative", type=int, default=500)
    return parser.parse_args()


def accepted_manual(row: dict[str, str]) -> bool | None:
    value = row.get("review_decision", "").strip().lower()
    if value == "accept":
        return True
    if value == "reject":
        return False
    return None


def duplicate_representatives(rows: list[dict[str, str]]) -> set[str]:
    representatives: set[str] = set()
    seen_groups: set[str] = set()
    for row in rows:
        group = row.get("near_duplicate_group", "").strip()
        if not group:
            representatives.add(row["sample_id"])
        elif group not in seen_groups:
            seen_groups.add(group)
            representatives.add(row["sample_id"])
    return representatives


def round_robin(rows: Iterable[dict[str, str]], limit: int) -> list[dict[str, str]]:
    groups: dict[str, deque[dict[str, str]]] = defaultdict(deque)
    for row in rows:
        groups[row["dataset"]].append(row)
    selected: list[dict[str, str]] = []
    keys = sorted(groups)
    while keys and len(selected) < limit:
        remaining: list[str] = []
        for key in keys:
            if groups[key] and len(selected) < limit:
                selected.append(groups[key].popleft())
            if groups[key]:
                remaining.append(key)
        keys = remaining
    return selected


def converted_class_ids(row: dict[str, str]) -> set[int]:
    path = Path(row.get("converted_label_path", ""))
    if not path.is_file():
        return set()
    result: set[int] = set()
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw.strip():
            result.add(int(raw.split()[0]))
    return result


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.max_direct_per_class < 1 or args.max_negative < 0:
        raise ValueError("선택 상한값이 올바르지 않습니다.")
    stage41, output = args.stage41_dir.resolve(), args.output_dir.resolve()
    review_path = stage41 / "classification_review.csv"
    if not review_path.is_file():
        raise FileNotFoundError("41번 classification_review.csv가 없습니다.")
    rows = read_csv(review_path)
    representatives = duplicate_representatives(rows)

    direct = [row for row in rows if row.get("converted_label_path")]
    wcs = [row for row in rows if row["proposed_use"] in {"wcs_required", "direct_and_wcs"}]
    negatives = [row for row in rows if row["proposed_use"] == "negative_candidate"]

    direct_selected_ids: set[str] = set()
    direct_class_counts: Counter[str] = Counter()
    direct_ids_by_sample = {row["sample_id"]: converted_class_ids(row) for row in direct}
    for class_id, class_name in enumerate(TARGET_CLASSES):
        eligible = [
            row for row in direct
            if class_id in direct_ids_by_sample[row["sample_id"]]
            and row["sample_id"] in representatives
            and accepted_manual(row) is not False
        ]
        chosen = round_robin(eligible, args.max_direct_per_class)
        direct_selected_ids.update(row["sample_id"] for row in chosen)
        direct_class_counts[class_name] += len(chosen)

    wcs_selected_ids = {
        row["sample_id"] for row in wcs
        if row["sample_id"] in representatives and accepted_manual(row) is not False
    }
    negative_eligible = [
        row for row in negatives
        if row["sample_id"] in representatives and accepted_manual(row) is not False
    ]
    negative_selected_ids = {row["sample_id"] for row in round_robin(negative_eligible, args.max_negative)}

    output.mkdir(parents=True, exist_ok=True)
    selected_label_dir = output / "selected_direct_labels"
    selected_label_dir.mkdir(parents=True, exist_ok=True)
    for old in selected_label_dir.glob("*.txt"):
        old.unlink()

    output_rows: list[dict[str, Any]] = []
    selected_direct: list[dict[str, Any]] = []
    selected_wcs: list[dict[str, Any]] = []
    selected_negative: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for index, row in enumerate(rows, 1):
        sample_id = row["sample_id"]
        manual = accepted_manual(row)
        is_representative = sample_id in representatives
        if manual is False:
            selection, reason = "reject", "manual rejection"
        elif sample_id in direct_selected_ids:
            selection, reason = "select_direct", "balanced direct target candidate; visual confirmation still required"
        elif sample_id in wcs_selected_ids:
            selection, reason = "select_wcs", "unique constellation-context representative for WCS"
        elif sample_id in negative_selected_ids:
            selection, reason = "select_negative", "balanced negative candidate; target absence must be confirmed"
        elif not is_representative:
            selection, reason = "reserve_near_duplicate", "another member represents this perceptual duplicate group"
        elif row["proposed_use"] in {"direct_label_candidate", "direct_and_wcs"}:
            selection, reason = "reserve_class_balance", "held out to prevent target/source imbalance"
        elif row["proposed_use"] == "negative_candidate":
            selection, reason = "reserve_negative", "held out after balanced negative quota"
        else:
            selection, reason = "reserve", "not automatically selected"
        converted_target = ""
        if selection == "select_direct":
            source = Path(row["converted_label_path"])
            if not source.is_file():
                raise FileNotFoundError(f"변환 라벨이 없습니다: {source}")
            target = selected_label_dir / source.name
            shutil.copy2(source, target)
            converted_target = str(target)
        out = {
            "selection_index": index,
            "dataset": row["dataset"],
            "source_split": row["source_split"],
            "sample_id": sample_id,
            "image_path": row["image_path"],
            "source_label_path": row["source_label_path"],
            "converted_label_path": converted_target or row.get("converted_label_path", ""),
            "proposed_use": row["proposed_use"],
            "target_candidates": row.get("target_candidates", ""),
            "near_duplicate_group": row.get("near_duplicate_group", ""),
            "duplicate_representative": is_representative,
            "automatic_selection": selection,
            "selection_reason": reason,
            "visual_type": row.get("visual_type", ""),
            "review_decision": row.get("review_decision", ""),
            "review_notes": row.get("review_notes", ""),
            "license": row.get("license", ""),
            "source_url": row.get("source_url", ""),
        }
        output_rows.append(out)
        status_counts[selection] += 1
        if selection == "select_direct":
            selected_direct.append(out)
        elif selection == "select_wcs":
            selected_wcs.append(out)
        elif selection == "select_negative":
            selected_negative.append(out)

    write_csv(output / "selection_review.csv", output_rows, OUTPUT_FIELDS)
    write_csv(output / "selected_direct.csv", selected_direct, OUTPUT_FIELDS)
    write_csv(output / "selected_wcs.csv", selected_wcs, OUTPUT_FIELDS)
    write_csv(output / "selected_negative.csv", selected_negative, OUTPUT_FIELDS)
    summary = {
        "status": "completed",
        "input_images": len(rows),
        "all_images_accounted_for": len(output_rows) == len(rows),
        "near_duplicate_representatives": len(representatives),
        "selection_counts": dict(status_counts),
        "selected_direct_images": len(selected_direct),
        "selected_wcs_images": len(selected_wcs),
        "selected_negative_images": len(selected_negative),
        "direct_image_counts_by_target": dict(direct_class_counts),
        "max_direct_per_class": args.max_direct_per_class,
        "max_negative": args.max_negative,
        "source_images_modified": False,
        "automatic_training_approval": False,
        "training_ready": False,
        "reason_not_ready": "selected direct and negative candidates still require visual acceptance; WCS queue requires plate solving",
        "paths": {
            "selection_review": str(output / "selection_review.csv"),
            "selected_direct": str(output / "selected_direct.csv"),
            "selected_wcs": str(output / "selected_wcs.csv"),
            "selected_negative": str(output / "selected_negative.csv"),
            "selected_direct_labels": str(selected_label_dir),
        },
    }
    write_json(output / "summary.json", summary)
    print("Roboflow 42번 균형 선택 완료")
    print(f"전체 반영: {len(output_rows)}/{len(rows)}장")
    print(f"직접 학습 후보: {len(selected_direct)}장")
    print(f"WCS 후보: {len(selected_wcs)}장")
    print(f"음성 후보: {len(selected_negative)}장")
    print(f"유사 중복 대표: {len(representatives)}장")
    print(f"review: {output / 'selection_review.csv'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
