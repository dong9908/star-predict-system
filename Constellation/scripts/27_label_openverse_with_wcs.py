"""Plate-solve reviewed Openverse night-sky images and create YOLO label candidates.

Only successfully solved images can become positives or verified backgrounds.
Fixed celestial coordinates are projected through WCS and checked for a local
point-source signal. Jupiter is deliberately not auto-labelled because its
position is time-dependent and most Openverse files have no trustworthy capture
time. Generated labels remain review candidates until their overlays are checked.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from astropy.wcs import WCS
from PIL import Image, ImageDraw, ImageFont

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION = PROJECT_ROOT / "data" / "results" / "openverse_classification" / "classification.csv"
WCS_ROOT = PROJECT_ROOT / "data" / "wcs" / "openverse"
OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "openverse_wcs_labels"
PLATE_SOLVER = PROJECT_ROOT / "scripts" / "07_plate_solving.py"
VALID_LABELS = {"valid_smartphone_night_sky", "valid_night_sky_device_unknown"}
CLASS_NAMES = [
    "Pleiades", "Jupiter", "Betelgeuse", "Aldebaran",
    "Zeta Tauri", "Elnath", "Hassaleh", "Bellatrix",
]

# ICRS/J2000 positions in degrees. Pleiades uses the cluster centre; the others
# are named stars. Jupiter is omitted because a static coordinate is invalid.
TARGETS = [
    {"class_id": 0, "name": "Pleiades", "ra": 56.75, "dec": 24.1167, "box_w": 0.035, "box_h": 0.035, "cluster": True},
    {"class_id": 2, "name": "Betelgeuse", "ra": 88.79294, "dec": 7.40706, "box_w": 0.020, "box_h": 0.015},
    {"class_id": 3, "name": "Aldebaran", "ra": 68.98016, "dec": 16.50930, "box_w": 0.020, "box_h": 0.015},
    {"class_id": 4, "name": "Zeta Tauri", "ra": 84.41119, "dec": 21.14255, "box_w": 0.020, "box_h": 0.015},
    {"class_id": 5, "name": "Elnath", "ra": 81.57297, "dec": 28.60745, "box_w": 0.020, "box_h": 0.015},
    {"class_id": 6, "name": "Hassaleh", "ra": 74.24842, "dec": 33.16610, "box_w": 0.020, "box_h": 0.015},
    {"class_id": 7, "name": "Bellatrix", "ra": 81.28276, "dec": 6.34970, "box_w": 0.020, "box_h": 0.015},
]

TARGET_TERMS = {
    "orion", "taurus", "pleiades", "aldebaran", "betelgeuse", "bellatrix",
    "auriga", "elnath", "alnath", "hassaleh", "zeta tauri", "jupiter",
    "gemini", "winter constellation", "zodiacal light",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classification", type=Path, default=CLASSIFICATION)
    parser.add_argument("--wcs-dir", type=Path, default=WCS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--solve", action="store_true", help="Run the WSL local solver for missing WCS files")
    parser.add_argument("--all-valid", action="store_true", help="Try every reviewed night-sky image, not only target-priority titles")
    parser.add_argument("--max-images", type=int)
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--force-solve", action="store_true")
    parser.add_argument("--min-snr", type=float, default=3.5)
    return parser.parse_args()


def normalized(text: str) -> str:
    return " ".join(str(text or "").lower().replace("_", " ").split())


def hint_for(title: str) -> tuple[float, float, float] | None:
    text = normalized(title)
    if any(term in text for term in {"orion", "taurus", "pleiades", "aldebaran", "betelgeuse", "bellatrix", "auriga", "gemini", "winter constellation", "zodiacal"}):
        return 78.0, 17.0, 55.0
    if any(term in text for term in {"perseus", "cassiopeia", "andromeda", "camelopardalis"}):
        return 25.0, 52.0, 60.0
    if "big dipper" in text:
        return 180.0, 58.0, 55.0
    return None


def plate_paths(wcs_root: Path, item_id: str) -> tuple[Path, Path]:
    folder = wcs_root / item_id
    return folder / f"{item_id}.wcs", folder / f"{item_id}_plate_solve.json"


def run_solver(row: dict[str, str], wcs_root: Path, timeout: int, force: bool) -> tuple[str, str]:
    image = Path(row["source_path"])
    item_id = row["item_id"]
    wcs_path, report_path = plate_paths(wcs_root, item_id)
    if wcs_path.is_file() and not force:
        return "cached", ""
    command = [
        sys.executable, str(PLATE_SOLVER), str(image),
        "--backend", "local", "--no-nova-fallback",
        "--output-dir", str(wcs_root), "--timeout-seconds", str(timeout),
        "--downsample", "2", "--scale-units", "degwidth",
        "--scale-lower", "10", "--scale-upper", "120",
    ]
    hint = hint_for(row.get("title", ""))
    if hint:
        command.extend(["--center-ra", str(hint[0]), "--center-dec", str(hint[1]), "--radius", str(hint[2])])
    if force:
        command.append("--force")
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    if wcs_path.is_file():
        return "success", ""
    error = completed.stderr.strip() or completed.stdout.strip()
    if report_path.is_file():
        try:
            error = json.loads(report_path.read_text(encoding="utf-8")).get("error", error)
        except Exception:
            pass
    return "failed", error[-500:]


def point_source_snr(gray: np.ndarray, x: float, y: float, radius: int) -> float:
    xi, yi = int(round(x)), int(round(y))
    y0, y1 = max(0, yi - radius), min(gray.shape[0], yi + radius + 1)
    x0, x1 = max(0, xi - radius), min(gray.shape[1], xi + radius + 1)
    patch = gray[y0:y1, x0:x1].astype(np.float32)
    if patch.size < 25:
        return 0.0
    median = float(np.median(patch))
    mad = float(np.median(np.abs(patch - median)))
    sigma = max(1.0, 1.4826 * mad)
    return max(0.0, (float(np.max(patch)) - median) / sigma)


def project_targets(wcs_path: Path, image_path: Path, min_snr: float) -> tuple[list[dict[str, Any]], int, int]:
    with Image.open(image_path) as image:
        width, height = image.size
        gray = np.asarray(image.convert("L"), dtype=np.uint8)
    wcs = WCS(str(wcs_path), naxis=2)
    results: list[dict[str, Any]] = []
    for target in TARGETS:
        x, y = wcs.all_world2pix([[target["ra"], target["dec"]]], 0)[0]
        inside = bool(np.isfinite(x) and np.isfinite(y) and 0 <= x < width and 0 <= y < height)
        radius = max(5, int(round(min(width, height) * (0.018 if target.get("cluster") else 0.008))))
        snr = point_source_snr(gray, float(x), float(y), radius) if inside else 0.0
        verified = inside and snr >= min_snr
        results.append({**target, "x": float(x), "y": float(y), "inside_fov": inside, "snr": round(snr, 3), "verified": verified})
    return results, width, height


def write_yolo(path: Path, projected: list[dict[str, Any]], width: int, height: int) -> int:
    lines = []
    for target in projected:
        if not target["verified"]:
            continue
        x = min(1.0, max(0.0, target["x"] / width))
        y = min(1.0, max(0.0, target["y"] / height))
        lines.append(f'{target["class_id"]} {x:.8f} {y:.8f} {target["box_w"]:.8f} {target["box_h"]:.8f}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def draw_overlay(image_path: Path, output: Path, projected: list[dict[str, Any]]) -> None:
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for target in projected:
        if not target["inside_fov"]:
            continue
        x, y = target["x"], target["y"]
        bw = target["box_w"] * image.width
        bh = target["box_h"] * image.height
        color = "#22c55e" if target["verified"] else "#ef4444"
        draw.rectangle((x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2), outline=color, width=max(2, image.width // 600))
        draw.text((x + 4, y + 4), f'{target["name"]} snr={target["snr"]:.1f}', fill=color, font=font)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=90)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    classification = args.classification.resolve()
    wcs_root = args.wcs_dir.resolve()
    output_root = args.output_dir.resolve()
    review_csv = output_root / "label_review.csv"
    existing_reviews = {
        row.get("item_id", ""): row for row in read_csv(review_csv)
    } if review_csv.is_file() else {}
    rows = [row for row in read_csv(classification) if row.get("final_label") in VALID_LABELS]
    if not args.all_valid:
        rows = [row for row in rows if any(term in normalized(row.get("title", "")) for term in TARGET_TERMS)]
    if args.max_images is not None:
        rows = rows[: max(0, args.max_images)]
    output_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for index, row in enumerate(rows, 1):
        item_id = row["item_id"]
        previous_review = existing_reviews.get(item_id, {})
        review_decision = previous_review.get("review_decision", "").strip()
        review_notes = previous_review.get("review_notes", "")
        wcs_path, _ = plate_paths(wcs_root, item_id)
        solve_status, solve_error = ("not_requested", "")
        if args.solve:
            print(f"[{index:03d}/{len(rows):03d}] Plate Solving: {row.get('title') or item_id}")
            solve_status, solve_error = run_solver(row, wcs_root, args.timeout_seconds, args.force_solve)
        elif wcs_path.is_file():
            solve_status = "cached"
        if not wcs_path.is_file():
            counts["plate_solve_failed_or_missing"] += 1
            output_rows.append({
                "item_id": item_id, "filename": row["filename"], "title": row.get("title", ""),
                "image_path": row["source_path"], "classification": row["final_label"],
                "solve_status": solve_status, "solve_error": solve_error,
                "wcs_path": "", "label_path": "", "overlay_path": "",
                "verified_objects": 0, "inside_fov_objects": 0,
                "background_verified": False, "jupiter_auto_labelled": False,
                "review_status": "plate_solve_required", "review_decision": review_decision,
                "review_notes": review_notes,
            })
            continue
        try:
            projected, width, height = project_targets(wcs_path, Path(row["source_path"]), args.min_snr)
            label_path = output_root / "labels" / f"{item_id}.txt"
            overlay_path = output_root / "overlays" / f"{item_id}_wcs_yolo.jpg"
            verified_count = write_yolo(label_path, projected, width, height)
            draw_overlay(Path(row["source_path"]), overlay_path, projected)
            inside_count = sum(bool(target["inside_fov"]) for target in projected)
            background = inside_count == 0
            review_status = "review_label_overlay" if verified_count else ("verified_background_candidate" if background else "targets_inside_but_not_visually_verified")
            counts[review_status] += 1
            for target in projected:
                object_rows.append({
                    "item_id": item_id, "filename": row["filename"], "class_id": target["class_id"],
                    "class_name": target["name"], "ra": target["ra"], "dec": target["dec"],
                    "pixel_x": round(target["x"], 3), "pixel_y": round(target["y"], 3),
                    "inside_fov": target["inside_fov"], "point_source_snr": target["snr"],
                    "verified": target["verified"],
                })
            output_rows.append({
                "item_id": item_id, "filename": row["filename"], "title": row.get("title", ""),
                "image_path": row["source_path"], "classification": row["final_label"],
                "solve_status": solve_status, "solve_error": "", "wcs_path": str(wcs_path),
                "label_path": str(label_path), "overlay_path": str(overlay_path),
                "verified_objects": verified_count, "inside_fov_objects": inside_count,
                "background_verified": background, "jupiter_auto_labelled": False,
                "review_status": review_status, "review_decision": review_decision,
                "review_notes": review_notes,
            })
        except Exception as exc:
            counts["wcs_projection_failed"] += 1
            output_rows.append({
                "item_id": item_id, "filename": row["filename"], "title": row.get("title", ""),
                "image_path": row["source_path"], "classification": row["final_label"],
                "solve_status": solve_status, "solve_error": f"{type(exc).__name__}: {exc}",
                "wcs_path": str(wcs_path), "label_path": "", "overlay_path": "",
                "verified_objects": 0, "inside_fov_objects": 0,
                "background_verified": False, "jupiter_auto_labelled": False,
                "review_status": "wcs_projection_failed", "review_decision": review_decision,
                "review_notes": review_notes,
            })

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_fields = list(output_rows[0].keys()) if output_rows else []
    object_fields = list(object_rows[0].keys()) if object_rows else [
        "item_id", "filename", "class_id", "class_name", "ra", "dec", "pixel_x", "pixel_y",
        "inside_fov", "point_source_snr", "verified",
    ]
    write_csv(output_root / "manifest.csv", output_rows, manifest_fields)
    accepted_rows = [
        row for row in output_rows
        if row.get("review_decision") == "accept" and row.get("wcs_path")
    ]
    write_csv(output_root / "accepted_manifest.csv", accepted_rows, manifest_fields)
    write_csv(
        review_csv,
        output_rows,
        ["item_id", "filename", "title", "review_status", "review_decision", "review_notes"],
    )
    write_csv(output_root / "projected_objects.csv", object_rows, object_fields)
    (output_root / "classes.txt").write_text("\n".join(CLASS_NAMES) + "\n", encoding="utf-8")
    summary = {
        "selected_images": len(rows), "counts": dict(sorted(counts.items())),
        "wcs_solved": sum(bool(row.get("wcs_path")) for row in output_rows),
        "yolo_labels_with_objects": sum(int(row.get("verified_objects", 0)) > 0 for row in output_rows),
        "verified_background_candidates": sum(str(row.get("background_verified")).lower() == "true" or row.get("background_verified") is True for row in output_rows),
        "jupiter_auto_labelled": 0,
        "review_accepted": sum(row.get("review_decision") == "accept" for row in output_rows),
        "review_rejected": sum(row.get("review_decision") == "reject" for row in output_rows),
        "review_pending": sum(
            bool(row.get("wcs_path")) and not row.get("review_decision") for row in output_rows
        ),
        "accepted_yolo_positive_images": sum(
            row.get("review_decision") == "accept" and int(row.get("verified_objects", 0)) > 0
            for row in output_rows
        ),
        "accepted_yolo_background_images": sum(
            row.get("review_decision") == "accept" and bool(row.get("background_verified"))
            for row in output_rows
        ),
        "warning": "All generated YOLO labels are candidates until overlay review. Empty labels are valid only for successfully solved WCS footprints.",
    }
    write_json(output_root / "summary.json", summary)
    print("Openverse WCS/YOLO 후보 생성 완료")
    print(f"선택 사진: {len(rows):,}장")
    print(f"WCS 성공: {summary['wcs_solved']:,}장")
    print(f"객체 라벨 생성: {summary['yolo_labels_with_objects']:,}장")
    print(f"음성 후보: {summary['verified_background_candidates']:,}장")
    print(f"manifest: {output_root / 'manifest.csv'}")
    print(f"summary: {output_root / 'summary.json'}")
    print(f"review: {review_csv}")


if __name__ == "__main__":
    main()
