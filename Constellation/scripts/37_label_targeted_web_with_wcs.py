"""Create reviewable YOLO candidates from stage-36 TargetedWeb WCS results.

Only images with a successful, existing WCS solution are processed. Fixed
ICRS targets are projected into each image and checked for a local point-source
signal. Jupiter is projected only when a trustworthy capture timestamp exists.
All outputs remain review candidates; stage 38 must approve them before they
are merged into a training dataset.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from astropy.coordinates import get_body
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image, ImageDraw, ImageFont, ImageOps

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATE_RESULTS = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "targeted_web_plate_solving"
    / "plate_solve_results.csv"
)
DEFAULT_CLASSIFICATION = (
    PROJECT_ROOT
    / "data"
    / "results"
    / "targeted_web_classification"
    / "classification.csv"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "targeted_web_wcs_labels"
SUCCESS_STATUSES = {"success", "cached_success"}
CLASS_NAMES = [
    "Pleiades",
    "Jupiter",
    "Betelgeuse",
    "Aldebaran",
    "Zeta Tauri",
    "Elnath",
    "Hassaleh",
    "Bellatrix",
]

# class_id, name, ICRS/J2000 RA, DEC, normalized box width/height, cluster
TARGETS = [
    (0, "Pleiades", 56.75000, 24.11670, 0.035, 0.035, True),
    (1, "Jupiter", None, None, 0.020, 0.020, False),
    (2, "Betelgeuse", 88.79294, 7.40706, 0.020, 0.015, False),
    (3, "Aldebaran", 68.98016, 16.50930, 0.020, 0.015, False),
    (4, "Zeta Tauri", 84.41119, 21.14255, 0.020, 0.015, False),
    (5, "Elnath", 81.57297, 28.60745, 0.020, 0.015, False),
    (6, "Hassaleh", 74.24842, 33.16610, 0.020, 0.015, False),
    (7, "Bellatrix", 81.28276, 6.34970, 0.020, 0.015, False),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plate-results", type=Path, default=DEFAULT_PLATE_RESULTS)
    parser.add_argument("--classification", type=Path, default=DEFAULT_CLASSIFICATION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-snr", type=float, default=3.5)
    parser.add_argument("--edge-margin", type=float, default=0.01)
    parser.add_argument("--contact-sheet-columns", type=int, default=4)
    parser.add_argument("--force", action="store_true", help="Overwrite generated labels and overlays")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.min_snr < 0:
        raise ValueError("--min-snr은 0 이상이어야 합니다.")
    if not 0 <= args.edge_margin < 0.25:
        raise ValueError("--edge-margin은 0 이상 0.25 미만이어야 합니다.")
    if args.contact_sheet_columns < 1:
        raise ValueError("--contact-sheet-columns는 1 이상이어야 합니다.")


def parse_capture_time(value: str) -> Time | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return Time(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except (ValueError, TypeError):
        return None


def target_coordinates(captured_at: str) -> list[dict[str, Any]]:
    capture_time = parse_capture_time(captured_at)
    coordinates: list[dict[str, Any]] = []
    for class_id, name, ra, dec, box_w, box_h, cluster in TARGETS:
        source = "fixed_icrs_j2000"
        if name == "Jupiter":
            if capture_time is None:
                coordinates.append(
                    {
                        "class_id": class_id,
                        "class_name": name,
                        "ra": "",
                        "dec": "",
                        "box_w": box_w,
                        "box_h": box_h,
                        "cluster": cluster,
                        "coordinate_source": "capture_time_missing",
                    }
                )
                continue
            body = get_body("jupiter", capture_time).icrs
            ra, dec = float(body.ra.deg), float(body.dec.deg)
            source = "astropy_builtin_ephemeris"
        coordinates.append(
            {
                "class_id": class_id,
                "class_name": name,
                "ra": float(ra),
                "dec": float(dec),
                "box_w": box_w,
                "box_h": box_h,
                "cluster": cluster,
                "coordinate_source": source,
            }
        )
    return coordinates


def point_source_snr(gray: np.ndarray, x: float, y: float, cluster: bool) -> float:
    radius = max(5, int(round(min(gray.shape) * (0.018 if cluster else 0.008))))
    xi, yi = int(round(x)), int(round(y))
    y0, y1 = max(0, yi - radius), min(gray.shape[0], yi + radius + 1)
    x0, x1 = max(0, xi - radius), min(gray.shape[1], xi + radius + 1)
    patch = gray[y0:y1, x0:x1].astype(np.float32)
    if patch.size < 25:
        return 0.0
    median = float(np.median(patch))
    mad = float(np.median(np.abs(patch - median)))
    sigma = max(1.0, 1.4826 * mad)
    return round(max(0.0, (float(np.max(patch)) - median) / sigma), 3)


def project_targets(
    image_path: Path,
    wcs_path: Path,
    captured_at: str,
    min_snr: float,
    edge_margin: float,
) -> tuple[list[dict[str, Any]], int, int]:
    with Image.open(image_path) as image:
        width, height = image.size
        gray = np.asarray(image.convert("L"), dtype=np.uint8)
    wcs = WCS(str(wcs_path), naxis=2)
    margin_x, margin_y = width * edge_margin, height * edge_margin
    projected: list[dict[str, Any]] = []
    for target in target_coordinates(captured_at):
        if target["ra"] == "" or target["dec"] == "":
            x = y = float("nan")
            inside = False
            snr = 0.0
        else:
            try:
                x, y = wcs.all_world2pix(
                    [[target["ra"], target["dec"]]], 0, quiet=True
                )[0]
            except Exception:
                # A sky point far outside a SIP image can fail inverse
                # projection; for coverage purposes it is outside the frame.
                x = y = float("nan")
            inside = bool(
                np.isfinite(x)
                and np.isfinite(y)
                and margin_x <= x < width - margin_x
                and margin_y <= y < height - margin_y
            )
            snr = point_source_snr(gray, float(x), float(y), bool(target["cluster"])) if inside else 0.0
        verified = bool(inside and snr >= min_snr)
        projected.append(
            {
                **target,
                "pixel_x": round(float(x), 3) if np.isfinite(x) else "",
                "pixel_y": round(float(y), 3) if np.isfinite(y) else "",
                "inside_fov": inside,
                "point_source_snr": snr,
                "auto_verified": verified,
            }
        )
    return projected, width, height


def write_yolo(path: Path, projected: list[dict[str, Any]], width: int, height: int) -> int:
    lines: list[str] = []
    for target in projected:
        if not target["auto_verified"]:
            continue
        x = min(1.0, max(0.0, float(target["pixel_x"]) / width))
        y = min(1.0, max(0.0, float(target["pixel_y"]) / height))
        lines.append(
            f'{target["class_id"]} {x:.8f} {y:.8f} '
            f'{target["box_w"]:.8f} {target["box_h"]:.8f}'
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def draw_overlay(
    image_path: Path,
    output_path: Path,
    projected: list[dict[str, Any]],
    review_status: str,
) -> None:
    # Keep the encoded pixel grid unchanged: the WCS solution refers to this
    # exact grid. Applying EXIF orientation here would move the overlay while
    # leaving the projected coordinates unchanged.
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    line_width = max(2, min(image.size) // 500)
    draw.rectangle((0, 0, image.width, max(32, image.height // 24)), fill=(0, 0, 0))
    draw.text((8, 8), review_status, fill="#ffffff", font=font)
    for target in projected:
        if not target["inside_fov"]:
            continue
        x, y = float(target["pixel_x"]), float(target["pixel_y"])
        bw, bh = target["box_w"] * image.width, target["box_h"] * image.height
        color = "#22c55e" if target["auto_verified"] else "#ef4444"
        draw.rectangle(
            (x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2),
            outline=color,
            width=line_width,
        )
        draw.text(
            (x + 5, y + 5),
            f'{target["class_name"]} snr={target["point_source_snr"]:.1f}',
            fill=color,
            font=font,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, quality=92)


def make_contact_sheet(
    rows: list[dict[str, Any]], output_path: Path, columns: int
) -> None:
    available = [row for row in rows if Path(str(row.get("overlay_path", ""))).is_file()]
    if not available:
        return
    tile_width, tile_height, caption_height = 360, 260, 54
    sheet_rows = (len(available) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile_width, sheet_rows * (tile_height + caption_height)), "#111827")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, row in enumerate(available):
        with Image.open(row["overlay_path"]) as source:
            thumb = ImageOps.contain(source.convert("RGB"), (tile_width, tile_height))
        x0 = (index % columns) * tile_width
        y0 = (index // columns) * (tile_height + caption_height)
        x = x0 + (tile_width - thumb.width) // 2
        y = y0 + (tile_height - thumb.height) // 2
        sheet.paste(thumb, (x, y))
        caption = (
            f'{row["item_id"][:34]}\n'
            f'{row["review_status"]} | objects={row["auto_verified_objects"]}'
        )
        draw.multiline_text((x0 + 6, y0 + tile_height + 5), caption, fill="white", font=font, spacing=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=90)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    plate_results = args.plate_results.resolve()
    classification_path = args.classification.resolve()
    output = args.output_dir.resolve()
    if not plate_results.is_file():
        raise FileNotFoundError(f"36번 결과가 없습니다: {plate_results}")
    if not classification_path.is_file():
        raise FileNotFoundError(f"35번 분류 결과가 없습니다: {classification_path}")

    classifications = {row.get("filename", ""): row for row in read_csv(classification_path)}
    solved = [
        row
        for row in read_csv(plate_results)
        if row.get("status") in SUCCESS_STATUSES
        and Path(row.get("wcs_path", "")).is_file()
        and Path(row.get("source_path", "")).is_file()
    ]
    if not solved:
        raise RuntimeError("사용 가능한 TargetedWeb WCS 성공 사진이 없습니다.")

    review_path = output / "label_review.csv"
    previous_reviews = (
        {row.get("item_id", ""): row for row in read_csv(review_path)}
        if review_path.is_file()
        else {}
    )
    manifest_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()

    for index, plate in enumerate(solved, 1):
        item_id = plate["item_id"]
        metadata = classifications.get(plate.get("filename", ""), {})
        previous = previous_reviews.get(item_id, {})
        image_path = Path(plate["source_path"])
        wcs_path = Path(plate["wcs_path"])
        label_path = output / "labels" / f"{item_id}.txt"
        overlay_path = output / "overlays" / f"{item_id}_wcs_yolo.jpg"
        try:
            projected, width, height = project_targets(
                image_path,
                wcs_path,
                metadata.get("captured_at", ""),
                args.min_snr,
                args.edge_margin,
            )
            inside = [target for target in projected if target["inside_fov"]]
            verified = [target for target in projected if target["auto_verified"]]
            if verified:
                review_status = "positive_candidate"
            elif not inside:
                review_status = "verified_negative_candidate"
            else:
                review_status = "uncertain_target_inside_no_signal"
            if args.force or not label_path.is_file():
                write_yolo(label_path, projected, width, height)
            if args.force or not overlay_path.is_file():
                draw_overlay(image_path, overlay_path, projected, review_status)
            counts[review_status] += 1
            for target in verified:
                class_counts[target["class_name"]] += 1
            for target in projected:
                object_rows.append(
                    {
                        "item_id": item_id,
                        "filename": plate.get("filename", ""),
                        "query_group": plate.get("query_group", ""),
                        "class_id": target["class_id"],
                        "class_name": target["class_name"],
                        "ra": target["ra"],
                        "dec": target["dec"],
                        "coordinate_source": target["coordinate_source"],
                        "pixel_x": target["pixel_x"],
                        "pixel_y": target["pixel_y"],
                        "inside_fov": target["inside_fov"],
                        "point_source_snr": target["point_source_snr"],
                        "auto_verified": target["auto_verified"],
                    }
                )
            manifest_rows.append(
                {
                    "item_id": item_id,
                    "provider": plate.get("provider", ""),
                    "provider_id": plate.get("provider_id", ""),
                    "query_group": plate.get("query_group", ""),
                    "filename": plate.get("filename", ""),
                    "title": metadata.get("title", ""),
                    "creator": metadata.get("creator", ""),
                    "license": metadata.get("license", ""),
                    "license_url": metadata.get("license_url", ""),
                    "source_page_url": metadata.get("source_page_url", ""),
                    "camera_kind": plate.get("camera_kind", ""),
                    "captured_at": metadata.get("captured_at", ""),
                    "image_path": str(image_path),
                    "wcs_path": str(wcs_path),
                    "label_path": str(label_path),
                    "overlay_path": str(overlay_path),
                    "image_width": width,
                    "image_height": height,
                    "targets_inside_count": len(inside),
                    "targets_inside": ";".join(target["class_name"] for target in inside),
                    "auto_verified_objects": len(verified),
                    "auto_verified_classes": ";".join(target["class_name"] for target in verified),
                    "verified_negative_candidate": not inside,
                    "review_status": review_status,
                    "review_decision": previous.get("review_decision", ""),
                    "review_notes": previous.get("review_notes", ""),
                    "processing_status": "success",
                    "processing_error": "",
                }
            )
        except Exception as error:
            counts["projection_failed"] += 1
            manifest_rows.append(
                {
                    "item_id": item_id,
                    "provider": plate.get("provider", ""),
                    "provider_id": plate.get("provider_id", ""),
                    "query_group": plate.get("query_group", ""),
                    "filename": plate.get("filename", ""),
                    "title": metadata.get("title", ""),
                    "creator": metadata.get("creator", ""),
                    "license": metadata.get("license", ""),
                    "license_url": metadata.get("license_url", ""),
                    "source_page_url": metadata.get("source_page_url", ""),
                    "camera_kind": plate.get("camera_kind", ""),
                    "captured_at": metadata.get("captured_at", ""),
                    "image_path": str(image_path),
                    "wcs_path": str(wcs_path),
                    "label_path": "",
                    "overlay_path": "",
                    "image_width": "",
                    "image_height": "",
                    "targets_inside_count": 0,
                    "targets_inside": "",
                    "auto_verified_objects": 0,
                    "auto_verified_classes": "",
                    "verified_negative_candidate": False,
                    "review_status": "projection_failed",
                    "review_decision": previous.get("review_decision", ""),
                    "review_notes": previous.get("review_notes", ""),
                    "processing_status": "failed",
                    "processing_error": f"{type(error).__name__}: {error}",
                }
            )
        print(f"[{index:03d}/{len(solved):03d}] {item_id}: {manifest_rows[-1]['review_status']}")

    output.mkdir(parents=True, exist_ok=True)
    manifest_fields = list(manifest_rows[0].keys())
    object_fields = list(object_rows[0].keys()) if object_rows else [
        "item_id", "filename", "query_group", "class_id", "class_name", "ra", "dec",
        "coordinate_source", "pixel_x", "pixel_y", "inside_fov", "point_source_snr",
        "auto_verified",
    ]
    write_csv(output / "manifest.csv", manifest_rows, manifest_fields)
    write_csv(output / "projected_objects.csv", object_rows, object_fields)
    write_csv(
        review_path,
        manifest_rows,
        [
            "item_id", "filename", "query_group", "title", "review_status",
            "auto_verified_classes", "overlay_path", "review_decision", "review_notes",
        ],
    )
    accepted = [row for row in manifest_rows if row.get("review_decision") == "accept"]
    write_csv(output / "accepted_manifest.csv", accepted, manifest_fields)
    (output / "classes.txt").write_text("\n".join(CLASS_NAMES) + "\n", encoding="utf-8")

    for status in (
        "positive_candidate",
        "verified_negative_candidate",
        "uncertain_target_inside_no_signal",
    ):
        make_contact_sheet(
            [row for row in manifest_rows if row.get("review_status") == status],
            output / "contact_sheets" / f"{status}.jpg",
            args.contact_sheet_columns,
        )
    make_contact_sheet(
        [row for row in manifest_rows if row.get("processing_status") == "success"],
        output / "contact_sheets" / "all_candidates.jpg",
        args.contact_sheet_columns,
    )

    summary = {
        "status": "completed",
        "plate_solved_images": len(solved),
        "projection_success_images": sum(row["processing_status"] == "success" for row in manifest_rows),
        "projection_failed_images": sum(row["processing_status"] == "failed" for row in manifest_rows),
        "candidate_counts": dict(sorted(counts.items())),
        "auto_verified_class_counts": {name: class_counts[name] for name in CLASS_NAMES},
        "review_accepted": sum(row.get("review_decision") == "accept" for row in manifest_rows),
        "review_rejected": sum(row.get("review_decision") == "reject" for row in manifest_rows),
        "review_pending": sum(
            row.get("processing_status") == "success" and not row.get("review_decision")
            for row in manifest_rows
        ),
        "min_snr": args.min_snr,
        "edge_margin": args.edge_margin,
        "jupiter_policy": "Auto-labelled only when a parseable capture timestamp is available.",
        "training_warning": "All labels and empty backgrounds are candidates until stage-38 manual review.",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "manifest": str(output / "manifest.csv"),
            "projected_objects": str(output / "projected_objects.csv"),
            "label_review": str(review_path),
            "labels": str(output / "labels"),
            "overlays": str(output / "overlays"),
            "contact_sheets": str(output / "contact_sheets"),
        },
    }
    write_json(output / "summary.json", summary)
    print("TargetedWeb WCS/YOLO 라벨 후보 생성 완료")
    print(f"WCS 입력: {len(solved)}장")
    print(f"투영 성공: {summary['projection_success_images']}장")
    print(f"양성 후보: {counts['positive_candidate']}장")
    print(f"음성 후보: {counts['verified_negative_candidate']}장")
    print(f"불확실 후보: {counts['uncertain_target_inside_no_signal']}장")
    print(f"review: {review_path}")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
