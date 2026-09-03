from uuid import uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from models.member import UserModel
from payment.config import KakaoPaySettings, get_kakaopay_settings
from payment.exceptions import (
    PaymentAmountMismatchError,
    PaymentConfigurationError,
    PaymentConflictError,
    PaymentInvalidStateError,
    PaymentNotFoundError,
    PaymentProviderResponseError,
)
from payment.models import PaymentModel, PaymentStatus
from payment.providers.kakaopay_provider import KakaoPayProvider
from payment.schemas import KakaoPayApprovalResponse, KakaoPayReadyResponse
from payment.services.entitlement_service import grant_fortune_access


def generate_partner_order_id(user_id: int) -> str:
    return f"FORTUNE-{user_id}-{uuid4().hex.upper()}"


def get_user_payment_by_order_id(
    db: Session,
    user_id: int,
    partner_order_id: str,
) -> PaymentModel:
    payment = (
        db.query(PaymentModel)
        .filter(
            PaymentModel.partner_order_id == partner_order_id,
            PaymentModel.user_id == user_id,
        )
        .first()
    )
    if payment is None:
        raise PaymentNotFoundError("결제 정보를 찾을 수 없습니다.")
    return payment


def list_user_payments(db: Session, user_id: int) -> list[PaymentModel]:
    return (
        db.query(PaymentModel)
        .filter(PaymentModel.user_id == user_id)
        .order_by(PaymentModel.created_at.desc())
        .all()
    )


async def prepare_fortune_payment(
    db: Session,
    user: UserModel,
    provider: KakaoPayProvider | None = None,
    settings: KakaoPaySettings | None = None,
) -> tuple[PaymentModel, KakaoPayReadyResponse]:
    try:
        active_settings = settings or get_kakaopay_settings()
    except ValueError as error:
        raise PaymentConfigurationError(str(error)) from error

    active_provider = provider or KakaoPayProvider(active_settings)
    payment = PaymentModel(
        user_id=user.user_id,
        partner_order_id=generate_partner_order_id(user.user_id),
        item_name=active_settings.product_name,
        amount=active_settings.product_price,
        status=PaymentStatus.READY,
    )

    try:
        db.add(payment)
        db.flush()
        ready_response = await active_provider.ready(
            payment.partner_order_id,
            str(user.user_id),
        )
        payment.tid = ready_response.tid
        db.commit()
        db.refresh(payment)
        return payment, ready_response
    except IntegrityError as error:
        db.rollback()
        raise PaymentConflictError("중복된 결제 주문이 생성되었습니다.") from error
    except Exception:
        db.rollback()
        raise


def _validate_approval(
    payment: PaymentModel,
    user: UserModel,
    approval: KakaoPayApprovalResponse,
    settings: KakaoPaySettings,
) -> None:
    if approval.tid != payment.tid:
        raise PaymentProviderResponseError("카카오페이 거래번호가 일치하지 않습니다.")
    if approval.cid != settings.cid:
        raise PaymentProviderResponseError("카카오페이 가맹점 코드가 일치하지 않습니다.")
    if approval.partner_order_id != payment.partner_order_id:
        raise PaymentProviderResponseError("카카오페이 주문번호가 일치하지 않습니다.")
    if approval.partner_user_id != str(user.user_id):
        raise PaymentProviderResponseError("카카오페이 사용자 정보가 일치하지 않습니다.")
    if approval.amount.total != payment.amount:
        raise PaymentAmountMismatchError("카카오페이 승인 금액이 주문 금액과 다릅니다.")
    if approval.item_name != payment.item_name:
        raise PaymentProviderResponseError("카카오페이 결제 상품이 일치하지 않습니다.")


async def approve_fortune_payment(
    db: Session,
    user: UserModel,
    partner_order_id: str,
    pg_token: str,
    provider: KakaoPayProvider | None = None,
    settings: KakaoPaySettings | None = None,
) -> PaymentModel:
    payment = get_user_payment_by_order_id(
        db,
        user.user_id,
        partner_order_id,
    )

    if payment.status == PaymentStatus.APPROVED:
        if not user.has_fortune_access:
            grant_fortune_access(user)
            db.commit()
        return payment
    if payment.status != PaymentStatus.READY:
        raise PaymentInvalidStateError(
            f"{payment.status.value} 상태의 결제는 승인할 수 없습니다.",
        )
    if not payment.tid:
        raise PaymentInvalidStateError("결제 준비 거래번호가 없습니다.")

    try:
        active_settings = settings or get_kakaopay_settings()
    except ValueError as error:
        raise PaymentConfigurationError(str(error)) from error
    active_provider = provider or KakaoPayProvider(active_settings)

    try:
        approval = await active_provider.approve(
            payment.tid,
            payment.partner_order_id,
            str(user.user_id),
            pg_token,
        )
        _validate_approval(payment, user, approval, active_settings)

        payment.aid = approval.aid
        payment.status = PaymentStatus.APPROVED
        payment.approved_at = approval.approved_at
        grant_fortune_access(user)

        db.commit()
        db.refresh(payment)
        return payment
    except IntegrityError as error:
        db.rollback()
        raise PaymentConflictError("이미 처리된 카카오페이 거래입니다.") from error
    except SQLAlchemyError:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
