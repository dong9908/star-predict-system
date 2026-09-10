import csv
import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
import numpy as np

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u

from sqlalchemy.orm import Session

from models.constellation import ConstellationModel
from models.star import StarModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STELLARIUM_LINES = PROJECT_ROOT / "Constellation" / "data" / "reference" / "stellarium" / "western" / "index.json"
HYG_CATALOG = PROJECT_ROOT / "Constellation" / "HYG-Database-main" / "hyg" / "CURRENT" / "hygdata_v41.csv"
IMAGE_STAR_POSITIONS = Path(__file__).with_name("constellation_image_star_positions.json")
AUDITED_IMAGE_STAR_POSITIONS = Path(__file__).with_name("constellation_image_star_positions_wcs_audit.json")


@lru_cache(maxsize=1)
def load_line_star_references():
    if not STELLARIUM_LINES.is_file() or not HYG_CATALOG.is_file():
        return {}, {}
    payload = json.loads(STELLARIUM_LINES.read_text(encoding="utf-8"))
    line_hips_by_iau = {}
    required_hips = set()
    for entry in payload.get("constellations", []):
        iau = str(entry.get("iau") or "")
        hips = {
            int(value)
            for line in entry.get("lines", [])
            for value in line
            if isinstance(value, (int, float))
        }
        if iau and hips:
            line_hips_by_iau[iau] = hips
            required_hips.update(hips)

    stars_by_hip = {}
    with HYG_CATALOG.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            raw_hip = str(row.get("hip") or "").strip()
            if not raw_hip:
                continue
            hip = int(raw_hip)
            if hip not in required_hips:
                continue
            try:
                stars_by_hip[hip] = {
                    "hip": hip,
                    "proper": str(row.get("proper") or "").strip(),
                    "ra": float(row["ra"]),
                    "dec": float(row["dec"]),
                }
            except (TypeError, ValueError):
                continue
    return line_hips_by_iau, stars_by_hip


def load_image_star_positions():
    """Return per-image HIP marker positions measured from catalog assets."""
    if not IMAGE_STAR_POSITIONS.is_file():
        return {}

    try:
        payload = json.loads(IMAGE_STAR_POSITIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    positions = {}
    for iau, config in payload.items():
        stars = config.get("stars", config) if isinstance(config, dict) else {}
        if not isinstance(stars, dict):
            continue
        positions[iau] = {
            int(hip): value
            for hip, value in stars.items()
            if str(hip).isdigit() and isinstance(value, dict)
        }
    if AUDITED_IMAGE_STAR_POSITIONS.is_file():
        try:
            audited = json.loads(AUDITED_IMAGE_STAR_POSITIONS.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            audited = {}
        for iau, stars in audited.items():
            if not isinstance(stars, dict):
                continue
            target = positions.setdefault(iau, {})
            for hip, coordinates in stars.items():
                if not str(hip).isdigit() or not isinstance(coordinates, list) or len(coordinates) != 2:
                    continue
                target[int(hip)] = {
                    "x_percent": coordinates[0],
                    "y_percent": coordinates[1],
                }
    return positions


def load_image_line_points(abbreviation):
    if not IMAGE_STAR_POSITIONS.is_file():
        return []
    try:
        payload = json.loads(IMAGE_STAR_POSITIONS.read_text(encoding="utf-8"))
        points = payload.get(abbreviation, {}).get("line_points", [])
    except (OSError, AttributeError, json.JSONDecodeError):
        return []

    audited_positions = load_image_star_positions().get(abbreviation, {})
    result = []
    included_hips = set()
    for index, point in enumerate(points):
        try:
            hip = int(point["hip"]) if point.get("hip") is not None else None
            audited = audited_positions.get(hip)
            result.append({
                "point_id": index,
                "hip": hip,
                "x_percent": float(audited["x_percent"] if audited else point["x_percent"]),
                "y_percent": float(audited["y_percent"] if audited else point["y_percent"]),
            })
            if hip is not None:
                included_hips.add(hip)
        except (KeyError, TypeError, ValueError):
            continue
    for hip, point in audited_positions.items():
        if hip in included_hips or point.get("clickable") is False:
            continue
        try:
            result.append({
                "point_id": len(result),
                "hip": hip,
                "x_percent": float(point["x_percent"]),
                "y_percent": float(point["y_percent"]),
            })
        except (KeyError, TypeError, ValueError):
            continue
    return result


def get_constellation_stars(
    db: Session,
    constellation_name: str
):
    # 1. 별자리 이름으로 constellations 테이블 조회
    constellation = (
        db.query(ConstellationModel)
        .filter(ConstellationModel.name_ko == constellation_name)
        .first()
    )

    if not constellation:
        return None

    # 2. 별자리 약어 가져오기
    abbreviation = constellation.abbreviation

    # 3. 뱀자리 머리 / 꼬리는 통합 Ser로 계산
    if abbreviation in ["SerH", "SerT"]:
        abbreviation = "Ser"

    # 4. star 테이블에서 해당 별자리의 별 조회
    stars = (
        db.query(StarModel)
        .filter(StarModel.con == abbreviation)
        .filter(StarModel.ra.isnot(None))
        .filter(StarModel.dec_val.isnot(None))
        .filter(StarModel.mag.isnot(None))
        .all()
    )

    if not stars:
        return None

    # 5. DataFrame으로 변환
    df = pd.DataFrame([
        {
            "id": star.id,
            "proper": star.proper,
            "proper_ko": star.proper_ko,
            "ra": star.ra,
            "dec": star.dec_val,
            "mag": star.mag,
            "con": star.con,
        }
        for star in stars
    ])

    # 6. 6등급 이하의 별만 사용
    bright_stars = df[df["mag"] <= 6]

    return bright_stars


def get_main_stars(
    db: Session,
    abbreviation: str
):
    original_abbreviation = abbreviation
    # 뱀자리 머리 / 꼬리 처리
    if abbreviation in ["SerH", "SerT"]:
        abbreviation = "Ser"

    # 별자리의 밝은 별 최대 3개 조회
    main_stars = (
        db.query(StarModel)
        .filter(StarModel.con == abbreviation)
        .filter(StarModel.proper.isnot(None))
        .filter(StarModel.proper != "")
        .filter(StarModel.mag.isnot(None))
        .order_by(StarModel.mag.asc())
        .all()
    )

    line_hips_by_iau, stars_by_hip = load_line_star_references()
    line_hips = set(line_hips_by_iau.get(original_abbreviation, set()))
    if original_abbreviation in {"SerH", "SerT", "Ser"}:
        line_hips = set().union(*(
            hips for iau, hips in line_hips_by_iau.items() if iau.startswith("Ser")
        ))
    line_stars = [stars_by_hip[hip] for hip in line_hips if hip in stars_by_hip]
    hip_by_name = {
        star["proper"].casefold(): star["hip"]
        for star in line_stars
        if star["proper"]
    }
    image_positions = load_image_star_positions().get(original_abbreviation, {})
    main_stars = main_stars[:3]

    projected = []
    if line_stars:
        ra_degrees = np.asarray([star["ra"] * 15.0 for star in line_stars])
        dec_degrees = np.asarray([star["dec"] for star in line_stars])
        radians = np.deg2rad(ra_degrees)
        center_ra = np.rad2deg(np.arctan2(np.mean(np.sin(radians)), np.mean(np.cos(radians)))) % 360
        center_dec = float(np.mean(dec_degrees))
        projected_x = ((ra_degrees - center_ra + 180) % 360 - 180) * np.cos(np.deg2rad(center_dec))
        projected = [
            (float(x), float(dec))
            for x, dec in zip(projected_x, dec_degrees)
        ]

    def relative_position(star):
        hip = hip_by_name.get(str(star.proper or "").casefold())
        image_position = image_positions.get(hip)
        if image_position is not None:
            if image_position.get("clickable") is False:
                return {"clickable": False, "x_percent": None, "y_percent": None}
            try:
                return {
                    "clickable": True,
                    "x_percent": round(float(image_position["x_percent"]), 2),
                    "y_percent": round(float(image_position["y_percent"]), 2),
                }
            except (KeyError, TypeError, ValueError):
                pass
        if not hip or not projected or star.ra is None or star.dec_val is None:
            return {"clickable": False, "x_percent": None, "y_percent": None}
        radians = np.deg2rad([item["ra"] * 15.0 for item in line_stars])
        center_ra = np.rad2deg(np.arctan2(np.mean(np.sin(radians)), np.mean(np.cos(radians)))) % 360
        center_dec = float(np.mean([item["dec"] for item in line_stars]))
        x = ((float(star.ra) * 15.0 - center_ra + 180) % 360 - 180) * np.cos(np.deg2rad(center_dec))
        xs = [item[0] for item in projected]
        ys = [item[1] for item in projected]
        x_span = max(xs) - min(xs)
        y_span = max(ys) - min(ys)
        # 일반적인 천구도처럼 적경 증가 방향을 왼쪽으로 표시합니다.
        x_percent = 50.0 if x_span == 0 else 90.0 - ((x - min(xs)) / x_span * 80.0)
        y_percent = 50.0 if y_span == 0 else 90.0 - ((float(star.dec_val) - min(ys)) / y_span * 80.0)
        return {
            "clickable": True,
            "x_percent": round(float(x_percent), 2),
            "y_percent": round(float(y_percent), 2),
        }

    return [
        {
            "star_id": star.id,
            "hip": hip_by_name.get(str(star.proper or "").casefold()),
            "name": star.proper_ko,
            "name_en": star.proper,
            "mag": star.mag,
            **relative_position(star),
        }
        for star in main_stars
    ]


def calculate_star_positions(
    stars,
    date: str,
    time: str,
    latitude: float,
    longitude: float
):
    # 관측 위치
    location = EarthLocation(
        lat=latitude * u.deg,
        lon=longitude * u.deg,
    )

    # 관측 날짜와 시간
    observation_time = Time(f"{date} {time}:00")

    # 별의 적경(RA), 적위(Dec)
    coordinates = SkyCoord(
        ra=stars["ra"].values * u.hourangle,
        dec=stars["dec"].values * u.deg,
        frame="icrs",
    )

    # 해당 시간/위치의 지평 좌표계로 변환
    altaz = coordinates.transform_to(
        AltAz(
            obstime=observation_time,
            location=location,
        )
    )

    # 결과 복사
    result = stars.copy()

    result["altitude"] = altaz.alt.deg
    result["azimuth"] = altaz.az.deg

    return result


def get_constellation_detail(
    db: Session,
    constellation_id: int
):
    # 1. 별자리 정보 조회
    constellation = (
        db.query(ConstellationModel)
        .filter(
            ConstellationModel.constellation_id == constellation_id
        )
        .first()
    )

    if not constellation:
        return None

    # 2. 밝은 주요 별 최대 3개 조회
    main_stars = get_main_stars(
        db,
        constellation.abbreviation
    )

    return {
        "constellation_id": constellation.constellation_id,
        "name_ko": constellation.name_ko,
        "name_en": constellation.name_en,
        "description": constellation.description,
        "mythology": constellation.mythology,
        "difficulty": constellation.difficulty,
        "image_url": constellation.image_url,
        "abbreviation": constellation.abbreviation,

        "main_stars": main_stars,
        "image_line_points": load_image_line_points(constellation.abbreviation),
    }
