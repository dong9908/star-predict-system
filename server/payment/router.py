from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from database.connection import get_db
from models.member import UserModel
from payment.exceptions import (
    PaymentAmountMismatchError,
    PaymentAuthenticationError,
    PaymentConfigurationError,
    PaymentConflictError,
    PaymentError,
    PaymentInvalidStateError,
    PaymentNotFoundError,
    PaymentProviderResponseError,
    PaymentProviderUnavailableError,
)
from payment.schemas import (
    PaymentAccessResponse,
    PaymentApprovalResponse,
    PaymentApproveRequest,
    PaymentHistoryItem,
    PaymentReadyResponse,
)
from payment.services.entitlement_service import has_fortune_access
from payment.services.payment_service import (
    approve_fortune_payment,
    list_user_payments,
    prepare_fortune_payment,
)


payment_router = APIRouter()


@payment_router.post(
    "/ready",
    response_model=PaymentReadyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ready_fortune_payment(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentReadyResponse:
    try:
        payment, ready = await prepare_fortune_payment(db, user)
    except Exception as error:
        raise _to_http_exception(error) from error

    pc_url = str(ready.next_redirect_pc_url)
    mobile_url = (
        str(ready.next_redirect_mobile_url)
        if ready.next_redirect_mobile_url
        else None
    )
    app_url = (
        str(ready.next_redirect_app_url)
        if ready.next_redirect_app_url
        else None
    )
    return PaymentReadyResponse(
        payment_id=payment.payment_id,
        partner_order_id=payment.partner_order_id,
        redirect_url=pc_url,
        pc_redirect_url=pc_url,
        mobile_redirect_url=mobile_url,
        app_redirect_url=app_url,
        status=payment.status,
    )


@payment_router.post(
    "/approve",
    response_model=PaymentApprovalResponse,
)
async def approve_payment(
    request: PaymentApproveRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentApprovalResponse:
    try:
        payment = await approve_fortune_payment(
            db,
            user,
            request.partner_order_id,
            request.pg_token,
        )
    except Exception as error:
        raise _to_http_exception(error) from error

    if payment.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="승인된 결제의 승인 시간이 없습니다.",
        )

    return PaymentApprovalResponse(
        payment_id=payment.payment_id,
        partner_order_id=payment.partner_order_id,
        item_name=payment.item_name,
        amount=payment.amount,
        status=payment.status,
        approved_at=payment.approved_at,
        has_fortune_access=has_fortune_access(user),
    )


@payment_router.get(
    "/history",
    response_model=list[PaymentHistoryItem],
)
async def get_payment_history(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentHistoryItem]:
    return [
        PaymentHistoryItem.model_validate(payment)
        for payment in list_user_payments(db, user.user_id)
    ]


@payment_router.get(
    "/access",
    response_model=PaymentAccessResponse,
)
async def get_payment_access(
    user: UserModel = Depends(get_current_user),
) -> PaymentAccessResponse:
    return PaymentAccessResponse(
        has_fortune_access=has_fortune_access(user),
    )


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, PaymentNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="결제 정보를 찾을 수 없습니다.",
        )
    if isinstance(
        error,
        (PaymentConflictError, PaymentInvalidStateError),
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )
    if isinstance(error, PaymentAmountMismatchError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="승인 금액이 주문 금액과 일치하지 않습니다.",
        )
    if isinstance(error, PaymentProviderUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="카카오페이 서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.",
        )
    if isinstance(
        error,
        (
            PaymentAuthenticationError,
            PaymentConfigurationError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="결제 서비스를 사용할 수 없습니다.",
        )
    if isinstance(error, PaymentProviderResponseError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="카카오페이 응답을 처리하지 못했습니다.",
        )
    if isinstance(error, PaymentError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="카카오페이 결제 요청에 실패했습니다.",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="결제 처리 중 오류가 발생했습니다.",
    )
