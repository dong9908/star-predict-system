import pandas as pd

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u

from sqlalchemy.orm import Session

from models.constellation import ConstellationModel
from models.star import StarModel


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
            "ra": star.ra,
            "dec": star.dec_val,
            "mag": star.mag,
            "con": star.con,
        }
        for star in stars
    ])

    # 6. 가장 밝은 별만 사용
    bright_stars = df[df["mag"] <= 6]

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