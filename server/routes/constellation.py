import numpy as np

from fastapi import APIRouter
from schemas.constellation import ConstellationRequest
from services.constellation import (
    get_constellation_stars,
    calculate_star_positions,
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
def get_constellation_position(request: ConstellationRequest):

    # 1. 별자리 이름으로 별 데이터 조회
    stars = get_constellation_stars(request.constellation)

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