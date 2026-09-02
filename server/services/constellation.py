from pathlib import Path
import pandas as pd
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u

# 서버에서 실행 되는지 임시 테스트 경로. 나중에 DB에 추가하며 삭제 예정.
CSV_PATH = Path(r"C:\dev\hyg\data\hyg\CURRENT\hyg_v44.csv.gz")


# 별자리 한글 이름 → HYG 데이터의 별자리 약어
CONSTELLATION_MAP = {
    "오리온자리": "Ori",
    # 나중에 전체 별자리 추가
}


def load_star_data():
    df = pd.read_csv(CSV_PATH)

    print("========== CSV 로딩 완료 ==========")
    print("전체 데이터 개수:", len(df))
    print("컬럼:", df.columns.tolist())

    return df


def get_constellation_stars(constellation_name: str):
    abbreviation = CONSTELLATION_MAP.get(constellation_name)

    if not abbreviation:
        return None

    df = load_star_data()

    stars = df[df["con"] == abbreviation]
    # 가장 밝은 6개의 별만 사용. (이유: 오리온 자리의 경우 1977개의 별이 있음.)
    bright_stars = stars[stars["mag"] <= 6]

    return bright_stars

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