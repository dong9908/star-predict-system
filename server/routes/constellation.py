import numpy as np

from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from database.connection import get_db
from models.constellation import ConstellationModel
from models.user_constellation import UserConstellationModel
from models.member import UserModel
from core.security import get_current_user
from schemas.constellation import ConstellationRequest
from services.constellation import (
    get_constellation_stars,
    calculate_star_positions,
    get_main_stars,
    get_constellation_detail,
)

constellation_router = APIRouter()

# 0도 근처의 중앙값을 제대로 가져오게끔 360도 원형으로 설정
def circular_median(angles):
    angles = np.asarray(angles)

    # 각도를 0~360 범위로 정규화
    angles = angles % 360

    # 각도를 라디안으로 변환
    radians = np.deg2rad(angles)

    # 기준점을 하나씩 잡아 가장 가까운 각도의 중앙값을 찾음
    candidates = angles

    best_angle = None
    best_distance = float("inf")

    for candidate in candidates:
        differences = np.abs(
            np.angle(
                np.exp(1j * (radians - np.deg2rad(candidate)))
            )
        )

        total_distance = np.sum(differences)

        if total_distance < best_distance:
            best_distance = total_distance
            best_angle = candidate

    return float(best_angle % 360)

def get_direction(azimuth: float):
    directions = [
        "북",
        "북동",
        "동",
        "남동",
        "남",
        "남서",
        "서",
        "북서",
    ]

    index = int((azimuth + 22.5) // 45) % 8

    return directions[index]

@constellation_router.post("/position")
def get_constellation_position(
    request: ConstellationRequest,
    db: Session = Depends(get_db)):

    # 1. 별자리 이름으로 별 데이터 조회
    stars = get_constellation_stars(
        db,
        request.constellation)

    if stars is None or stars.empty:
        return {
            "message": "해당 별자리를 찾을 수 없습니다."
        }

    # 2. Astropy로 별 위치 계산
    result = calculate_star_positions(
        stars,
        request.date,
        request.time,
        request.latitude,
        request.longitude,
    )

    # 3. 현재 지평선 위에 있는 별
    visible_stars = result[result["altitude"] > 0]

    # 4. 관측 상태
    if len(visible_stars) == len(result):
        observable = "전체 관측 가능"
    elif len(visible_stars) > 0:
        observable = "일부 관측 가능"
    else:
        observable = "현재 관측 불가"

    # 5. 대표 고도 / 방위각
    altitude = result["altitude"].median()
    azimuth = circular_median(result["azimuth"].values)

    return {
        "constellation": request.constellation,
        "observable": observable,
        "altitude": round(float(altitude), 2),
        "azimuth": round(float(azimuth), 2),
        "direction": get_direction(float(azimuth)),
    }

# 별자리 목록 조회 (가벼운 카탈로그용)
@constellation_router.get("/catalog")
def get_constellation_catalog(
    db: Session = Depends(get_db)
):

    constellations = (
        db.query(
            ConstellationModel.constellation_id,
            ConstellationModel.name_ko,
            ConstellationModel.name_en,
            ConstellationModel.image_url,
        )
        .order_by(
            ConstellationModel.constellation_id
        )
        .all()
    )

    result = []

    for constellation in constellations:
        result.append({
            "constellation_id": constellation.constellation_id,
            "name_ko": constellation.name_ko,
            "name_en": constellation.name_en,
            "image_url": constellation.image_url,
        })

    return result

# 개인 도감용 별자리 목록 조회
@constellation_router.get("/catalog/my")
def get_catalog_my(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # 전체 별자리 기본 정보
    constellations = (
        db.query(
            ConstellationModel.constellation_id,
            ConstellationModel.name_ko,
            ConstellationModel.image_url,
            ConstellationModel.difficulty,
        )
        .order_by(
            ConstellationModel.constellation_id
        )
        .all()
    )

    # 현재 사용자가 발견한 별자리
    user_constellations = (
        db.query(UserConstellationModel)
        .filter(
            UserConstellationModel.user_id
            == current_user.user_id
        )
        .all()
    )

    # 빠른 검색용 Map
    my_map = {
        item.constellation_id: item
        for item in user_constellations
    }

    result = []

    for constellation in constellations:
        discovered = my_map.get(
            constellation.constellation_id
        )


        result.append({
            "constellation_id":
                constellation.constellation_id,
            "name_ko":
                constellation.name_ko,
            "image_url":
                constellation.image_url,
            "difficulty":
                constellation.difficulty,
            "discovered":
                discovered is not None,
            "discovered_at":
                discovered.discovered_at
                if discovered else None
        })

    return result

# 별자리 전체 목록 조회
@constellation_router.get("/")
def get_constellations(db: Session = Depends(get_db)):

    constellations = (
        db.query(ConstellationModel)
        .order_by(ConstellationModel.constellation_id)
        .all()
    )

    result = []

    for constellation in constellations:

        main_stars = get_main_stars(
            db,
            constellation.abbreviation
        )

        result.append({
            "constellation_id": constellation.constellation_id,
            "name_ko": constellation.name_ko,
            "name_en": constellation.name_en,
            "description": constellation.description,
            "mythology": constellation.mythology,
            "difficulty": constellation.difficulty,
            "image_url": constellation.image_url,
            "abbreviation": constellation.abbreviation,
            "main_stars": main_stars,
        })

    return result

# 내가 발견한 별자리 목록 조회
@constellation_router.get("/my")
def get_my_constellations(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_constellations = (
        db.query(
            UserConstellationModel,
            ConstellationModel
        )
        .join(
            ConstellationModel,
            UserConstellationModel.constellation_id
            == ConstellationModel.constellation_id
        )
        .filter(
            UserConstellationModel.user_id == current_user.user_id
        )
        .order_by(
            UserConstellationModel.discovered_at.desc()
        )
        .all()
    )

    result = []

    for user_constellation, constellation in user_constellations:
        result.append({
            "user_constellation_id": user_constellation.user_constellation_id,
            "constellation_id": constellation.constellation_id,
            "name_ko": constellation.name_ko,
            "name_en": constellation.name_en,
            "image_url": user_constellation.image_url or constellation.image_url,
            "discovered_at": user_constellation.discovered_at,
        })

    return result

# 별자리 상세 정보 조회
@constellation_router.get("/{constellation_id}")
def get_constellation_detail_by_id(
    constellation_id: int,
    db: Session = Depends(get_db)
):
    constellation = get_constellation_detail(
        db,
        constellation_id
    )

    if not constellation:
        return {
            "message": "해당 별자리 정보를 찾을 수 없습니다."
        }

    return constellation