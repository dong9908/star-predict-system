from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from payment.models import PaymentStatus


class PaymentApproveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    partner_order_id: str = Field(
        min_length=1,
        max_length=100,
        alias="partnerOrderId",
    )
    pg_token: str = Field(min_length=1, max_length=255, alias="pgToken")


class PaymentOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    partner_order_id: str = Field(
        min_length=1,
        max_length=100,
        alias="partnerOrderId",
    )


class PaymentStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_id: int = Field(ge=1, alias="paymentId")
    partner_order_id: str = Field(alias="partnerOrderId")
    status: PaymentStatus


class PaymentRefundResponse(PaymentStatusResponse):
    cancelled_at: datetime = Field(alias="cancelledAt")
    has_fortune_access: bool = Field(alias="hasFortuneAccess")


class PaymentReadyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_id: int = Field(ge=1, alias="paymentId")
    partner_order_id: str = Field(alias="partnerOrderId")
    redirect_url: str = Field(alias="redirectUrl")
    pc_redirect_url: str = Field(alias="pcRedirectUrl")
    mobile_redirect_url: str | None = Field(default=None, alias="mobileRedirectUrl")
    app_redirect_url: str | None = Field(default=None, alias="appRedirectUrl")
    status: PaymentStatus


class PaymentApprovalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payment_id: int = Field(ge=1, alias="paymentId")
    partner_order_id: str = Field(alias="partnerOrderId")
    item_name: str = Field(alias="itemName")
    amount: int = Field(gt=0)
    status: PaymentStatus
    approved_at: datetime = Field(alias="approvedAt")
    has_fortune_access: bool = Field(alias="hasFortuneAccess")


class PaymentHistoryItem(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    payment_id: int = Field(alias="paymentId")
    partner_order_id: str = Field(alias="partnerOrderId")
    item_name: str = Field(alias="itemName")
    amount: int
    status: PaymentStatus
    approved_at: datetime | None = Field(alias="approvedAt")
    cancelled_at: datetime | None = Field(alias="cancelledAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PaymentAccessResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    has_fortune_access: bool = Field(alias="hasFortuneAccess")


class KakaoPayReadyResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tid: str = Field(min_length=1, max_length=100)
    next_redirect_app_url: HttpUrl | None = None
    next_redirect_mobile_url: HttpUrl | None = None
    next_redirect_pc_url: HttpUrl
    android_app_scheme: str | None = None
    ios_app_scheme: str | None = None
    created_at: datetime


class KakaoPayAmount(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int = Field(ge=0)
    tax_free: int = Field(default=0, ge=0)
    vat: int = Field(default=0, ge=0)
    point: int = Field(default=0, ge=0)
    discount: int = Field(default=0, ge=0)
    green_deposit: int = Field(default=0, ge=0)


class KakaoPayApprovalResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    aid: str = Field(min_length=1, max_length=100)
    tid: str = Field(min_length=1, max_length=100)
    cid: str
    partner_order_id: str
    partner_user_id: str
    payment_method_type: str
    amount: KakaoPayAmount
    item_name: str
    quantity: int = Field(ge=1)
    created_at: datetime
    approved_at: datetime


class KakaoPayCancellationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    aid: str
    tid: str
    cid: str
    status: str
    partner_order_id: str
    partner_user_id: str
    payment_method_type: str
    amount: KakaoPayAmount
    canceled_amount: KakaoPayAmount
    cancel_available_amount: KakaoPayAmount
    item_name: str
    quantity: int = Field(ge=1)
    approved_at: datetime | None = None
    canceled_at: datetime
