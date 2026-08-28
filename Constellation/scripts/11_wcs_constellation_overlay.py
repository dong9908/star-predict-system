"""Project Stellarium constellations through WCS and recognize visible patterns."""

from __future__ import annotations

import argparse
import csv
import json
import math
import warnings
import sys
from colorsys import hsv_to_rgb
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WCS_ROOT = PROJECT_ROOT / "data" / "wcs"
DEFAULT_DETECTION_ROOT = PROJECT_ROOT / "data" / "results" / "star_detection"
DEFAULT_STELLARIUM = PROJECT_ROOT / "data" / "reference" / "stellarium" / "western" / "index.json"
DEFAULT_HYG = PROJECT_ROOT / "HYG-Database-main" / "hyg" / "CURRENT" / "hygdata_v41.csv"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "results" / "wcs_constellation_overlay"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="원본 밤하늘 사진")
    parser.add_argument("--wcs", type=Path, help="07단계 .new, .wcs 또는 FITS 파일")
    parser.add_argument("--star-detection", type=Path, help="03단계 *_stars.json")
    parser.add_argument("--wcs-root", type=Path, default=DEFAULT_WCS_ROOT)
    parser.add_argument("--detection-root", type=Path, default=DEFAULT_DETECTION_ROOT)
    parser.add_argument("--stellarium", type=Path, default=DEFAULT_STELLARIUM)
    parser.add_argument("--hyg", type=Path, default=DEFAULT_HYG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--match-radius-px", type=float, default=5.0)
    parser.add_argument("--minimum-matched-stars", type=int, default=3)
    parser.add_argument("--minimum-match-fraction", type=float, default=0.45)
    parser.add_argument("--max-constellations", type=int, default=12)
    parser.add_argument("--include-two-star", action="store_true")
    return parser.parse_args()


def read_image(path: Path) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"이미지를 찾을 수 없습니다: {path}")
    encoded = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"이미지를 읽을 수 없습니다: {path}")
    return image


def write_image(path: Path, image: np.ndarray) -> None:
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 94])
    if not success:
        raise RuntimeError(f"이미지 저장에 실패했습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(path)


def line_hips(line: list[Any]) -> list[int]:
    return [int(value) for value in line if isinstance(value, (int, float))]


def load_stellarium(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Stellarium 파일을 찾을 수 없습니다: {path}")
    entries = json.loads(path.read_text(encoding="utf-8")).get("constellations")
    if not isinstance(entries, list):
        raise ValueError("Stellarium index.json 형식이 아닙니다.")
    return entries


def load_hyg(path: Path, required: set[int]) -> dict[int, dict[str, float]]:
    if not path.is_file():
        raise FileNotFoundError(f"HYG 파일을 찾을 수 없습니다: {path}")
    result: dict[int, dict[str, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            raw = (row.get("hip") or "").strip()
            if not raw:
                continue
            hip = int(raw)
            if hip not in required:
                continue
            try:
                value = {
                    "ra_deg": float(row["ra"]) * 15.0,
                    "dec_deg": float(row["dec"]),
                    "mag": float(row["mag"]),
                }
            except (TypeError, ValueError):
                continue
            if hip not in result or value["mag"] < result[hip]["mag"]:
                result[hip] = value
    return result


def find_wcs(image: Path, explicit: Path | None, root: Path) -> Path:
    if explicit:
        path = explicit.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"WCS 파일을 찾을 수 없습니다: {path}")
        return path
    folder = root.resolve() / image.stem
    report = folder / f"{image.stem}_plate_solve.json"
    if report.is_file():
        payload = json.loads(report.read_text(encoding="utf-8"))
        if payload.get("status") == "failed":
            raise RuntimeError("최근 07단계 Plate Solving이 실패하여 남아 있는 WCS를 사용하지 않습니다.")
        report_image = payload.get("image")
        if report_image and Path(str(report_image)).resolve() != image.resolve():
            raise RuntimeError("WCS 보고서의 원본 이미지가 현재 입력 이미지와 다릅니다.")
    for path in (folder / f"{image.stem}.new", folder / f"{image.stem}.wcs"):
        if path.is_file():
            return path
    raise FileNotFoundError(f"07단계 WCS 파일이 없습니다: {folder}")


def load_detection(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"03단계 별 검출 JSON이 없습니다: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    points = np.asarray(
        [[float(item["x"]), float(item["y"])] for item in payload.get("stars", [])],
        dtype=float,
    ).reshape((-1, 2))
    return points, payload


def match_points(
    reference: dict[int, tuple[float, float]],
    detected: np.ndarray,
    radius: float,
) -> dict[int, dict[str, Any]]:
    candidates: list[tuple[float, int, int]] = []
    for hip, point in reference.items():
        distances = np.linalg.norm(detected - np.asarray(point), axis=1)
        for detected_index in np.where(distances <= radius)[0]:
            candidates.append((float(distances[detected_index]), hip, int(detected_index)))
    matches: dict[int, dict[str, Any]] = {}
    used_detected: set[int] = set()
    for distance, hip, detected_index in sorted(candidates):
        if hip in matches or detected_index in used_detected:
            continue
        used_detected.add(detected_index)
        matches[hip] = {
            "detected_star_id": detected_index + 1,
            "detected_x": round(float(detected[detected_index, 0]), 4),
            "detected_y": round(float(detected[detected_index, 1]), 4),
            "error_px": round(distance, 6),
        }
    return matches


def projected_coordinates(
    wcs: WCS,
    coordinates: dict[int, dict[str, float]],
    height: int,
    orientation: str,
) -> dict[int, tuple[float, float]]:
    hips = list(coordinates)
    ra = np.asarray([coordinates[hip]["ra_deg"] for hip in hips])
    dec = np.asarray([coordinates[hip]["dec_deg"] for hip in hips])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x_values, y_values = wcs.world_to_pixel_values(ra, dec)
    if orientation == "vertical_flip":
        y_values = height - 1 - y_values
    return {
        hip: (float(x), float(y))
        for hip, x, y in zip(hips, x_values, y_values)
        if math.isfinite(float(x)) and math.isfinite(float(y))
    }


def choose_orientation(
    wcs: WCS,
    coordinates: dict[int, dict[str, float]],
    detected: np.ndarray,
    width: int,
    height: int,
    radius: float,
) -> tuple[str, dict[str, tuple[int, float]]]:
    metrics: dict[str, tuple[int, float]] = {}
    for orientation in ("as_is", "vertical_flip"):
        projected = projected_coordinates(wcs, coordinates, height, orientation)
        visible = {
            hip: point
            for hip, point in projected.items()
            if 0 <= point[0] < width and 0 <= point[1] < height
        }
        matches = match_points(visible, detected, radius)
        median = float(np.median([item["error_px"] for item in matches.values()])) if matches else math.inf
        metrics[orientation] = (len(matches), median)
    orientation = min(metrics, key=lambda key: (-metrics[key][0], metrics[key][1]))
    return orientation, metrics


def constellation_metrics(
    entry: dict[str, Any],
    projected: dict[int, tuple[float, float]],
    detected: np.ndarray,
    width: int,
    height: int,
    radius: float,
) -> dict[str, Any] | None:
    lines = [line_hips(line) for line in entry.get("lines", [])]
    hips = sorted({hip for line in lines for hip in line if hip in projected})
    visible = {
        hip: projected[hip]
        for hip in hips
        if 0 <= projected[hip][0] < width and 0 <= projected[hip][1] < height
    }
    if len(visible) < 2:
        return None
    matches = match_points(visible, detected, radius)
    visible_edges: list[tuple[int, int]] = []
    for line in lines:
        for first, second in zip(line, line[1:]):
            if first in visible and second in visible:
                visible_edges.append((first, second))
    matched_edges = [(first, second) for first, second in visible_edges if first in matches and second in matches]
    errors = [item["error_px"] for item in matches.values()]
    fraction = len(matches) / len(visible)
    edge_fraction = len(matched_edges) / len(visible_edges) if visible_edges else 0.0
    median_error = float(np.median(errors)) if errors else math.inf
    score = (
        45 * fraction
        + 25 * edge_fraction
        + 20 * min(1.0, len(matches) / 5.0)
        + 10 * max(0.0, 1.0 - median_error / radius)
    )
    common_name = entry.get("common_name", {})
    return {
        "iau": entry.get("iau"),
        "english_name": common_name.get("english"),
        "native_name": common_name.get("native"),
        "visible_reference_stars": len(visible),
        "matched_stars": len(matches),
        "match_fraction": round(fraction, 6),
        "visible_edges": len(visible_edges),
        "matched_edges": len(matched_edges),
        "edge_fraction": round(edge_fraction, 6),
        "median_error_px": round(median_error, 6) if math.isfinite(median_error) else None,
        "score": round(score, 4),
        "visible_hips": list(visible),
        "matches": {str(hip): value for hip, value in matches.items()},
        "lines": lines,
    }


def confidence(result: dict[str, Any], args: argparse.Namespace) -> str | None:
    matched = result["matched_stars"]
    fraction = result["match_fraction"]
    median = result["median_error_px"]
    if result["matched_edges"] < 1 or median is None or median > args.match_radius_px * 0.8:
        return None
    if matched >= max(4, args.minimum_matched_stars) and fraction >= max(0.6, args.minimum_match_fraction):
        return "high"
    if matched >= args.minimum_matched_stars and fraction >= args.minimum_match_fraction:
        return "medium"
    if args.include_two_star and matched >= 2 and fraction >= 0.67:
        return "low"
    return None


def constellation_color(index: int, total: int) -> tuple[int, int, int]:
    red, green, blue = hsv_to_rgb(index / max(total, 1), 0.78, 1.0)
    return int(blue * 255), int(green * 255), int(red * 255)


def draw_overlay(
    image: np.ndarray,
    selected: list[dict[str, Any]],
    projected: dict[int, tuple[float, float]],
) -> np.ndarray:
    canvas = image.copy()
    panel_height = max(120, min(300, 55 + 34 * len(selected)))
    overlay = canvas.copy()
    cv2.rectangle(overlay, (0, 0), (canvas.shape[1], panel_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.82, canvas, 0.18, 0, canvas)
    title = "WCS constellations: " + (", ".join(item["iau"] for item in selected) if selected else "none")
    cv2.putText(canvas, title, (18, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    rectangle = (0, 0, canvas.shape[1], canvas.shape[0])
    for index, result in enumerate(selected):
        color = constellation_color(index, len(selected))
        visible_set = set(result["visible_hips"])
        matched_set = {int(hip) for hip in result["matches"]}
        for line in result["lines"]:
            for first, second in zip(line, line[1:]):
                if first not in projected or second not in projected:
                    continue
                point_a = tuple(round(value) for value in projected[first])
                point_b = tuple(round(value) for value in projected[second])
                clipped, clipped_a, clipped_b = cv2.clipLine(rectangle, point_a, point_b)
                if clipped:
                    cv2.line(canvas, clipped_a, clipped_b, color, 4, cv2.LINE_AA)
        label_points = []
        for hip in visible_set:
            x, y = projected[hip]
            label_points.append((x, y))
            matched = hip in matched_set
            cv2.circle(canvas, (round(x), round(y)), 8 if matched else 5, (40, 255, 40) if matched else color, 2, cv2.LINE_AA)
        if label_points:
            label_x = round(float(np.median([point[0] for point in label_points])))
            label_y = round(float(np.median([point[1] for point in label_points])))
            cv2.putText(canvas, result["iau"], (label_x + 8, label_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
        summary = (
            f"{result['iau']} {result['confidence']} | stars {result['matched_stars']}/"
            f"{result['visible_reference_stars']} | edges {result['matched_edges']}/"
            f"{result['visible_edges']} | err {result['median_error_px']:.2f}px"
        )
        cv2.putText(canvas, summary, (18, 68 + 32 * index), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 2, cv2.LINE_AA)
    return canvas


def main() -> None:
    args = parse_args()
    if args.match_radius_px <= 0 or args.minimum_matched_stars < 2:
        raise ValueError("매칭 반경과 최소 일치 별 개수를 확인해주세요.")
    if not 0 < args.minimum_match_fraction <= 1 or args.max_constellations < 1:
        raise ValueError("일치 비율 또는 최대 별자리 수를 확인해주세요.")
    image_path = args.image.resolve()
    image = read_image(image_path)
    height, width = image.shape[:2]
    wcs_path = find_wcs(image_path, args.wcs, args.wcs_root)
    detection_path = (
        args.star_detection.resolve()
        if args.star_detection
        else args.detection_root.resolve() / image_path.stem / f"{image_path.stem}_stars.json"
    )
    detected, detection_payload = load_detection(detection_path)
    entries = load_stellarium(args.stellarium.resolve())
    required = {
        hip
        for entry in entries
        for line in entry.get("lines", [])
        for hip in line_hips(line)
    }
    coordinates = load_hyg(args.hyg.resolve(), required)
    celestial = WCS(fits.getheader(wcs_path), naxis=2).celestial
    orientation, orientation_metrics = choose_orientation(
        celestial, coordinates, detected, width, height, args.match_radius_px
    )
    projected = projected_coordinates(celestial, coordinates, height, orientation)

    candidates = []
    for entry in entries:
        result = constellation_metrics(
            entry, projected, detected, width, height, args.match_radius_px
        )
        if result is None:
            continue
        result["confidence"] = confidence(result, args)
        candidates.append(result)
    candidates.sort(key=lambda item: item["score"], reverse=True)
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    selected = [item for item in candidates if item["confidence"]]
    selected.sort(key=lambda item: (confidence_order[item["confidence"]], -item["score"]))
    selected = selected[: args.max_constellations]
    output_folder = args.output_dir.resolve() / image_path.stem
    output_folder.mkdir(parents=True, exist_ok=True)
    json_path = output_folder / f"{image_path.stem}_wcs_constellations.json"
    csv_path = output_folder / f"{image_path.stem}_wcs_constellations.csv"
    image_output = output_folder / f"{image_path.stem}_wcs_overlay.jpg"
    payload = {
        "image": str(image_path),
        "wcs": str(wcs_path),
        "star_detection": str(detection_path),
        "references": {"stellarium": str(args.stellarium.resolve()), "hyg": str(args.hyg.resolve())},
        "orientation": orientation,
        "orientation_metrics": {
            key: {"matched_stars": value[0], "median_error_px": None if not math.isfinite(value[1]) else round(value[1], 6)}
            for key, value in orientation_metrics.items()
        },
        "parameters": {
            "match_radius_px": args.match_radius_px,
            "minimum_matched_stars": args.minimum_matched_stars,
            "minimum_match_fraction": args.minimum_match_fraction,
            "include_two_star": args.include_two_star,
        },
        "decision": {
            "status": "recognized" if selected else "no_constellation_confirmed",
            "constellations": [item["iau"] for item in selected],
            "count": len(selected),
            "reason": (
                "WCS 재투영 별과 실제 검출점이 일치하는 Western 별자리를 찾았습니다."
                if selected
                else "WCS 영역에 별자리 선은 있으나 실제 검출점 일치 기준을 통과하지 못했습니다."
            ),
        },
        "selected": selected,
        "candidates": candidates,
        "detected_stars": int(detection_payload.get("detected_stars", len(detected))),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = [
        "rank", "iau", "native_name", "confidence", "score", "matched_stars",
        "visible_reference_stars", "match_fraction", "matched_edges", "visible_edges",
        "edge_fraction", "median_error_px",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for rank, item in enumerate(candidates, start=1):
            writer.writerow({"rank": rank, **{key: item.get(key) for key in fields if key != "rank"}})
    write_image(image_output, draw_overlay(image, selected, projected))

    print(f"WCS 방향: {orientation}")
    print(f"인식된 별자리: {', '.join(item['iau'] + ' / ' + item['native_name'] for item in selected) if selected else '없음'}")
    for item in selected:
        print(
            f"  {item['iau']}: {item['confidence']}, 별 {item['matched_stars']}/"
            f"{item['visible_reference_stars']}, 선 {item['matched_edges']}/{item['visible_edges']}, "
            f"오차 {item['median_error_px']:.3f}px"
        )
    print(f"overlay_json: {json_path}")
    print(f"overlay_csv: {csv_path}")
    print(f"overlay_image: {image_output}")


if __name__ == "__main__":
    main()
