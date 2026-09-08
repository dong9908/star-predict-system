"""Create visual review artifacts for stage-42 Roboflow candidates.

Direct candidates are rendered with their converted eight-class YOLO boxes.
Negative candidates are rendered without boxes so reviewers can verify that
none of the eight targets is present. Decisions survive reruns. Only explicit
``accept`` decisions are exported; no candidate is automatically approved.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE42 = PROJECT_ROOT / "data" / "results" / "roboflow_training_selection"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "roboflow_candidate_review"
TARGET_CLASSES = (
    "Pleiades", "Jupiter", "Betelgeuse", "Aldebaran",
    "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix",
)
COLORS = ("#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#e879f9", "#a3e635", "#fb7185", "#60a5fa")
DECISIONS = {"", "accept", "reject"}
VISUAL_TYPES = {"", "real_sky", "simulation", "diagram", "celestial_closeup", "invalid"}
DIRECT_FIELDS = [
    "review_index", "sample_id", "dataset", "source_split", "image_path",
    "converted_label_path", "target_candidates", "object_count", "visual_type",
    "box_quality", "review_decision", "review_notes", "license", "source_url",
]
NEGATIVE_FIELDS = [
    "review_index", "sample_id", "dataset", "source_split", "image_path",
    "target_candidates", "visual_type", "target_absent", "review_decision",
    "review_notes", "license", "source_url",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage42-dir", type=Path, default=DEFAULT_STAGE42)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sheet-columns", type=int, default=6)
    parser.add_argument("--sheet-rows", type=int, default=5)
    return parser.parse_args()


def normalize_decision(value: Any) -> str:
    result = str(value or "").strip().lower()
    return result if result in DECISIONS else ""


def normalize_visual_type(value: Any) -> str:
    result = str(value or "").strip().lower()
    return result if result in VISUAL_TYPES else ""


def previous(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    return {row["sample_id"]: row for row in read_csv(path)}


def parse_boxes(path: Path) -> list[tuple[int, float, float, float, float]]:
    boxes: list[tuple[int, float, float, float, float]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 5:
            raise ValueError(f"{path}:{line_number} YOLO 열 수 오류")
        class_id = int(parts[0])
        values = [float(value) for value in parts[1:]]
        if not 0 <= class_id < len(TARGET_CLASSES):
            raise ValueError(f"{path}:{line_number} 클래스 오류")
        if not all(0 <= value <= 1 for value in values) or values[2] <= 0 or values[3] <= 0:
            raise ValueError(f"{path}:{line_number} 좌표 오류")
        boxes.append((class_id, *values))
    if not boxes:
        raise ValueError(f"직접 후보 라벨이 비어 있습니다: {path}")
    return boxes


def overlay(image_path: Path, label_path: Path) -> Image.Image:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    line_width = max(2, min(image.size) // 350)
    for class_id, x, y, width, height in parse_boxes(label_path):
        left = (x - width / 2) * image.width
        top = (y - height / 2) * image.height
        right = (x + width / 2) * image.width
        bottom = (y + height / 2) * image.height
        color = COLORS[class_id]
        draw.rectangle((left, top, right, bottom), outline=color, width=line_width)
        label = TARGET_CLASSES[class_id]
        text_box = draw.textbbox((0, 0), label, font=font, stroke_width=1)
        text_w, text_h = text_box[2] - text_box[0], text_box[3] - text_box[1]
        text_y = max(0, top - text_h - 4)
        draw.rectangle((left, text_y, left + text_w + 6, text_y + text_h + 4), fill="black")
        draw.text((left + 3, text_y + 2), label, fill=color, font=font, stroke_width=1, stroke_fill="black")
    return image


def save_overlay(image_path: Path, label_path: Path, output: Path) -> None:
    image = overlay(image_path, label_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=92)


def make_sheets(
    rows: list[dict[str, Any]], output: Path, columns: int, sheet_rows: int, direct: bool
) -> int:
    if not rows:
        return 0
    per_page = columns * sheet_rows
    cell_w, cell_h = 260, 215
    font = ImageFont.load_default()
    output.mkdir(parents=True, exist_ok=True)
    pages = 0
    for start in range(0, len(rows), per_page):
        pages += 1
        items = rows[start:start + per_page]
        sheet = Image.new("RGB", (columns * cell_w, sheet_rows * cell_h), "#111827")
        draw = ImageDraw.Draw(sheet)
        for offset, row in enumerate(items):
            left, top = (offset % columns) * cell_w, (offset // columns) * cell_h
            try:
                if direct:
                    image = overlay(Path(row["image_path"]), Path(row["converted_label_path"]))
                else:
                    with Image.open(row["image_path"]) as source:
                        image = source.convert("RGB")
                thumb = ImageOps.contain(image, (250, 165))
                sheet.paste(thumb, (left + (cell_w - thumb.width) // 2, top + 3))
            except Exception as error:
                draw.rectangle((left + 5, top + 5, left + 255, top + 165), fill="#7f1d1d")
                draw.text((left + 8, top + 20), str(error)[:35], fill="white", font=font)
            decision = row.get("review_decision", "") or "PENDING"
            color = "#22c55e" if decision == "accept" else ("#ef4444" if decision == "reject" else "#facc15")
            line1 = f'#{row["review_index"]} {row["dataset"][:22]}'
            line2 = f'{row.get("target_candidates", "negative")[:29] or "negative"}'
            line3 = f'{decision} / {row.get("visual_type", "") or "type?"}'
            draw.multiline_text((left + 5, top + 170), f"{line1}\n{line2}\n{line3}", fill=color, font=font, spacing=1)
        sheet.save(output / f"page_{pages:03d}.jpg", quality=90)
    return pages


def export_accepted(direct: list[dict[str, Any]], negatives: list[dict[str, Any]], output: Path) -> tuple[int, int]:
    labels = output / "accepted_labels"
    labels.mkdir(parents=True, exist_ok=True)
    for old in labels.glob("*.txt"):
        old.unlink()
    accepted_direct = 0
    accepted_negative = 0
    for row in direct:
        if row["review_decision"] != "accept":
            continue
        source = Path(row["converted_label_path"])
        (labels / f'{row["review_index"]:04d}_direct.txt').write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
        accepted_direct += 1
    for row in negatives:
        if row["review_decision"] != "accept":
            continue
        (labels / f'{row["review_index"]:04d}_negative.txt').write_text("", encoding="utf-8")
        accepted_negative += 1
    return accepted_direct, accepted_negative


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.sheet_columns < 1 or args.sheet_rows < 1:
        raise ValueError("연락처 시트 행과 열은 1 이상이어야 합니다.")
    stage42, output = args.stage42_dir.resolve(), args.output_dir.resolve()
    direct_source = stage42 / "selected_direct.csv"
    negative_source = stage42 / "selected_negative.csv"
    if not direct_source.is_file() or not negative_source.is_file():
        raise FileNotFoundError("42번 selected_direct.csv 또는 selected_negative.csv가 없습니다.")
    source_direct, source_negatives = read_csv(direct_source), read_csv(negative_source)
    direct_path, negative_path = output / "direct_review.csv", output / "negative_review.csv"
    old_direct, old_negatives = previous(direct_path), previous(negative_path)

    direct: list[dict[str, Any]] = []
    for index, row in enumerate(source_direct, 1):
        old = old_direct.get(row["sample_id"], {})
        label_path = Path(row["converted_label_path"])
        image_path = Path(row["image_path"])
        if not label_path.is_file() or not image_path.is_file():
            raise FileNotFoundError(f"직접 후보 입력 누락: {image_path} / {label_path}")
        boxes = parse_boxes(label_path)
        actual_targets = "|".join(
            TARGET_CLASSES[class_id] for class_id in sorted({box[0] for box in boxes})
        )
        direct.append({
            "review_index": index, "sample_id": row["sample_id"], "dataset": row["dataset"],
            "source_split": row["source_split"], "image_path": str(image_path),
            "converted_label_path": str(label_path), "target_candidates": actual_targets,
            "object_count": len(boxes), "visual_type": normalize_visual_type(old.get("visual_type", "")),
            "box_quality": old.get("box_quality", ""),
            "review_decision": normalize_decision(old.get("review_decision", "")),
            "review_notes": old.get("review_notes", ""), "license": row.get("license", ""),
            "source_url": row.get("source_url", ""),
        })

    negatives: list[dict[str, Any]] = []
    for index, row in enumerate(source_negatives, 1):
        old = old_negatives.get(row["sample_id"], {})
        image_path = Path(row["image_path"])
        if not image_path.is_file():
            raise FileNotFoundError(f"음성 후보 입력 누락: {image_path}")
        negatives.append({
            "review_index": index, "sample_id": row["sample_id"], "dataset": row["dataset"],
            "source_split": row["source_split"], "image_path": str(image_path),
            "target_candidates": row.get("target_candidates", ""),
            "visual_type": normalize_visual_type(old.get("visual_type", "")),
            "target_absent": old.get("target_absent", ""),
            "review_decision": normalize_decision(old.get("review_decision", "")),
            "review_notes": old.get("review_notes", ""), "license": row.get("license", ""),
            "source_url": row.get("source_url", ""),
        })

    output.mkdir(parents=True, exist_ok=True)
    write_csv(direct_path, direct, DIRECT_FIELDS)
    write_csv(negative_path, negatives, NEGATIVE_FIELDS)
    overlay_dir = output / "direct_overlays"
    for row in direct:
        save_overlay(Path(row["image_path"]), Path(row["converted_label_path"]), overlay_dir / f'{row["review_index"]:04d}.jpg')
    direct_pages = make_sheets(direct, output / "contact_sheets" / "direct", args.sheet_columns, args.sheet_rows, True)
    negative_pages = make_sheets(negatives, output / "contact_sheets" / "negative", args.sheet_columns, args.sheet_rows, False)
    accepted_direct, accepted_negative = export_accepted(direct, negatives, output)
    direct_counts = Counter(row["review_decision"] or "pending" for row in direct)
    negative_counts = Counter(row["review_decision"] or "pending" for row in negatives)
    pending = direct_counts["pending"] + negative_counts["pending"]
    summary = {
        "status": "completed", "direct_candidates": len(direct), "negative_candidates": len(negatives),
        "direct_review_counts": dict(direct_counts), "negative_review_counts": dict(negative_counts),
        "accepted_direct": accepted_direct, "accepted_negative": accepted_negative,
        "review_pending_total": pending, "contact_sheet_pages": direct_pages + negative_pages,
        "direct_contact_sheet_pages": direct_pages, "negative_contact_sheet_pages": negative_pages,
        "training_ready": pending == 0 and (accepted_direct + accepted_negative) > 0,
        "source_images_modified": False,
        "instructions": "Inspect contact sheets; fill visual_type, box_quality/target_absent, review_decision=accept|reject; rerun stage 44.",
        "paths": {
            "direct_review": str(direct_path), "negative_review": str(negative_path),
            "accepted_labels": str(output / "accepted_labels"), "direct_overlays": str(overlay_dir),
            "contact_sheets": str(output / "contact_sheets"),
        },
    }
    write_json(output / "summary.json", summary)
    print("Roboflow 44번 시각 검토 자료 생성 완료")
    print(f"직접 후보: {len(direct)}장 / 음성 후보: {len(negatives)}장")
    print(f"연락처 시트: 직접 {direct_pages}페이지 / 음성 {negative_pages}페이지")
    print(f"판정 대기: {pending}장 / 승인: {accepted_direct + accepted_negative}장")
    print(f"training_ready: {summary['training_ready']}")
    print(f"direct_review: {direct_path}")
    print(f"negative_review: {negative_path}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
