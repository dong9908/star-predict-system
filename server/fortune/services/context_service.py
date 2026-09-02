from datetime import date, datetime
from zoneinfo import ZoneInfo

from models.member import UserModel

from fortune.schemas import FortuneContextResponse
from fortune.services.zodiac_service import calculate_zodiac


SEOUL_TZ = ZoneInfo("Asia/Seoul")


def build_fortune_context(
    user: UserModel,
    current_date: date | None = None,
) -> FortuneContextResponse:
    """Build the stable user context consumed by later fortune stages."""
    if user.birth_date is None:
        raise ValueError("사용자의 생년월일 정보가 없습니다.")

    today = current_date or datetime.now(SEOUL_TZ).date()
    return FortuneContextResponse(
        user_id=user.user_id,
        birth_date=user.birth_date,
        today=today,
        zodiac=calculate_zodiac(user.birth_date),
    )
