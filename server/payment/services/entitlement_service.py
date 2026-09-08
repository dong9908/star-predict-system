from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.member import UserModel
from payment.models import PaymentModel, PaymentStatus


SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


def get_seoul_now() -> datetime:
    """MySQL DATETIME과 비교할 서울 기준 naive datetime을 반환한다."""
    return datetime.now(SEOUL_TIMEZONE).replace(tzinfo=None)


def get_active_fortune_payment(
    db: Session,
    user_id: int,
    now: datetime | None = None,
) -> PaymentModel | None:
    current_time = now or get_seoul_now()
    return (
        db.query(PaymentModel)
        .filter(
            PaymentModel.user_id == user_id,
            PaymentModel.status == PaymentStatus.APPROVED,
            PaymentModel.access_expires_at.is_not(None),
            PaymentModel.access_expires_at > current_time,
        )
        .order_by(PaymentModel.access_expires_at.desc())
        .first()
    )


def has_fortune_access(db: Session, user: UserModel) -> bool:
    return get_active_fortune_payment(db, user.user_id) is not None


def sync_fortune_access(db: Session, user: UserModel) -> bool:
    has_access = has_fortune_access(db, user)
    user.has_fortune_access = has_access
    return has_access


def grant_fortune_access(user: UserModel) -> None:
    user.has_fortune_access = True


def revoke_fortune_access(user: UserModel) -> None:
    user.has_fortune_access = False
