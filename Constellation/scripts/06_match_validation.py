"""Validate a constellation match with structure, observation metadata, and optional WCS."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.utils import iers
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
from PIL import ExifTags, Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "results" / "match_validation"
DEFAULT_HYG = PROJECT_ROOT / "HYG-Database-main" / "hyg" / "CURRENT" / "hygdata_v41.csv"
DEFAULT_GAIA = PROJECT_ROOT / "data" / "reference" / "gaia_dr3_g10.csv"
DEFAULT_DETECTION_ROOT = PROJECT_ROOT / "data" / "results" / "star_detection"
FILENAME_TIME = re.compile(r"PXL_(\d{8})_(\d{6})(\d{3})?")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matching", type=Path, help="05단계에서 생성한 *_matching.json")
    parser.add_argument("--wcs", type=Path, help="Astrometry.net의 .wcs, .fits 또는 .new 파일")
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument(
        "--captured-at",
        help="ISO 8601 촬영 시각. 예: 2026-08-25T22:30:00+09:00",
    )
    parser.add_argument(
        "--utc-offset-hours",
        type=float,
        help="EXIF/파일명의 시간대가 없을 때 적용할 UTC 시차. 한국은 9",
    )
    parser.add_argument("--hyg", type=Path)
    parser.add_argument("--gaia", type=Path, default=DEFAULT_GAIA)
    parser.add_argument("--star-detection", type=Path, help="03단계의 *_stars.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-altitude-deg", type=float, default=-5.0)
    parser.add_argument("--max-angular-error-arcsec", type=float, default=180.0)
    parser.add_argument("--gaia-max-magnitude", type=float, default=8.0)
    parser.add_argument("--global-match-radius-px", type=float, default=5.0)
    parser.add_argument("--minimum-global-matches", type=int, default=12)
    parser.add_argument("--max-candidate-reprojection-error-px", type=float, default=5.0)
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
    success, encoded = cv2.imencode(path.suffix or ".jpg", image)
    if not success:
        raise RuntimeError(f"이미지 인코딩에 실패했습니다: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded.tofile(path)


def output_stem(path: Path) -> str:
    stem = path.stem
    return stem[:-9] if stem.endswith("_matching") else stem


def load_matching(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"매칭 JSON을 찾을 수 없습니다: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "decision" not in payload or "results" not in payload or "image" not in payload:
        raise ValueError("05단계 매칭 JSON 형식이 아닙니다.")
    return payload


def rational_float(value: Any) -> float:
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return float(value.numerator / value.denominator)
    return float(value)


def dms_to_decimal(values: Any, reference: str) -> float:
    degrees, minutes, seconds = (rational_float(value) for value in values)
    result = degrees + minutes / 60.0 + seconds / 3600.0
    return -result if reference.upper() in {"S", "W"} else result


def extract_exif_metadata(image_path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "datetime_raw": None,
        "offset_raw": None,
        "latitude": None,
        "longitude": None,
        "datetime_source": None,
        "location_source": None,
    }
    with Image.open(image_path) as image:
        exif = image.getexif()
        metadata["datetime_raw"] = exif.get(36867) or exif.get(306)
        metadata["offset_raw"] = exif.get(36881) or exif.get(36880)
        if metadata["datetime_raw"]:
            metadata["datetime_source"] = "EXIF"
        try:
            gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        except (AttributeError, KeyError, TypeError):
            gps = {}
        if gps:
            try:
                latitude = dms_to_decimal(gps[2], str(gps[1]))
                longitude = dms_to_decimal(gps[4], str(gps[3]))
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    metadata["latitude"] = latitude
                    metadata["longitude"] = longitude
                    metadata["location_source"] = "EXIF GPS"
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                pass
    if not metadata["datetime_raw"]:
        match = FILENAME_TIME.search(image_path.name)
        if match:
            milliseconds = (match.group(3) or "000")[:3]
            metadata["datetime_raw"] = f"{match.group(1)}{match.group(2)}{milliseconds}"
            metadata["datetime_source"] = "filename"
    return metadata


def parse_utc_offset(value: str) -> timezone:
    normalized = value.strip()
    sign = -1 if normalized.startswith("-") else 1
    digits = normalized.lstrip("+-")
    if ":" in digits:
        hours_text, minutes_text = digits.split(":", 1)
        offset = timedelta(hours=int(hours_text), minutes=int(minutes_text))
    else:
        offset = timedelta(hours=float(digits))
    return timezone(sign * offset)


def parse_capture_time(
    raw: str | None,
    offset_raw: str | None,
    utc_offset_hours: float | None,
) -> tuple[datetime | None, str | None]:
    if not raw:
        return None, "촬영 시각이 없습니다."
    normalized = str(raw).strip().replace("Z", "+00:00")
    parsed: datetime | None = None
    formats = (
        "%Y:%m:%d %H:%M:%S",
        "%Y%m%d%H%M%S%f",
    )
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        for format_text in formats:
            try:
                parsed = datetime.strptime(normalized, format_text)
                break
            except ValueError:
                continue
    if parsed is None:
        return None, f"촬영 시각 형식을 해석할 수 없습니다: {raw}"
    if parsed.tzinfo is None:
        if offset_raw:
            parsed = parsed.replace(tzinfo=parse_utc_offset(str(offset_raw)))
        elif utc_offset_hours is not None:
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=utc_offset_hours)))
        else:
            return None, "촬영 시각에 시간대가 없습니다. --utc-offset-hours가 필요합니다."
    return parsed.astimezone(timezone.utc), None


def resolve_observation_metadata(
    image_path: Path,
    latitude_override: float | None,
    longitude_override: float | None,
    captured_at_override: str | None,
    utc_offset_hours: float | None,
) -> dict[str, Any]:
    if (latitude_override is None) != (longitude_override is None):
        raise ValueError("--latitude와 --longitude는 함께 지정해야 합니다.")
    exif = extract_exif_metadata(image_path)
    if latitude_override is not None:
        if not -90 <= latitude_override <= 90 or not -180 <= longitude_override <= 180:
            raise ValueError("위도 또는 경도 범위를 확인해주세요.")
        latitude = latitude_override
        longitude = longitude_override
        location_source = "command line"
    else:
        latitude = exif["latitude"]
        longitude = exif["longitude"]
        location_source = exif["location_source"]

    raw_time = captured_at_override or exif["datetime_raw"]
    time_source = "command line" if captured_at_override else exif["datetime_source"]
    captured_utc, time_error = parse_capture_time(
        raw_time,
        None if captured_at_override else exif["offset_raw"],
        utc_offset_hours,
    )
    return {
        "latitude": latitude,
        "longitude": longitude,
        "location_source": location_source,
        "captured_at_utc": captured_utc.isoformat() if captured_utc else None,
        "time_source": time_source,
        "time_error": time_error,
    }


def load_hyg_coordinates(path: Path, hips: set[int]) -> dict[int, dict[str, float]]:
    if not path.is_file():
        raise FileNotFoundError(f"HYG CSV를 찾을 수 없습니다: {path}")
    coordinates: dict[int, dict[str, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            raw_hip = row.get("hip", "").strip()
            if not raw_hip:
                continue
            hip = int(raw_hip)
            if hip not in hips:
                continue
            try:
                candidate = {
                    "ra_deg": float(row["ra"]) * 15.0,
                    "dec_deg": float(row["dec"]),
                    "mag": float(row["mag"]),
                }
            except (TypeError, ValueError):
                continue
            previous = coordinates.get(hip)
            if previous is None or candidate["mag"] < previous["mag"]:
                coordinates[hip] = candidate
    return coordinates


def structural_validation(matching: dict[str, Any]) -> dict[str, Any]:
    if not matching["results"]:
        return {
            "status": "fail",
            "summary": "5단계에서 별자리 후보를 찾지 못했습니다.",
            "details": {},
        }
    best = matching["results"][0]
    mappings = best.get("mappings", [])
    unique_hips = {int(item["hip"]) for item in mappings}
    unique_stars = {int(item["observed_star_id"]) for item in mappings}
    errors = [float(item["error_px"]) for item in mappings]
    consistent = (
        len(mappings) == int(best["matched_stars"])
        and len(unique_hips) == len(mappings)
        and len(unique_stars) == len(mappings)
        and all(error <= float(best["match_radius_px"]) + 1e-6 for error in errors)
    )
    confidence = matching["decision"].get("confidence", "low")
    if not consistent:
        status = "fail"
        summary = "매칭 수, 중복 대응 또는 허용 반경 일관성 검사에 실패했습니다."
    elif confidence == "high":
        status = "strong"
        summary = "그래프 내부 근거가 강하지만 독립적인 천구 좌표 검증은 아닙니다."
    elif confidence == "medium":
        status = "moderate"
        summary = "그래프 내부 근거가 보통이며 외부 검증이 필요합니다."
    else:
        status = "weak"
        summary = "그래프 내부 근거가 약해 후보로만 유지합니다."
    return {
        "status": status,
        "summary": summary,
        "independent_evidence": False,
        "details": {
            "candidate": best["iau"],
            "score": best["score"],
            "confidence": confidence,
            "matched_stars": best["matched_stars"],
            "visible_reference_stars": best["visible_reference_stars"],
            "verified_matches_beyond_seed": best["verified_matches_beyond_seed"],
            "matched_edges": best["matched_edges"],
            "visible_reference_edges": best["visible_reference_edges"],
            "rms_error_px": best["rms_error_px"],
            "match_radius_px": best["match_radius_px"],
            "mapping_consistent": consistent,
        },
    }


def visibility_validation(
    best: dict[str, Any] | None,
    coordinates: dict[int, dict[str, float]],
    observation: dict[str, Any],
    minimum_altitude_deg: float,
) -> dict[str, Any]:
    if best is None:
        return {"status": "not_available", "summary": "검증할 후보가 없습니다.", "stars": []}
    if observation["latitude"] is None or observation["longitude"] is None:
        return {"status": "not_available", "summary": "GPS 위치가 없습니다.", "stars": []}
    if observation["captured_at_utc"] is None:
        return {
            "status": "not_available",
            "summary": observation["time_error"] or "사용 가능한 촬영 시각이 없습니다.",
            "stars": [],
        }
    hips = [int(item["hip"]) for item in best.get("mappings", []) if int(item["hip"]) in coordinates]
    if len(hips) < 3:
        return {"status": "not_available", "summary": "HYG 좌표가 3개 미만입니다.", "stars": []}

    iers.conf.auto_download = False
    iers.conf.auto_max_age = None
    sky = SkyCoord(
        ra=[coordinates[hip]["ra_deg"] for hip in hips] * u.deg,
        dec=[coordinates[hip]["dec_deg"] for hip in hips] * u.deg,
        frame="icrs",
    )
    location = EarthLocation(
        lat=float(observation["latitude"]) * u.deg,
        lon=float(observation["longitude"]) * u.deg,
    )
    observation_datetime = datetime.fromisoformat(
        str(observation["captured_at_utc"]).replace("Z", "+00:00")
    )
    altaz = sky.transform_to(AltAz(obstime=Time(observation_datetime), location=location))
    altitudes = np.asarray(altaz.alt.deg, dtype=float)
    azimuths = np.asarray(altaz.az.deg, dtype=float)
    visible = altitudes >= minimum_altitude_deg
    visible_fraction = float(np.mean(visible))
    if visible_fraction >= 0.8:
        status = "pass"
        summary = "후보 별 대부분이 촬영 시각에 지평선 위에 있었습니다."
    elif visible_fraction < 0.5:
        status = "fail"
        summary = "후보 별 대부분이 촬영 시각에 지평선 아래여서 후보와 모순됩니다."
    else:
        status = "inconclusive"
        summary = "후보 별 일부만 지평선 위여서 가시성 검증이 불확실합니다."
    return {
        "status": status,
        "summary": summary,
        "minimum_altitude_deg": minimum_altitude_deg,
        "visible_fraction": round(visible_fraction, 6),
        "median_altitude_deg": round(float(np.median(altitudes)), 4),
        "stars": [
            {
                "hip": hip,
                "altitude_deg": round(float(altitude), 4),
                "azimuth_deg": round(float(azimuth), 4),
                "above_threshold": bool(is_visible),
            }
            for hip, altitude, azimuth, is_visible in zip(hips, altitudes, azimuths, visible)
        ],
    }


def load_detection_points(path: Path | None) -> tuple[np.ndarray, dict[str, Any] | None]:
    if path is None or not path.is_file():
        return np.empty((0, 2), dtype=float), None
    payload = json.loads(path.read_text(encoding="utf-8"))
    points = np.asarray(
        [[float(star["x"]), float(star["y"])] for star in payload.get("stars", [])],
        dtype=float,
    )
    return points.reshape((-1, 2)), payload


def load_bright_gaia(path: Path, maximum_magnitude: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not path.is_file():
        raise FileNotFoundError(f"Gaia CSV를 찾을 수 없습니다: {path}")
    chunks: list[np.ndarray] = []
    for frame in pd.read_csv(
        path,
        usecols=["ra", "dec", "phot_g_mean_mag"],
        chunksize=100_000,
    ):
        numeric = frame.apply(pd.to_numeric, errors="coerce").dropna()
        numeric = numeric[numeric["phot_g_mean_mag"] <= maximum_magnitude]
        if not numeric.empty:
            chunks.append(numeric[["ra", "dec", "phot_g_mean_mag"]].to_numpy(dtype=float))
    if not chunks:
        return np.array([]), np.array([]), np.array([])
    values = np.vstack(chunks)
    return values[:, 0], values[:, 1], values[:, 2]


def greedy_spatial_matches(
    projected: np.ndarray,
    magnitudes: np.ndarray,
    detected: np.ndarray,
    radius: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not len(projected) or not len(detected):
        empty = np.empty((0, 2), dtype=float)
        return np.array([], dtype=float), empty, empty
    cell_size = max(radius, 1.0)
    cells: dict[tuple[int, int], list[int]] = {}
    for index, point in enumerate(detected):
        key = (int(point[0] // cell_size), int(point[1] // cell_size))
        cells.setdefault(key, []).append(index)
    candidates: list[tuple[float, int, int]] = []
    for projected_index in np.argsort(magnitudes):
        point = projected[projected_index]
        cell_x, cell_y = int(point[0] // cell_size), int(point[1] // cell_size)
        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                for detected_index in cells.get((cell_x + offset_x, cell_y + offset_y), []):
                    distance = float(np.linalg.norm(point - detected[detected_index]))
                    if distance <= radius:
                        candidates.append((distance, int(projected_index), detected_index))
    used_projected: set[int] = set()
    used_detected: set[int] = set()
    selected: list[tuple[float, int, int]] = []
    for item in sorted(candidates):
        distance, projected_index, detected_index = item
        if projected_index in used_projected or detected_index in used_detected:
            continue
        used_projected.add(projected_index)
        used_detected.add(detected_index)
        selected.append(item)
    if not selected:
        empty = np.empty((0, 2), dtype=float)
        return np.array([], dtype=float), empty, empty
    return (
        np.asarray([item[0] for item in selected], dtype=float),
        np.asarray([projected[item[1]] for item in selected], dtype=float),
        np.asarray([detected[item[2]] for item in selected], dtype=float),
    )


def spatial_coverage(points: np.ndarray, width: int, height: int) -> dict[str, Any]:
    if not len(points):
        return {"occupied_3x3_cells": 0, "bounding_box_area_fraction": 0.0}
    cell_x = np.clip((points[:, 0] / max(width, 1) * 3).astype(int), 0, 2)
    cell_y = np.clip((points[:, 1] / max(height, 1) * 3).astype(int), 0, 2)
    occupied = len(set(zip(cell_x.tolist(), cell_y.tolist())))
    span_x = float(np.ptp(points[:, 0])) if len(points) > 1 else 0.0
    span_y = float(np.ptp(points[:, 1])) if len(points) > 1 else 0.0
    return {
        "occupied_3x3_cells": occupied,
        "bounding_box_area_fraction": round(span_x * span_y / max(width * height, 1), 6),
    }


def global_reprojection_validation(
    celestial: WCS,
    gaia_path: Path,
    detection_path: Path | None,
    image_width: int,
    image_height: int,
    maximum_magnitude: float,
    match_radius_px: float,
    minimum_matches: int,
) -> dict[str, Any]:
    detected, detection_payload = load_detection_points(detection_path)
    if detection_payload is None:
        return {
            "status": "not_available",
            "summary": "03단계 별 검출 JSON이 없어 사진 전체 재투영을 검사할 수 없습니다.",
        }
    if len(detected) < 3:
        return {
            "status": "fail",
            "summary": "사진 전체 재투영과 비교할 검출 별이 3개 미만입니다.",
            "detected_stars": len(detected),
        }
    try:
        ra, dec, magnitudes = load_bright_gaia(gaia_path, maximum_magnitude)
    except (FileNotFoundError, ValueError, KeyError) as error:
        return {"status": "not_available", "summary": str(error)}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        x_values, y_values = celestial.world_to_pixel_values(ra, dec)
    finite = np.isfinite(x_values) & np.isfinite(y_values)
    results: list[dict[str, Any]] = []
    for orientation, oriented_y in (
        ("as_is", y_values),
        ("vertical_flip", image_height - 1 - y_values),
    ):
        inside = (
            finite
            & (x_values >= 0)
            & (x_values < image_width)
            & (oriented_y >= 0)
            & (oriented_y < image_height)
        )
        projected = np.column_stack((x_values[inside], oriented_y[inside]))
        errors, matched_projected, _ = greedy_spatial_matches(
            projected,
            magnitudes[inside],
            detected,
            match_radius_px,
        )
        coverage = spatial_coverage(matched_projected, image_width, image_height)
        results.append(
            {
                "orientation": orientation,
                "catalog_stars_in_frame": int(len(projected)),
                "matched_stars": int(len(errors)),
                "median_error_px": float(np.median(errors)) if len(errors) else math.inf,
                "p90_error_px": float(np.percentile(errors, 90)) if len(errors) else math.inf,
                "rms_error_px": float(np.sqrt(np.mean(errors**2))) if len(errors) else math.inf,
                **coverage,
            }
        )
    best_result = min(
        results,
        key=lambda item: (-item["matched_stars"], item["median_error_px"]),
    )
    enough_matches = best_result["matched_stars"] >= minimum_matches
    accurate = (
        best_result["median_error_px"] <= match_radius_px * 0.6
        and best_result["p90_error_px"] <= match_radius_px
    )
    distributed = best_result["occupied_3x3_cells"] >= 3
    if enough_matches and accurate and distributed:
        status = "pass"
        summary = "Gaia 별이 사진 전역의 검출점과 작은 픽셀 오차로 일치합니다."
    elif (
        best_result["matched_stars"] < max(4, minimum_matches // 3)
        or best_result["median_error_px"] > match_radius_px * 0.85
    ):
        status = "fail"
        summary = "WCS로 재투영한 Gaia 별이 사진 전체 검출점과 일치하지 않습니다."
    else:
        status = "inconclusive"
        summary = "전역 재투영 근거의 수, 오차 또는 공간 분포가 충분하지 않습니다."
    return {
        "status": status,
        "summary": summary,
        "detection_file": str(detection_path),
        "gaia_file": str(gaia_path),
        "gaia_max_magnitude": maximum_magnitude,
        "match_radius_px": match_radius_px,
        "minimum_matches": minimum_matches,
        "detected_stars": int(len(detected)),
        **{
            key: round(value, 6) if isinstance(value, float) and math.isfinite(value) else value
            for key, value in best_result.items()
        },
    }


def wcs_validation(
    best: dict[str, Any] | None,
    coordinates: dict[int, dict[str, float]],
    wcs_path: Path | None,
    detection_path: Path | None,
    gaia_path: Path,
    image_width: int,
    image_height: int,
    max_angular_error_arcsec: float,
    maximum_gaia_magnitude: float,
    global_match_radius_px: float,
    minimum_global_matches: int,
    max_candidate_reprojection_error_px: float,
) -> dict[str, Any]:
    if wcs_path is None:
        return {"status": "not_available", "summary": "WCS Plate Solving 파일이 없습니다.", "stars": []}
    if best is None:
        return {"status": "not_available", "summary": "검증할 후보가 없습니다.", "stars": []}
    if not wcs_path.is_file():
        raise FileNotFoundError(f"WCS 파일을 찾을 수 없습니다: {wcs_path}")
    header = fits.getheader(wcs_path)
    # Nova .new files may store RGB as a third image axis. Select the two
    # celestial axes explicitly so SIP distortion remains valid in Astropy.
    celestial = WCS(header, naxis=2).celestial
    if not celestial.has_celestial:
        raise ValueError(f"천구 WCS 헤더가 아닙니다: {wcs_path}")

    mappings = [item for item in best.get("mappings", []) if int(item["hip"]) in coordinates]
    if len(mappings) < 3:
        return {"status": "not_available", "summary": "WCS와 비교할 HIP 별이 3개 미만입니다.", "stars": []}
    hips = [int(item["hip"]) for item in mappings]
    x_values = np.asarray([float(item["observed_x"]) for item in mappings])
    y_values = np.asarray([float(item["observed_y"]) for item in mappings])
    reference = SkyCoord(
        ra=[coordinates[hip]["ra_deg"] for hip in hips] * u.deg,
        dec=[coordinates[hip]["dec_deg"] for hip in hips] * u.deg,
        frame="icrs",
    )

    orientation_results = []
    for orientation, y_pixels in (
        ("as_is", y_values),
        ("vertical_flip", image_height - 1 - y_values),
    ):
        world = celestial.pixel_to_world(x_values, y_pixels)
        separations = np.asarray(world.separation(reference).arcsec, dtype=float)
        predicted_x, predicted_y = celestial.world_to_pixel(reference)
        if orientation == "vertical_flip":
            predicted_y = image_height - 1 - predicted_y
        pixel_errors = np.sqrt((predicted_x - x_values) ** 2 + (predicted_y - y_values) ** 2)
        orientation_results.append(
            (float(np.nanmedian(pixel_errors)), orientation, separations, pixel_errors)
        )
    _, orientation, separations, pixel_errors = min(orientation_results, key=lambda item: item[0])
    median_error = float(np.nanmedian(separations))

    try:
        pixel_scale_arcsec = float(np.median(proj_plane_pixel_scales(celestial)) * 3600.0)
    except Exception:
        pixel_scale_arcsec = math.nan
    allowed_error = max_angular_error_arcsec
    valid = np.isfinite(separations)
    passing = valid & (separations <= allowed_error)
    passing_fraction = float(np.mean(passing)) if len(passing) else 0.0
    pixel_valid = np.isfinite(pixel_errors)
    pixel_inliers = pixel_valid & (pixel_errors <= max_candidate_reprojection_error_px)
    pixel_inlier_fraction = float(np.mean(pixel_inliers)) if len(pixel_inliers) else 0.0
    pixel_median = float(np.nanmedian(pixel_errors))
    pixel_p90 = float(np.nanpercentile(pixel_errors, 90))
    if (
        len(mappings) >= 4
        and pixel_inlier_fraction >= 0.7
        and pixel_median <= max_candidate_reprojection_error_px
        and pixel_p90 <= max_candidate_reprojection_error_px * 2
    ):
        candidate_status = "pass"
        candidate_summary = "후보 HIP 별의 WCS 재투영 위치가 실제 검출점과 일치합니다."
    elif len(mappings) >= 4 and (
        pixel_inlier_fraction < 0.4
        or pixel_median > max_candidate_reprojection_error_px * 2
        or pixel_p90 > max_candidate_reprojection_error_px * 4
    ):
        candidate_status = "fail"
        candidate_summary = "후보 HIP 별의 재투영 위치가 실제 대응점과 크게 다릅니다."
    else:
        candidate_status = "inconclusive"
        candidate_summary = "후보 별 재투영 결과가 확정 또는 기각 기준에 충분하지 않습니다."
    global_check = global_reprojection_validation(
        celestial,
        gaia_path,
        detection_path,
        image_width,
        image_height,
        maximum_gaia_magnitude,
        global_match_radius_px,
        minimum_global_matches,
    )
    if candidate_status == "pass" and global_check["status"] == "pass":
        status = "pass"
        summary = "후보 HIP 대응과 사진 전체 Gaia 재투영이 모두 일치합니다."
    elif candidate_status == "fail" or global_check["status"] == "fail":
        status = "fail"
        summary = "후보 대응 또는 사진 전체 WCS 재투영 일관성에 실패했습니다."
    else:
        status = "inconclusive"
        summary = "후보 대응과 사진 전체 재투영을 모두 확정할 근거가 부족합니다."
    return {
        "status": status,
        "summary": summary,
        "wcs_file": str(wcs_path),
        "pixel_y_orientation": orientation,
        "pixel_scale_arcsec": round(pixel_scale_arcsec, 6) if math.isfinite(pixel_scale_arcsec) else None,
        "allowed_error_arcsec": round(allowed_error, 4),
        "median_error_arcsec": round(median_error, 4),
        "passing_fraction": round(passing_fraction, 6),
        "candidate_reprojection": {
            "status": candidate_status,
            "summary": candidate_summary,
            "maximum_error_px": max_candidate_reprojection_error_px,
            "median_error_px": round(pixel_median, 6),
            "p90_error_px": round(pixel_p90, 6),
            "inlier_fraction": round(pixel_inlier_fraction, 6),
        },
        "global_reprojection": global_check,
        "stars": [
            {
                "hip": hip,
                "angular_error_arcsec": round(float(error), 4),
                "reprojection_error_px": round(float(pixel_error), 6),
                "within_angular_limit": bool(is_passing),
                "within_reprojection_limit": bool(pixel_inlier),
            }
            for hip, error, pixel_error, is_passing, pixel_inlier in zip(
                hips, separations, pixel_errors, passing, pixel_inliers
            )
        ],
    }


def final_decision(
    structural: dict[str, Any],
    visibility: dict[str, Any],
    wcs_check: dict[str, Any],
) -> tuple[str, str]:
    if structural["status"] == "fail":
        return "rejected", "그래프 매칭 결과의 내부 일관성 검사에 실패했습니다."
    if visibility["status"] == "fail":
        return "rejected", "촬영 시각·위치의 지평선 가시성과 후보가 모순됩니다."
    if wcs_check["status"] == "fail":
        return "rejected", "Plate Solving 천구 좌표와 후보 HIP 좌표가 모순됩니다."
    if wcs_check["status"] == "pass":
        return "confirmed", "Plate Solving WCS와 HIP 좌표가 일치해 후보를 확정했습니다."
    if structural["status"] == "strong" and visibility["status"] == "pass":
        return "provisional", "강한 그래프 근거와 가시성은 일치하지만 WCS 확정이 필요합니다."
    return "needs_plate_solve", "후보를 독립적으로 확정할 WCS 정보가 필요합니다."


def check_rows(
    structural: dict[str, Any],
    observation: dict[str, Any],
    visibility: dict[str, Any],
    wcs_check: dict[str, Any],
    status: str,
    reason: str,
) -> list[dict[str, str]]:
    metadata_available = (
        observation["latitude"] is not None
        and observation["longitude"] is not None
        and observation["captured_at_utc"] is not None
    )
    rows = [
        {"check": "structural", "status": structural["status"], "summary": structural["summary"]},
        {
            "check": "observation_metadata",
            "status": "available" if metadata_available else "not_available",
            "summary": (
                "촬영 시각과 GPS를 사용할 수 있습니다."
                if metadata_available
                else "촬영 시각 또는 GPS가 부족합니다."
            ),
        },
        {"check": "horizon_visibility", "status": visibility["status"], "summary": visibility["summary"]},
    ]
    if "candidate_reprojection" in wcs_check:
        check = wcs_check["candidate_reprojection"]
        rows.append(
            {"check": "candidate_reprojection", "status": check["status"], "summary": check["summary"]}
        )
    if "global_reprojection" in wcs_check:
        check = wcs_check["global_reprojection"]
        rows.append(
            {"check": "global_reprojection", "status": check["status"], "summary": check["summary"]}
        )
    rows.extend(
        (
            {"check": "wcs_plate_solve", "status": wcs_check["status"], "summary": wcs_check["summary"]},
            {"check": "final", "status": status, "summary": reason},
        )
    )
    return rows


def create_validation_image(
    base: np.ndarray,
    best: dict[str, Any] | None,
    structural: dict[str, Any],
    observation: dict[str, Any],
    visibility: dict[str, Any],
    wcs_check: dict[str, Any],
    final_status: str,
) -> np.ndarray:
    image = base.copy()
    panel_height = max(250, round(image.shape[0] * 0.16))
    cv2.rectangle(image, (0, 0), (image.shape[1], panel_height), (0, 0, 0), -1)
    candidate = "none" if best is None else f"{best['iau']} / {best['native_name']}"
    location_text = (
        "missing"
        if observation["latitude"] is None
        else f"{observation['latitude']:.4f},{observation['longitude']:.4f}"
    )
    time_text = observation["captured_at_utc"] or "missing"
    lines = [
        f"Validation: {candidate} | final={final_status}",
        f"Structural={structural['status']} | confidence={structural.get('details', {}).get('confidence', 'none')}",
        f"Observation UTC={time_text} | GPS={location_text}",
        f"Horizon visibility={visibility['status']} | WCS={wcs_check['status']}",
        "Candidate reproj={} | Global reproj={}".format(
            wcs_check.get("candidate_reprojection", {}).get("status", "N/A"),
            wcs_check.get("global_reprojection", {}).get("status", "N/A"),
        ),
        "CONFIRMED requires WCS-to-HIP sky-coordinate agreement",
    ]
    status_color = {
        "confirmed": (40, 255, 40),
        "provisional": (0, 220, 255),
        "needs_plate_solve": (0, 180, 255),
        "rejected": (40, 40, 255),
    }.get(final_status, (255, 255, 255))
    font_scale = max(0.50, image.shape[1] / 4300)
    line_height = panel_height / (len(lines) + 0.5)
    for index, line in enumerate(lines):
        cv2.putText(
            image,
            line,
            (20, round((index + 1) * line_height)),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale * (1.12 if index == 0 else 1.0),
            status_color if index == 0 else (230, 230, 230),
            2,
            cv2.LINE_AA,
        )
    return image


def write_checks_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["check", "status", "summary"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    if args.max_angular_error_arcsec <= 0:
        raise ValueError("max-angular-error-arcsec는 0보다 커야 합니다.")
    if args.gaia_max_magnitude <= 0:
        raise ValueError("gaia-max-magnitude는 0보다 커야 합니다.")
    if args.global_match_radius_px <= 0 or args.max_candidate_reprojection_error_px <= 0:
        raise ValueError("재투영 픽셀 오차 기준은 0보다 커야 합니다.")
    if args.minimum_global_matches < 3:
        raise ValueError("minimum-global-matches는 3 이상이어야 합니다.")
    matching_path = args.matching.resolve()
    stem = output_stem(matching_path)
    matching = load_matching(matching_path)
    image_path = Path(matching["image"]).resolve()
    original = read_image(image_path)
    best = matching["results"][0] if matching["results"] else None
    hips = {int(item["hip"]) for item in (best.get("mappings", []) if best else [])}
    hyg_path = (
        args.hyg.resolve()
        if args.hyg
        else Path(matching.get("reference", {}).get("hyg", DEFAULT_HYG)).resolve()
    )
    coordinates = load_hyg_coordinates(hyg_path, hips)
    observation = resolve_observation_metadata(
        image_path,
        args.latitude,
        args.longitude,
        args.captured_at,
        args.utc_offset_hours,
    )
    structural = structural_validation(matching)
    visibility = visibility_validation(
        best,
        coordinates,
        observation,
        args.minimum_altitude_deg,
    )
    wcs_path = args.wcs.resolve() if args.wcs else None
    detection_path = (
        args.star_detection.resolve()
        if args.star_detection
        else DEFAULT_DETECTION_ROOT / stem / f"{stem}_stars.json"
    )
    wcs_check = wcs_validation(
        best,
        coordinates,
        wcs_path,
        detection_path,
        args.gaia.resolve(),
        original.shape[1],
        original.shape[0],
        args.max_angular_error_arcsec,
        args.gaia_max_magnitude,
        args.global_match_radius_px,
        args.minimum_global_matches,
        args.max_candidate_reprojection_error_px,
    )
    final_status, reason = final_decision(structural, visibility, wcs_check)
    rows = check_rows(structural, observation, visibility, wcs_check, final_status, reason)

    output_dir = args.output_dir.resolve() / stem
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}_validation.json"
    csv_path = output_dir / f"{stem}_validation_checks.csv"
    image_output_path = output_dir / f"{stem}_validated.jpg"
    payload = {
        "source_matching": str(matching_path),
        "image": str(image_path),
        "candidate": None
        if best is None
        else {
            "iau": best["iau"],
            "english_name": best["english_name"],
            "native_name": best["native_name"],
        },
        "observation": observation,
        "structural_validation": structural,
        "horizon_visibility": visibility,
        "wcs_validation": wcs_check,
        "decision": {
            "status": final_status,
            "reason": reason,
            "confirmed": final_status == "confirmed",
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_checks_csv(csv_path, rows)

    matched_image_path = matching_path.parent / f"{stem}_matched.jpg"
    base = read_image(matched_image_path) if matched_image_path.is_file() else original
    validated_image = create_validation_image(
        base,
        best,
        structural,
        observation,
        visibility,
        wcs_check,
        final_status,
    )
    write_image(image_output_path, validated_image)

    print(f"후보: {best['iau'] + ' / ' + best['native_name'] if best else '없음'}")
    print(f"구조 검증: {structural['status']} - {structural['summary']}")
    print(f"촬영 시각(UTC): {observation['captured_at_utc'] or '없음'}")
    print(
        "촬영 위치: "
        + (
            f"{observation['latitude']:.6f}, {observation['longitude']:.6f}"
            if observation["latitude"] is not None
            else "없음"
        )
    )
    print(f"지평선 가시성: {visibility['status']} - {visibility['summary']}")
    print(f"WCS 검증: {wcs_check['status']} - {wcs_check['summary']}")
    if "candidate_reprojection" in wcs_check:
        candidate_check = wcs_check["candidate_reprojection"]
        print(
            "후보 재투영: "
            f"{candidate_check['status']} - median {candidate_check['median_error_px']}px, "
            f"p90 {candidate_check['p90_error_px']}px"
        )
    if "global_reprojection" in wcs_check:
        global_check = wcs_check["global_reprojection"]
        print(
            "사진 전체 재투영: "
            f"{global_check['status']} - {global_check.get('matched_stars', 0)}개 일치"
        )
    print(f"최종 판정: {final_status}")
    print(f"판정 이유: {reason}")
    print(f"checks_csv: {csv_path}")
    print(f"validation_json: {json_path}")
    print(f"validated_image: {image_output_path}")


if __name__ == "__main__":
    main()
