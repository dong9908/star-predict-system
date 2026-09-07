from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fortune.models import FortuneDailyResultModel
from fortune.schemas import InitialFortuneResponse


def get_daily_fortune(
    db: Session,
    user_id: int,
    fortune_date: date,
) -> InitialFortuneResponse | None:
    stored_result = (
        db.query(FortuneDailyResultModel)
        .filter(
            FortuneDailyResultModel.user_id == user_id,
            FortuneDailyResultModel.fortune_date == fortune_date,
        )
        .first()
    )
    if stored_result is None:
        return None
    return InitialFortuneResponse.model_validate(stored_result.result_json)


def save_daily_fortune(
    db: Session,
    user_id: int,
    fortune_date: date,
    zodiac_code: str,
    result: InitialFortuneResponse,
    model_name: str | None = None,
) -> InitialFortuneResponse:
    stored_result = FortuneDailyResultModel(
        user_id=user_id,
        fortune_date=fortune_date,
        zodiac_code=zodiac_code,
        result_json=result.model_dump(mode="json", by_alias=True),
        model_name=model_name,
    )
    db.add(stored_result)

    try:
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        existing_result = get_daily_fortune(db, user_id, fortune_date)
        if existing_result is None:
            raise
        return existing_result
