"""Create review artifacts and approved YOLO labels for stage-31 candidates.

The script preserves manual decisions in ``object_review.csv`` across reruns.
Set ``review_decision`` to ``accept`` or ``reject`` for every projected object,
then rerun this script.  Only accepted objects are exported to
``accepted_labels``; automatic SNR recommendations never become training labels
without an explicit review decision.
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
DEFAULT_COVERAGE = PROJECT_ROOT / "data" / "results" / "astro_smartphone_target_coverage"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_label_review"
DECISIONS = {"", "accept", "reject"}
BOX_SIZES = {
    "Pleiades": (0.035, 0.035),
    "Jupiter": (0.020, 0.015),
    "Betelgeuse": (0.020, 0.015),
    "Aldebaran": (0.020, 0.015),
    "Zeta Tauri": (0.020, 0.015),
    "Elnath": (0.020, 0.015),
    "Hassaleh": (0.020, 0.015),
    "Bellatrix": (0.020, 0.015),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage-dir", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sheet-columns", type=int, default=4)
    return parser.parse_args()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def safe_float(value: Any) -> float:
    return float(str(value).strip())


def load_previous(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.is_file():
        return {}
    return {(row.get("capture_group_id", ""), row.get("class_name", "")): row for row in read_csv(path)}


def draw_overlay(image_path: Path, output: Path, candidates: list[dict[str, Any]]) -> None:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    line_width = max(3, image.width // 500)
    for item in candidates:
        x, y = safe_float(item["pixel_x"]), safe_float(item["pixel_y"])
        bw, bh = BOX_SIZES[item["class_name"]]
        half_w, half_h = image.width * bw / 2, image.height * bh / 2
        decision = item["review_decision"]
        color = "#22c55e" if decision == "accept" else ("#ef4444" if decision == "reject" else "#facc15")
        draw.rectangle((x - half_w, y - half_h, x + half_w, y + half_h), outline=color, width=line_width)
        label = f'{item["class_name"]} SNR={float(item["point_source_snr"]):.1f} {decision or "PENDING"}'
        draw.text((x + half_w + 4, max(0, y - half_h)), label, fill=color, font=font, stroke_width=1, stroke_fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=90)


def target_crop(image_path: Path, item: dict[str, Any], size: int = 260) -> Image.Image:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    x, y = safe_float(item["pixel_x"]), safe_float(item["pixel_y"])
    radius = max(70, int(round(min(image.size) * (0.06 if item["class_name"] == "Pleiades" else 0.035))))
    crop = image.crop((max(0, int(x - radius)), max(0, int(y - radius)), min(image.width, int(x + radius)), min(image.height, int(y + radius))))
    return ImageOps.contain(crop, (size, size))


def contact_sheet(items: list[dict[str, Any]], image_paths: dict[str, Path], output: Path, columns: int) -> None:
    if not items:
        return
    cell_w, cell_h = 300, 340
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (cell_w * columns, cell_h * rows), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, item in enumerate(items):
        left, top = (index % columns) * cell_w, (index // columns) * cell_h
        try:
            crop = target_crop(image_paths[item["capture_group_id"]], item)
            sheet.paste(crop, (left + 20 + (260 - crop.width) // 2, top + 8 + (260 - crop.height) // 2))
        except Exception:
            pass
        draw.text((left + 10, top + 274), f'{index + 1:03d} {item["class_name"]}', fill="#facc15", font=font)
        draw.text((left + 10, top + 291), f'SNR={float(item["point_source_snr"]):.2f} auto={item["automatic_recommendation"]}', fill="white", font=font)
        draw.text((left + 10, top + 308), item["capture_group_id"][:38], fill="#93c5fd", font=font)
        draw.text((left + 10, top + 325), f'decision={item["review_decision"] or "PENDING"}', fill="#86efac", font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)


def write_accepted_labels(items: list[dict[str, Any]], output: Path) -> tuple[int, int]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if item["review_decision"] == "accept":
            grouped.setdefault(item["capture_group_id"], []).append(item)
    labels = output / "accepted_labels"
    labels.mkdir(parents=True, exist_ok=True)
    for old in labels.glob("*.txt"):
        old.unlink()
    for capture_id, accepted in grouped.items():
        lines = []
        for item in accepted:
            width, height = int(item["image_width"]), int(item["image_height"])
            x = min(1.0, max(0.0, safe_float(item["pixel_x"]) / width))
            y = min(1.0, max(0.0, safe_float(item["pixel_y"]) / height))
            bw, bh = BOX_SIZES[item["class_name"]]
            lines.append(f'{int(item["class_id"])} {x:.8f} {y:.8f} {bw:.8f} {bh:.8f}')
        (labels / f"{capture_id}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(grouped), sum(len(values) for values in grouped.values())


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    if args.sheet_columns <= 0:
        raise ValueError("--sheet-columns는 1 이상이어야 합니다.")
    coverage = args.coverage_dir.resolve()
    output = args.output_dir.resolve()
    images_csv = coverage / "image_target_coverage.csv"
    targets_csv = coverage / "projected_targets.csv"
    if not images_csv.is_file() or not targets_csv.is_file():
        raise FileNotFoundError("31번 결과 CSV를 찾을 수 없습니다.")

    images = {row["capture_group_id"]: row for row in read_csv(images_csv)}
    image_paths = {key: Path(row["source_path"]) for key, row in images.items()}
    review_path = output / "object_review.csv"
    previous = load_previous(review_path)
    candidates: list[dict[str, Any]] = []
    for target in read_csv(targets_csv):
        if not truthy(target.get("inside_fov")):
            continue
        image_row = images.get(target["capture_group_id"])
        if not image_row or not Path(image_row["source_path"]).is_file():
            continue
        old = previous.get((target["capture_group_id"], target["class_name"]), {})
        decision = old.get("review_decision", "").strip().lower()
        if decision not in DECISIONS:
            decision = ""
        with Image.open(image_row["source_path"]) as image:
            width, height = image.size
        candidates.append({
            "review_index": len(candidates) + 1,
            "capture_group_id": target["capture_group_id"], "session_id": target["session_id"],
            "filename": target["filename"], "source_path": image_row["source_path"],
            "split_candidate": target["split_candidate"], "class_id": target["class_id"], "class_name": target["class_name"],
            "pixel_x": target["pixel_x"], "pixel_y": target["pixel_y"],
            "point_source_snr": target["point_source_snr"], "automatic_recommendation": "likely_visible" if truthy(target.get("visually_verified")) else "low_snr_review",
            "image_width": width, "image_height": height,
            "review_decision": decision, "review_notes": old.get("review_notes", ""),
        })

    output.mkdir(parents=True, exist_ok=True)
    fields = list(candidates[0].keys()) if candidates else []
    write_csv(review_path, candidates, fields)
    by_image: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        by_image.setdefault(item["capture_group_id"], []).append(item)
    for capture_id, items in by_image.items():
        draw_overlay(image_paths[capture_id], output / "overlays" / f"{capture_id}_targets.jpg", items)
    contact_sheet(candidates, image_paths, output / "contact_sheets" / "all_candidates.jpg", args.sheet_columns)
    for class_name in BOX_SIZES:
        contact_sheet([item for item in candidates if item["class_name"] == class_name], image_paths, output / "contact_sheets" / f"{class_name.replace(' ', '_').lower()}.jpg", args.sheet_columns)
    accepted_images, accepted_objects = write_accepted_labels(candidates, output)
    counts = Counter(item["review_decision"] or "pending" for item in candidates)
    class_counts = {name: dict(Counter(item["review_decision"] or "pending" for item in candidates if item["class_name"] == name)) for name in BOX_SIZES}
    summary = {
        "candidate_images": len(by_image), "candidate_objects": len(candidates),
        "review_counts": dict(sorted(counts.items())), "class_review_counts": class_counts,
        "accepted_label_images": accepted_images, "accepted_objects": accepted_objects,
        "training_ready": bool(candidates) and counts.get("pending", 0) == 0,
        "source_images_modified": False,
        "instructions": "Inspect contact sheets/overlays, set review_decision to accept or reject, then rerun stage 32.",
    }
    write_json(output / "summary.json", summary)
    print("AstroSmartphone WCS 라벨 검토 자료 생성 완료")
    print(f"검토 사진: {len(by_image)}장 / 객체 후보: {len(candidates)}개")
    print(f"대기: {counts.get('pending', 0)} / 승인: {counts.get('accept', 0)} / 거절: {counts.get('reject', 0)}")
    print(f"review: {review_path}")
    print(f"contact_sheets: {output / 'contact_sheets'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
