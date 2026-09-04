import asyncio
import json
import socket
from collections.abc import Mapping
from typing import TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from payment.config import KakaoPaySettings, get_kakaopay_settings
from payment.exceptions import (
    PaymentApprovalError,
    PaymentAuthenticationError,
    PaymentCancellationError,
    PaymentConfigurationError,
    PaymentProviderResponseError,
    PaymentProviderUnavailableError,
    PaymentReadyError,
)
from payment.schemas import (
    KakaoPayApprovalResponse,
    KakaoPayCancellationResponse,
    KakaoPayReadyResponse,
)


KAKAOPAY_API_BASE_URL = "https://open-api.kakaopay.com/online/v1/payment"
KAKAOPAY_READY_URL = f"{KAKAOPAY_API_BASE_URL}/ready"
KAKAOPAY_APPROVE_URL = f"{KAKAOPAY_API_BASE_URL}/approve"
KAKAOPAY_CANCEL_URL = f"{KAKAOPAY_API_BASE_URL}/cancel"

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


def _append_query_parameter(url: str, name: str, value: str) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query[name] = value
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment),
    )


class KakaoPayProvider:
    def __init__(self, settings: KakaoPaySettings | None = None) -> None:
        try:
            self.settings = settings or get_kakaopay_settings()
        except ValueError as error:
            raise PaymentConfigurationError(str(error)) from error

    async def ready(
        self,
        partner_order_id: str,
        partner_user_id: str,
    ) -> KakaoPayReadyResponse:
        payload = {
            "cid": self.settings.cid,
            "partner_order_id": partner_order_id,
            "partner_user_id": partner_user_id,
            "item_name": self.settings.product_name,
            "quantity": 1,
            "total_amount": self.settings.product_price,
            "tax_free_amount": 0,
            "approval_url": _append_query_parameter(
                self.settings.approval_url,
                "partnerOrderId",
                partner_order_id,
            ),
            "cancel_url": _append_query_parameter(
                self.settings.cancel_url,
                "partnerOrderId",
                partner_order_id,
            ),
            "fail_url": _append_query_parameter(
                self.settings.fail_url,
                "partnerOrderId",
                partner_order_id,
            ),
        }
        return await self._post(
            KAKAOPAY_READY_URL,
            payload,
            KakaoPayReadyResponse,
            PaymentReadyError,
        )

    async def approve(
        self,
        tid: str,
        partner_order_id: str,
        partner_user_id: str,
        pg_token: str,
    ) -> KakaoPayApprovalResponse:
        payload = {
            "cid": self.settings.cid,
            "tid": tid,
            "partner_order_id": partner_order_id,
            "partner_user_id": partner_user_id,
            "pg_token": pg_token,
        }
        return await self._post(
            KAKAOPAY_APPROVE_URL,
            payload,
            KakaoPayApprovalResponse,
            PaymentApprovalError,
        )

    async def cancel(
        self,
        tid: str,
        cancel_amount: int,
        cancel_tax_free_amount: int = 0,
    ) -> KakaoPayCancellationResponse:
        payload = {
            "cid": self.settings.cid,
            "tid": tid,
            "cancel_amount": cancel_amount,
            "cancel_tax_free_amount": cancel_tax_free_amount,
        }
        return await self._post(
            KAKAOPAY_CANCEL_URL,
            payload,
            KakaoPayCancellationResponse,
            PaymentCancellationError,
        )

    async def _post(
        self,
        url: str,
        payload: Mapping[str, object],
        response_model: type[ResponseModel],
        operation_error: type[Exception],
    ) -> ResponseModel:
        return await asyncio.to_thread(
            self._post_sync,
            url,
            payload,
            response_model,
            operation_error,
        )

    def _post_sync(
        self,
        url: str,
        payload: Mapping[str, object],
        response_model: type[ResponseModel],
        operation_error: type[Exception],
    ) -> ResponseModel:
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": (
                    f"{self.settings.authorization_scheme} "
                    f"{self.settings.secret_key}"
                ),
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "ASTRA-Payment-Server/1.0",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self.settings.timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            self._raise_http_error(error, operation_error)
        except (TimeoutError, socket.timeout) as error:
            raise PaymentProviderUnavailableError(
                "카카오페이 요청 시간이 초과되었습니다.",
            ) from error
        except URLError as error:
            raise PaymentProviderUnavailableError(
                "카카오페이 서비스에 연결할 수 없습니다.",
            ) from error

        try:
            return response_model.model_validate_json(response_body)
        except (ValidationError, ValueError) as error:
            raise PaymentProviderResponseError(
                "카카오페이 응답 형식이 올바르지 않습니다.",
            ) from error

    @staticmethod
    def _raise_http_error(
        error: HTTPError,
        operation_error: type[Exception],
    ) -> None:
        message = "카카오페이 요청에 실패했습니다."
        try:
            body = json.loads(error.read().decode("utf-8"))
            provider_message = body.get("error_message") or body.get("message")
            if isinstance(provider_message, str) and provider_message.strip():
                message = provider_message.strip()
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            pass

        if error.code in {401, 403}:
            raise PaymentAuthenticationError(
                "카카오페이 인증에 실패했습니다.",
            ) from error
        if error.code == 408 or error.code >= 500:
            raise PaymentProviderUnavailableError(message) from error
        raise operation_error(message) from error
