"""Expand reviewed AstroSmartphone labels to aligned frames in each capture group.

The stage-31 plate-solved representative and stage-32 accepted YOLO labels are
used as anchors.  Other frames from the same capture group are aligned with
phase correlation, quality-ranked, and capped per group.  Source images are
never modified.  Test-candidate sessions are excluded to avoid leakage.
"""

from __future__ import annotations

import argparse
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = PROJECT_ROOT / "data" / "results" / "astro_smartphone_inventory" / "image_inventory.csv"
DEFAULT_COVERAGE = PROJECT_ROOT / "data" / "results" / "astro_smartphone_target_coverage" / "image_target_coverage.csv"
DEFAULT_LABELS = PROJECT_ROOT / "data" / "results" / "astro_smartphone_label_review" / "accepted_labels"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_frame_expansion"
CLASS_NAMES = ["Pleiades", "Jupiter", "Betelgeuse", "Aldebaran", "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--accepted-labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-frames-per-group", type=int, default=5)
    parser.add_argument("--min-alignment-response", type=float, default=0.08)
    parser.add_argument("--max-shift-fraction", type=float, default=0.08)
    parser.add_argument("--contact-sheet-columns", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.max_frames_per_group < 1:
        raise ValueError("--max-frames-per-group은 1 이상이어야 합니다.")
    if not 0 <= args.min_alignment_response <= 1:
        raise ValueError("--min-alignment-response는 0~1이어야 합니다.")
    if not 0 < args.max_shift_fraction <= 0.25:
        raise ValueError("--max-shift-fraction은 0 초과 0.25 이하여야 합니다.")


def load_gray(path: Path, max_side: int = 900) -> tuple[np.ndarray, tuple[int, int]]:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("이미지를 읽을 수 없습니다.")
    height, width = image.shape
    scale = min(1.0, max_side / max(width, height))
    if scale < 1:
        image = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    image = cv2.GaussianBlur(image, (3, 3), 0).astype(np.float32)
    image -= float(image.mean())
    std = float(image.std())
    if std > 1e-6:
        image /= std
    window = cv2.createHanningWindow((image.shape[1], image.shape[0]), cv2.CV_32F)
    return image * window, (width, height)


def image_quality(path: Path) -> tuple[float, float, float]:
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError("이미지를 읽을 수 없습니다.")
    if max(image.shape) > 1200:
        scale = 1200 / max(image.shape)
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    sharpness = float(cv2.Laplacian(image, cv2.CV_32F).var())
    median = float(np.median(image))
    contrast = float(np.percentile(image, 99) - np.percentile(image, 10))
    return sharpness, median, contrast


def alignment(reference: Path, candidate: Path) -> tuple[float, float, float]:
    ref, ref_size = load_gray(reference)
    cand, cand_size = load_gray(candidate)
    if cand.shape != ref.shape:
        cand = cv2.resize(cand, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
    (dx_small, dy_small), response = cv2.phaseCorrelate(ref, cand)
    dx = dx_small * ref_size[0] / ref.shape[1]
    dy = dy_small * ref_size[1] / ref.shape[0]
    # Normalized shift is valid after resizing frames with the same field of view.
    return dx / ref_size[0], dy / ref_size[1], float(response)


def read_labels(path: Path) -> list[tuple[int, float, float, float, float]]:
    labels: list[tuple[int, float, float, float, float]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 5:
            raise ValueError(f"잘못된 YOLO 라벨 {path}:{line_number}")
        class_id = int(parts[0])
        values = tuple(float(value) for value in parts[1:])
        if not 0 <= class_id < len(CLASS_NAMES) or not all(0 <= value <= 1 for value in values):
            raise ValueError(f"범위를 벗어난 YOLO 라벨 {path}:{line_number}")
        labels.append((class_id, *values))
    return labels


def shifted_labels(labels: list[tuple[int, float, float, float, float]], dx: float, dy: float) -> list[tuple[int, float, float, float, float]] | None:
    result = []
    for class_id, x, y, width, height in labels:
        nx, ny = x + dx, y + dy
        if nx - width / 2 < 0 or nx + width / 2 > 1 or ny - height / 2 < 0 or ny + height / 2 > 1:
            return None
        result.append((class_id, nx, ny, width, height))
    return result


def write_label(path: Path, labels: list[tuple[int, float, float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{class_id} {x:.8f} {y:.8f} {width:.8f} {height:.8f}" for class_id, x, y, width, height in labels]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_frames(rows: list[dict[str, Any]], maximum: int) -> set[str]:
    eligible = [row for row in rows if row["alignment_status"] in {"reference", "aligned"}]
    if len(eligible) <= maximum:
        return {row["sample_id"] for row in eligible}
    reference = [row for row in eligible if row["alignment_status"] == "reference"]
    others = [row for row in eligible if row["alignment_status"] != "reference"]
    others.sort(key=lambda row: (-float(row["selection_score"]), int(row.get("burst_index") or 0)))
    selected = reference[:1]
    slots = maximum - len(selected)
    if slots > 0 and others:
        # Pick across the ranked list rather than retaining only adjacent burst frames.
        indexes = np.linspace(0, len(others) - 1, slots, dtype=int)
        selected.extend(others[index] for index in sorted(set(indexes)))
        if len(selected) < maximum:
            for row in others:
                if row not in selected:
                    selected.append(row)
                if len(selected) == maximum:
                    break
    return {row["sample_id"] for row in selected}


def contact_sheet(group_id: str, rows: list[dict[str, Any]], target: Path, columns: int) -> None:
    selected = [row for row in rows if row["selected"] == "true"]
    if not selected:
        return
    thumb_w, thumb_h, caption_h = 420, 315, 54
    rows_count = math.ceil(len(selected) / columns)
    canvas = Image.new("RGB", (columns * thumb_w, rows_count * (thumb_h + caption_h)), "#151515")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, row in enumerate(selected):
        with Image.open(row["source_path"]) as source:
            image = source.convert("RGB")
            image.thumbnail((thumb_w, thumb_h))
        x0 = (index % columns) * thumb_w + (thumb_w - image.width) // 2
        y0 = (index // columns) * (thumb_h + caption_h) + (thumb_h - image.height) // 2
        canvas.paste(image, (x0, y0))
        overlay = ImageDraw.Draw(canvas)
        for class_id, x, y, width, height in read_labels(Path(row["generated_label_path"])):
            left = x0 + (x - width / 2) * image.width
            top = y0 + (y - height / 2) * image.height
            right = x0 + (x + width / 2) * image.width
            bottom = y0 + (y + height / 2) * image.height
            overlay.rectangle((left, top, right, bottom), outline="#00ff88", width=2)
            overlay.text((left, max(y0, top - 12)), CLASS_NAMES[class_id], fill="#00ff88", font=font)
        caption_y = (index // columns) * (thumb_h + caption_h) + thumb_h
        draw.text(((index % columns) * thumb_w + 5, caption_y + 4), Path(row["source_path"]).name[:52], fill="white", font=font)
        draw.text(((index % columns) * thumb_w + 5, caption_y + 22), f"resp={row['alignment_response']} shift=({row['shift_x_norm']},{row['shift_y_norm']})", fill="#cccccc", font=font)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, quality=90)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    inventory_path, coverage_path = args.inventory.resolve(), args.coverage.resolve()
    labels_dir, output = args.accepted_labels.resolve(), args.output_dir.resolve()
    for required in (inventory_path, coverage_path):
        if not required.is_file():
            raise FileNotFoundError(f"필수 파일이 없습니다: {required}")
    if not labels_dir.is_dir():
        raise FileNotFoundError(f"승인 라벨 폴더가 없습니다: {labels_dir}")

    inventory = read_csv(inventory_path)
    coverage = {row["capture_group_id"]: row for row in read_csv(coverage_path)}
    accepted = {path.stem: path for path in labels_dir.glob("*.txt")}
    groups: dict[str, list[dict[str, str]]] = {}
    for row in inventory:
        if row.get("capture_group_id") in accepted and not row.get("read_error") and Path(row["source_path"]).suffix.lower() in IMAGE_EXTENSIONS:
            groups.setdefault(row["capture_group_id"], []).append(row)

    excluded_test_groups = [group_id for group_id in groups if coverage.get(group_id, {}).get("split_candidate") == "test_candidate"]
    groups = {group_id: rows for group_id, rows in groups.items() if group_id not in excluded_test_groups}
    print(f"확장 대상 촬영 묶음: {len(groups)}개 (Test 제외: {len(excluded_test_groups)}개)")
    if args.dry_run:
        print(f"후보 프레임: {sum(len(rows) for rows in groups.values())}장 / 묶음당 최대 {args.max_frames_per_group}장")
        return

    label_output = output / "generated_labels"
    all_rows: list[dict[str, Any]] = []
    class_selected: Counter[str] = Counter()
    group_summaries: list[dict[str, Any]] = []
    for group_number, (group_id, frames) in enumerate(sorted(groups.items()), 1):
        representative_row = next((row for row in frames if str(row.get("is_capture_representative", "")).lower() == "true"), None)
        if representative_row is None:
            reference_path = Path(coverage[group_id]["source_path"])
            representative_row = next((row for row in frames if Path(row["source_path"]) == reference_path), None)
        if representative_row is None:
            print(f"[{group_number:02d}/{len(groups):02d}] 대표 사진 없음: {group_id}")
            continue
        reference = Path(representative_row["source_path"])
        base_labels = read_labels(accepted[group_id])
        group_rows: list[dict[str, Any]] = []
        for frame_number, frame in enumerate(sorted(frames, key=lambda row: (int(row.get("burst_index") or -1), row["filename"])), 1):
            source = Path(frame["source_path"])
            sample_id = f"astroframe_{group_id}_{frame_number:02d}"
            status, error = "aligned", ""
            dx = dy = 0.0
            response = 1.0
            try:
                sharpness, median, contrast = image_quality(source)
                if source.resolve() == reference.resolve():
                    status = "reference"
                else:
                    dx, dy, response = alignment(reference, source)
                    if response < args.min_alignment_response:
                        status, error = "rejected", "low_alignment_response"
                    elif max(abs(dx), abs(dy)) > args.max_shift_fraction:
                        status, error = "rejected", "excessive_shift"
                labels = shifted_labels(base_labels, dx, dy) if status in {"reference", "aligned"} else None
                if labels is None and status in {"reference", "aligned"}:
                    status, error = "rejected", "shifted_box_outside_image"
            except Exception as exc:
                sharpness = median = contrast = 0.0
                labels = None
                status, error = "failed", f"{type(exc).__name__}: {exc}"
            score = max(0.0, response) * math.log1p(max(0.0, sharpness)) * math.log1p(max(0.0, contrast))
            label_path = label_output / f"{sample_id}.txt"
            if labels is not None:
                write_label(label_path, labels)
            row = {
                "sample_id": sample_id, "capture_group_id": group_id, "session_id": frame.get("session_id", ""),
                "source_path": str(source), "reference_path": str(reference), "filename": frame.get("filename", ""),
                "resolution_kind": frame.get("resolution_kind", ""), "burst_index": frame.get("burst_index", ""),
                "alignment_status": status, "alignment_response": round(response, 6),
                "shift_x_norm": round(dx, 8), "shift_y_norm": round(dy, 8),
                "sharpness": round(sharpness, 3), "median_brightness": round(median, 3), "contrast": round(contrast, 3),
                "selection_score": round(score, 6), "selected": "false", "review_decision": "pending",
                "review_notes": error, "generated_label_path": str(label_path) if labels is not None else "",
                "object_count": len(labels or []), "class_names": ";".join(CLASS_NAMES[item[0]] for item in (labels or [])),
            }
            group_rows.append(row)
        selected_ids = choose_frames(group_rows, args.max_frames_per_group)
        for row in group_rows:
            if row["sample_id"] in selected_ids:
                row["selected"] = "true"
                for name in row["class_names"].split(";"):
                    if name:
                        class_selected[name] += 1
            elif row["alignment_status"] in {"reference", "aligned"}:
                row["review_decision"] = "not_selected"
                row["review_notes"] = "group_frame_cap"
            else:
                row["review_decision"] = "reject"
        all_rows.extend(group_rows)
        group_summaries.append({
            "capture_group_id": group_id, "session_id": representative_row.get("session_id", ""),
            "frames_found": len(group_rows), "frames_aligned": sum(row["alignment_status"] in {"reference", "aligned"} for row in group_rows),
            "frames_selected": sum(row["selected"] == "true" for row in group_rows),
            "class_names": ";".join(sorted({name for row in group_rows for name in row["class_names"].split(";") if name})),
        })
        contact_sheet(group_id, group_rows, output / "contact_sheets" / f"{group_id}.jpg", args.contact_sheet_columns)
        print(f"[{group_number:02d}/{len(groups):02d}] {group_id}: {group_summaries[-1]['frames_selected']}/{len(group_rows)}장 선택")

    fields = list(all_rows[0].keys()) if all_rows else ["sample_id"]
    write_csv(output / "frame_review.csv", all_rows, fields)
    write_csv(output / "group_summary.csv", group_summaries, list(group_summaries[0].keys()) if group_summaries else ["capture_group_id"])
    selected = [row for row in all_rows if row["selected"] == "true"]
    summary = {
        "status": "completed", "capture_groups": len(groups), "excluded_test_groups": len(excluded_test_groups),
        "candidate_frames": len(all_rows), "aligned_frames": sum(row["alignment_status"] in {"reference", "aligned"} for row in all_rows),
        "selected_frames": len(selected), "selected_sessions": len({row["session_id"] for row in selected}),
        "max_frames_per_group": args.max_frames_per_group, "class_selected_images": dict(class_selected),
        "pending_review": sum(row["review_decision"] == "pending" for row in selected), "training_ready": False,
        "source_images_modified": False,
        "next_action": "Inspect contact sheets, set selected rows to accept/reject in frame_review.csv, then rerun stage 45 with a future apply-review option or merge in stage 46.",
        "paths": {"review": str(output / "frame_review.csv"), "group_summary": str(output / "group_summary.csv"), "labels": str(label_output), "contact_sheets": str(output / "contact_sheets")},
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output / "summary.json", summary)
    print("45번 AstroSmartphone 연속 프레임 확장 완료")
    print(f"후보: {len(all_rows)}장 / 정렬 성공: {summary['aligned_frames']}장 / 선택: {len(selected)}장")
    print(f"검토 대기: {summary['pending_review']}장")
    print(f"review: {output / 'frame_review.csv'}")
    print(f"contact_sheets: {output / 'contact_sheets'}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
