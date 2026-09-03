import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class KakaoPaySettings:
    cid: str
    secret_key: str = field(repr=False)
    approval_url: str
    cancel_url: str
    fail_url: str
    product_name: str
    product_price: int
    timeout_seconds: float

    @property
    def authorization_scheme(self) -> str:
        return "DEV_SECRET_KEY" if self.secret_key.startswith("DEV") else "SECRET_KEY"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name}가 설정되지 않았습니다.")
    return value


def _validate_http_url(name: str, value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{name}는 올바른 HTTP(S) URL이어야 합니다.")
    return value


def get_kakaopay_settings() -> KakaoPaySettings:
    cid = _required_env("KAKAOPAY_CID")
    secret_key = _required_env("KAKAOPAY_SECRET_KEY")
    approval_url = _validate_http_url(
        "KAKAOPAY_APPROVAL_URL",
        _required_env("KAKAOPAY_APPROVAL_URL"),
    )
    cancel_url = _validate_http_url(
        "KAKAOPAY_CANCEL_URL",
        _required_env("KAKAOPAY_CANCEL_URL"),
    )
    fail_url = _validate_http_url(
        "KAKAOPAY_FAIL_URL",
        _required_env("KAKAOPAY_FAIL_URL"),
    )
    product_name = _required_env("FORTUNE_PRODUCT_NAME")

    try:
        product_price = int(_required_env("FORTUNE_PRODUCT_PRICE"))
    except ValueError as error:
        raise ValueError("FORTUNE_PRODUCT_PRICE는 정수여야 합니다.") from error
    if product_price <= 0:
        raise ValueError("FORTUNE_PRODUCT_PRICE는 0보다 커야 합니다.")

    if cid == "TC0ONETIME" and not secret_key.startswith("DEV"):
        raise ValueError("테스트 CID에는 Secret Key(dev)를 사용해야 합니다.")

    try:
        timeout_seconds = float(os.getenv("KAKAOPAY_TIMEOUT_SECONDS", "15"))
    except ValueError as error:
        raise ValueError("KAKAOPAY_TIMEOUT_SECONDS는 숫자여야 합니다.") from error
    if timeout_seconds <= 0:
        raise ValueError("KAKAOPAY_TIMEOUT_SECONDS는 0보다 커야 합니다.")

    return KakaoPaySettings(
        cid=cid,
        secret_key=secret_key,
        approval_url=approval_url,
        cancel_url=cancel_url,
        fail_url=fail_url,
        product_name=product_name,
        product_price=product_price,
        timeout_seconds=timeout_seconds,
    )
