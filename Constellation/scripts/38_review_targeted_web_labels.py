"""Review stage-37 TargetedWeb objects and export explicitly approved labels.

The script preserves decisions across reruns. Set ``review_decision`` to
``accept`` or ``reject`` in object_review.csv and negative_review.csv, then
rerun it. Automatic WCS/SNR recommendations never become training labels
without an explicit decision.
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
DEFAULT_STAGE37 = PROJECT_ROOT / "data" / "results" / "targeted_web_wcs_labels"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "targeted_web_label_review"
DECISIONS = {"", "accept", "reject"}
BOX_SIZES = {
    "Pleiades": (0.035, 0.035),
    "Jupiter": (0.020, 0.020),
    "Betelgeuse": (0.020, 0.015),
    "Aldebaran": (0.020, 0.015),
    "Zeta Tauri": (0.020, 0.015),
    "Elnath": (0.020, 0.015),
    "Hassaleh": (0.020, 0.015),
    "Bellatrix": (0.020, 0.015),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage37-dir", type=Path, default=DEFAULT_STAGE37)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sheet-columns", type=int, default=4)
    return parser.parse_args()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def decision(value: Any) -> str:
    result = str(value or "").strip().lower()
    return result if result in DECISIONS else ""


def previous_by_key(path: Path, fields: tuple[str, ...]) -> dict[tuple[str, ...], dict[str, str]]:
    if not path.is_file():
        return {}
    return {tuple(row.get(field, "") for field in fields): row for row in read_csv(path)}


def crop_target(image_path: Path, item: dict[str, Any], size: int = 300) -> Image.Image:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    x, y = float(item["pixel_x"]), float(item["pixel_y"])
    cluster = item["class_name"] == "Pleiades"
    radius = max(80, int(round(min(image.size) * (0.075 if cluster else 0.045))))
    crop = image.crop(
        (
            max(0, int(x - radius)),
            max(0, int(y - radius)),
            min(image.width, int(x + radius)),
            min(image.height, int(y + radius)),
        )
    )
    draw = ImageDraw.Draw(crop)
    cx, cy = x - max(0, int(x - radius)), y - max(0, int(y - radius))
    color = "#22c55e" if item["review_decision"] == "accept" else (
        "#ef4444" if item["review_decision"] == "reject" else "#facc15"
    )
    marker = max(5, min(crop.size) // 30)
    draw.ellipse((cx - marker, cy - marker, cx + marker, cy + marker), outline=color, width=2)
    draw.line((cx - marker * 2, cy, cx + marker * 2, cy), fill=color, width=1)
    draw.line((cx, cy - marker * 2, cx, cy + marker * 2), fill=color, width=1)
    return ImageOps.contain(crop, (size, size))


def object_contact_sheet(
    items: list[dict[str, Any]], output: Path, columns: int
) -> None:
    if not items:
        return
    cell_w, cell_h, image_size = 350, 400, 300
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(items):
        left, top = (index % columns) * cell_w, (index // columns) * cell_h
        try:
            crop = crop_target(Path(item["source_path"]), item, image_size)
            sheet.paste(crop, (left + (cell_w - crop.width) // 2, top + 5))
        except Exception as error:
            draw.text((left + 8, top + 20), str(error)[:45], fill="#ef4444", font=font)
        lines = [
            f'#{item["review_index"]} {item["class_name"]} SNR={float(item["point_source_snr"]):.2f}',
            f'auto={item["automatic_recommendation"]} decision={item["review_decision"] or "PENDING"}',
            item["item_id"][:47],
            item.get("title", "")[:47],
        ]
        draw.multiline_text((left + 8, top + 310), "\n".join(lines), fill="white", font=font, spacing=3)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def negative_contact_sheet(items: list[dict[str, Any]], output: Path, columns: int) -> None:
    if not items:
        return
    cell_w, cell_h = 360, 320
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(items):
        left, top = (index % columns) * cell_w, (index // columns) * cell_h
        try:
            with Image.open(item["source_path"]) as source:
                thumb = ImageOps.contain(source.convert("RGB"), (340, 250))
            sheet.paste(thumb, (left + (cell_w - thumb.width) // 2, top + 5))
        except Exception as error:
            draw.text((left + 8, top + 20), str(error)[:45], fill="#ef4444", font=font)
        text = (
            f'#{item["review_index"]} decision={item["review_decision"] or "PENDING"}\n'
            f'{item["item_id"][:45]}\n{item.get("title", "")[:45]}'
        )
        draw.multiline_text((left + 8, top + 260), text, fill="white", font=font, spacing=3)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def draw_image_overlay(image_path: Path, output: Path, items: list[dict[str, Any]]) -> None:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    width = max(2, min(image.size) // 500)
    for item in items:
        x, y = float(item["pixel_x"]), float(item["pixel_y"])
        bw, bh = BOX_SIZES[item["class_name"]]
        half_w, half_h = image.width * bw / 2, image.height * bh / 2
        color = "#22c55e" if item["review_decision"] == "accept" else (
            "#ef4444" if item["review_decision"] == "reject" else "#facc15"
        )
        draw.rectangle((x - half_w, y - half_h, x + half_w, y + half_h), outline=color, width=width)
        draw.text(
            (x + half_w + 3, max(0, y - half_h)),
            f'{item["class_name"]} {item["review_decision"] or "PENDING"}',
            fill=color,
            font=font,
            stroke_width=1,
            stroke_fill="black",
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=92)


def export_approved(
    objects: list[dict[str, Any]], negatives: list[dict[str, Any]], output: Path
) -> tuple[int, int, int]:
    labels_dir = output / "accepted_labels"
    labels_dir.mkdir(parents=True, exist_ok=True)
    for old in labels_dir.glob("*.txt"):
        old.unlink()
    by_image: dict[str, list[dict[str, Any]]] = {}
    for item in objects:
        if item["review_decision"] == "accept":
            by_image.setdefault(item["item_id"], []).append(item)
    for item_id, accepted in by_image.items():
        lines: list[str] = []
        for item in accepted:
            x = min(1.0, max(0.0, float(item["pixel_x"]) / int(item["image_width"])))
            y = min(1.0, max(0.0, float(item["pixel_y"]) / int(item["image_height"])))
            bw, bh = BOX_SIZES[item["class_name"]]
            lines.append(f'{int(item["class_id"])} {x:.8f} {y:.8f} {bw:.8f} {bh:.8f}')
        (labels_dir / f"{item_id}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    accepted_negatives = [item for item in negatives if item["review_decision"] == "accept"]
    for item in accepted_negatives:
        (labels_dir / f'{item["item_id"]}.txt').write_text("", encoding="utf-8")
    return len(by_image), sum(len(items) for items in by_image.values()), len(accepted_negatives)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.sheet_columns < 1:
        raise ValueError("--sheet-columns는 1 이상이어야 합니다.")
    stage37, output = args.stage37_dir.resolve(), args.output_dir.resolve()
    manifest_path, projected_path = stage37 / "manifest.csv", stage37 / "projected_objects.csv"
    if not manifest_path.is_file() or not projected_path.is_file():
        raise FileNotFoundError("37번 manifest.csv 또는 projected_objects.csv가 없습니다.")

    manifests = {row["item_id"]: row for row in read_csv(manifest_path)}
    object_review_path, negative_review_path = output / "object_review.csv", output / "negative_review.csv"
    previous_objects = previous_by_key(object_review_path, ("item_id", "class_name"))
    previous_negatives = previous_by_key(negative_review_path, ("item_id",))

    objects: list[dict[str, Any]] = []
    for target in read_csv(projected_path):
        if not truthy(target.get("inside_fov")):
            continue
        manifest = manifests.get(target["item_id"])
        if not manifest or not Path(manifest["image_path"]).is_file():
            continue
        old = previous_objects.get((target["item_id"], target["class_name"]), {})
        objects.append(
            {
                "review_index": len(objects) + 1,
                "item_id": target["item_id"],
                "filename": target["filename"],
                "query_group": target.get("query_group", ""),
                "title": manifest.get("title", ""),
                "source_path": manifest["image_path"],
                "class_id": target["class_id"],
                "class_name": target["class_name"],
                "pixel_x": target["pixel_x"],
                "pixel_y": target["pixel_y"],
                "point_source_snr": target["point_source_snr"],
                "automatic_recommendation": "likely_visible" if truthy(target.get("auto_verified")) else "low_snr_review",
                "image_width": manifest["image_width"],
                "image_height": manifest["image_height"],
                "review_decision": decision(old.get("review_decision", "")),
                "review_notes": old.get("review_notes", ""),
            }
        )

    negatives: list[dict[str, Any]] = []
    for manifest in manifests.values():
        if not truthy(manifest.get("verified_negative_candidate")) or manifest.get("processing_status") != "success":
            continue
        old = previous_negatives.get((manifest["item_id"],), {})
        negatives.append(
            {
                "review_index": len(negatives) + 1,
                "item_id": manifest["item_id"],
                "filename": manifest["filename"],
                "query_group": manifest.get("query_group", ""),
                "title": manifest.get("title", ""),
                "source_path": manifest["image_path"],
                "wcs_path": manifest["wcs_path"],
                "automatic_recommendation": "verified_negative_candidate",
                "review_decision": decision(old.get("review_decision", "")),
                "review_notes": old.get("review_notes", ""),
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    object_fields = list(objects[0].keys()) if objects else []
    negative_fields = list(negatives[0].keys()) if negatives else []
    write_csv(object_review_path, objects, object_fields)
    write_csv(negative_review_path, negatives, negative_fields)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in objects:
        grouped.setdefault(item["item_id"], []).append(item)
    for item_id, items in grouped.items():
        draw_image_overlay(Path(items[0]["source_path"]), output / "overlays" / f"{item_id}_review.jpg", items)
    object_contact_sheet(objects, output / "contact_sheets" / "all_objects.jpg", args.sheet_columns)
    for class_name in BOX_SIZES:
        object_contact_sheet(
            [item for item in objects if item["class_name"] == class_name],
            output / "contact_sheets" / f'{class_name.lower().replace(" ", "_")}.jpg',
            args.sheet_columns,
        )
    negative_contact_sheet(negatives, output / "contact_sheets" / "negative_candidates.jpg", args.sheet_columns)

    accepted_images, accepted_objects, accepted_negatives = export_approved(objects, negatives, output)
    object_counts = Counter(item["review_decision"] or "pending" for item in objects)
    negative_counts = Counter(item["review_decision"] or "pending" for item in negatives)
    class_counts = {
        name: dict(Counter(item["review_decision"] or "pending" for item in objects if item["class_name"] == name))
        for name in BOX_SIZES
    }
    pending = object_counts.get("pending", 0) + negative_counts.get("pending", 0)
    summary = {
        "status": "completed",
        "candidate_images_with_targets": len(grouped),
        "candidate_objects": len(objects),
        "negative_candidate_images": len(negatives),
        "object_review_counts": dict(sorted(object_counts.items())),
        "negative_review_counts": dict(sorted(negative_counts.items())),
        "class_review_counts": class_counts,
        "accepted_positive_images": accepted_images,
        "accepted_objects": accepted_objects,
        "accepted_negative_images": accepted_negatives,
        "review_pending_total": pending,
        "training_ready": bool(objects or negatives) and pending == 0,
        "source_images_modified": False,
        "instructions": "Inspect contact sheets, set every review_decision to accept or reject, then rerun stage 38.",
        "paths": {
            "object_review": str(object_review_path),
            "negative_review": str(negative_review_path),
            "accepted_labels": str(output / "accepted_labels"),
            "contact_sheets": str(output / "contact_sheets"),
            "overlays": str(output / "overlays"),
        },
    }
    write_json(output / "summary.json", summary)
    print("TargetedWeb 라벨 검토 자료 생성 완료")
    print(f"양성 사진: {len(grouped)}장 / 객체 후보: {len(objects)}개")
    print(f"음성 사진 후보: {len(negatives)}장")
    print(f"객체 - 대기: {object_counts.get('pending', 0)} / 승인: {object_counts.get('accept', 0)} / 거절: {object_counts.get('reject', 0)}")
    print(f"음성 - 대기: {negative_counts.get('pending', 0)} / 승인: {negative_counts.get('accept', 0)} / 거절: {negative_counts.get('reject', 0)}")
    print(f"training_ready: {summary['training_ready']}")
    print(f"object_review: {object_review_path}")
    print(f"negative_review: {negative_review_path}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
