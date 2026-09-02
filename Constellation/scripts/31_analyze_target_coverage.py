"""Analyze eight-target coverage in successfully plate-solved smartphone images.

Stage 31 consumes the stage-29 inventory and stage-30 WCS results.  It does not
run plate solving.  Targets are projected into every solved photograph; seven
objects use fixed ICRS coordinates and Jupiter is calculated for the EXIF
capture time.  Output splits are assigned by observing session to prevent
near-duplicate frames from leaking between training and independent test data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from astropy.coordinates import get_body
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image

from lib.io_utils import configure_utf8_console, read_csv, write_csv, write_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = PROJECT_ROOT / "data" / "results" / "astro_smartphone_plate_solving" / "plate_solve_results.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "results" / "astro_smartphone_target_coverage"

TARGETS = [
    (0, "Pleiades", 56.75000, 24.11670, True),
    (1, "Jupiter", None, None, False),
    (2, "Betelgeuse", 88.79294, 7.40706, False),
    (3, "Aldebaran", 68.98016, 16.50930, False),
    (4, "Zeta Tauri", 84.41119, 21.14255, False),
    (5, "Elnath", 81.57297, 28.60745, False),
    (6, "Hassaleh", 74.24842, 33.16610, False),
    (7, "Bellatrix", 81.28276, 6.34970, False),
]
SUCCESS = {"success", "cached_success"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plate-results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--test-fraction", type=float, default=0.20)
    parser.add_argument("--edge-margin", type=float, default=0.01, help="Normalized image-edge exclusion")
    parser.add_argument("--min-snr", type=float, default=3.5)
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not 0 < args.test_fraction < 1:
        raise ValueError("--test-fraction은 0과 1 사이여야 합니다.")
    if not 0 <= args.edge_margin < 0.25:
        raise ValueError("--edge-margin은 0 이상 0.25 미만이어야 합니다.")
    if args.min_snr < 0:
        raise ValueError("--min-snr은 0 이상이어야 합니다.")


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
    targets: list[dict[str, Any]] = []
    for class_id, name, ra, dec, cluster in TARGETS:
        coordinate_source = "fixed_icrs_j2000"
        if name == "Jupiter":
            if capture_time is None:
                targets.append({"class_id": class_id, "class_name": name, "ra": "", "dec": "", "cluster": cluster, "coordinate_source": "capture_time_missing"})
                continue
            body = get_body("jupiter", capture_time).icrs
            ra, dec = float(body.ra.deg), float(body.dec.deg)
            coordinate_source = "astropy_builtin_ephemeris"
        targets.append({"class_id": class_id, "class_name": name, "ra": float(ra), "dec": float(dec), "cluster": cluster, "coordinate_source": coordinate_source})
    return targets


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


def session_score(session_id: str) -> float:
    digest = hashlib.sha256(session_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64)


def main() -> None:
    configure_utf8_console()
    args = parse_args()
    validate_args(args)
    results_path = args.plate_results.resolve()
    output = args.output_dir.resolve()
    if not results_path.is_file():
        raise FileNotFoundError(f"30번 결과가 없습니다: {results_path}")

    solved = [row for row in read_csv(results_path) if row.get("status") in SUCCESS and Path(row.get("wcs_path", "")).is_file()]
    if not solved:
        raise RuntimeError("사용 가능한 WCS 성공 사진이 없습니다.")
    solved_sessions = sorted({row.get("session_id", "") for row in solved if row.get("session_id")})
    test_sessions = {session for session in solved_sessions if session_score(session) < args.test_fraction}
    if not test_sessions and solved_sessions:
        test_sessions.add(solved_sessions[0])

    image_rows: list[dict[str, Any]] = []
    object_rows: list[dict[str, Any]] = []
    class_images: Counter[str] = Counter()
    class_sessions: dict[str, set[str]] = defaultdict(set)
    failed_projection = 0

    for index, row in enumerate(solved, 1):
        image_path = Path(row["source_path"])
        wcs_path = Path(row["wcs_path"])
        try:
            with Image.open(image_path) as image:
                width, height = image.size
                gray = np.asarray(image.convert("L"), dtype=np.uint8)
            wcs = WCS(str(wcs_path), naxis=2)
            projected = []
            for target in target_coordinates(row.get("captured_at", "")):
                ra, dec = target["ra"], target["dec"]
                if ra == "" or dec == "":
                    x = y = float("nan")
                    inside = False
                    snr = 0.0
                else:
                    try:
                        x, y = wcs.all_world2pix([[ra, dec]], 0, quiet=True)[0]
                    except Exception:
                        # SIP inverse projection commonly fails for sky points far
                        # outside a wide-field image.  That is an outside-FOV
                        # target, not a failure of the image's valid WCS.
                        x = y = float("nan")
                    margin_x, margin_y = width * args.edge_margin, height * args.edge_margin
                    inside = bool(np.isfinite(x) and np.isfinite(y) and margin_x <= x < width - margin_x and margin_y <= y < height - margin_y)
                    snr = point_source_snr(gray, float(x), float(y), bool(target["cluster"])) if inside else 0.0
                visually_verified = inside and snr >= args.min_snr
                projected.append({**target, "pixel_x": round(float(x), 3) if np.isfinite(x) else "", "pixel_y": round(float(y), 3) if np.isfinite(y) else "", "inside_fov": inside, "point_source_snr": snr, "visually_verified": visually_verified})

            inside_names = [target["class_name"] for target in projected if target["inside_fov"]]
            verified_names = [target["class_name"] for target in projected if target["visually_verified"]]
            split = "test_candidate" if row.get("session_id") in test_sessions else "train_candidate"
            for target in projected:
                if target["inside_fov"]:
                    class_images[target["class_name"]] += 1
                    class_sessions[target["class_name"]].add(row.get("session_id", ""))
                object_rows.append({
                    "capture_group_id": row.get("capture_group_id", ""), "session_id": row.get("session_id", ""),
                    "filename": row.get("filename", ""), "split_candidate": split,
                    **{key: target[key] for key in ("class_id", "class_name", "ra", "dec", "coordinate_source", "pixel_x", "pixel_y", "inside_fov", "point_source_snr", "visually_verified")},
                })
            image_rows.append({
                "capture_group_id": row.get("capture_group_id", ""), "session_id": row.get("session_id", ""),
                "device_folder": row.get("device_folder", ""), "filename": row.get("filename", ""),
                "source_path": str(image_path), "captured_at": row.get("captured_at", ""), "wcs_path": str(wcs_path),
                "split_candidate": split, "targets_inside_count": len(inside_names),
                "targets_inside": ";".join(inside_names), "targets_visually_verified_count": len(verified_names),
                "targets_visually_verified": ";".join(verified_names), "verified_negative_candidate": len(inside_names) == 0,
                "projection_status": "success", "projection_error": "",
            })
        except Exception as error:
            failed_projection += 1
            image_rows.append({
                "capture_group_id": row.get("capture_group_id", ""), "session_id": row.get("session_id", ""),
                "device_folder": row.get("device_folder", ""), "filename": row.get("filename", ""),
                "source_path": str(image_path), "captured_at": row.get("captured_at", ""), "wcs_path": str(wcs_path),
                "split_candidate": "excluded", "targets_inside_count": 0, "targets_inside": "",
                "targets_visually_verified_count": 0, "targets_visually_verified": "", "verified_negative_candidate": False,
                "projection_status": "failed", "projection_error": f"{type(error).__name__}: {error}",
            })
        if index % 50 == 0:
            print(f"분석: {index}/{len(solved)}")

    valid_images = [row for row in image_rows if row["projection_status"] == "success"]
    negatives = [row for row in valid_images if row["verified_negative_candidate"]]
    tests = [row for row in valid_images if row["split_candidate"] == "test_candidate"]
    class_rows = [{
        "class_id": class_id, "class_name": name, "images_inside_fov": class_images[name],
        "independent_sessions": len(class_sessions[name]),
        "target_images_minimum": 100 if name in {"Hassaleh", "Bellatrix"} else 50,
        "additional_images_needed": max(0, (100 if name in {"Hassaleh", "Bellatrix"} else 50) - class_images[name]),
    } for class_id, name, *_ in TARGETS]

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "image_target_coverage.csv", image_rows, list(image_rows[0].keys()))
    write_csv(output / "projected_targets.csv", object_rows, list(object_rows[0].keys()))
    write_csv(output / "class_coverage_summary.csv", class_rows, list(class_rows[0].keys()))
    write_csv(output / "negative_candidates.csv", negatives, list(image_rows[0].keys()))
    write_csv(output / "independent_test_candidates.csv", tests, list(image_rows[0].keys()))
    summary = {
        "plate_solved_images": len(solved), "plate_solved_sessions": len(solved_sessions),
        "projection_success_images": len(valid_images), "projection_failed_images": failed_projection,
        "positive_images_any_target": sum(int(row["targets_inside_count"]) > 0 for row in valid_images),
        "verified_negative_candidates": len(negatives), "test_candidate_images": len(tests),
        "test_candidate_sessions": len({row["session_id"] for row in tests}),
        "test_fraction_requested": args.test_fraction, "split_unit": "observing_session",
        "class_coverage": {row["class_name"]: {"images": row["images_inside_fov"], "sessions": row["independent_sessions"]} for row in class_rows},
        "jupiter_note": "Jupiter coordinates use Astropy's built-in ephemeris and EXIF capture time.",
        "label_warning": "inside_fov is geometric coverage. visually_verified is an automatic SNR candidate and still requires review before YOLO training.",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output / "summary.json", summary)
    print("AstroSmartphone 8개 천체 포함 여부 분석 완료")
    print(f"WCS 입력: {len(solved)}장 / 투영 성공: {len(valid_images)}장")
    print(f"목표 천체 포함 사진: {summary['positive_images_any_target']}장")
    print(f"음성 후보: {len(negatives)}장")
    print(f"독립 Test 후보: {len(tests)}장 / {summary['test_candidate_sessions']}세션")
    print(f"summary: {output / 'summary.json'}")


if __name__ == "__main__":
    main()
