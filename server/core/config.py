import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class FortuneAISettings:
    provider: str
    api_key: str
    model: str
    timeout_seconds: float
    max_retries: int


def get_fortune_ai_settings() -> FortuneAISettings:
    provider = os.getenv("FORTUNE_AI_PROVIDER", "groq").strip().lower()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("FORTUNE_AI_MODEL", "").strip()

    if provider != "groq":
        raise ValueError("지원하지 않는 운세 AI 공급자입니다.")
    if not api_key:
        raise ValueError("GROQ_API_KEY가 설정되지 않았습니다.")
    if not model:
        raise ValueError("FORTUNE_AI_MODEL이 설정되지 않았습니다.")

    try:
        timeout_seconds = float(os.getenv("FORTUNE_AI_TIMEOUT_SECONDS", "30"))
        max_retries = int(os.getenv("FORTUNE_AI_MAX_RETRIES", "1"))
    except ValueError as error:
        raise ValueError("운세 AI 숫자 설정값이 올바르지 않습니다.") from error

    if timeout_seconds <= 0:
        raise ValueError("FORTUNE_AI_TIMEOUT_SECONDS는 0보다 커야 합니다.")
    if not 0 <= max_retries <= 3:
        raise ValueError("FORTUNE_AI_MAX_RETRIES는 0부터 3 사이여야 합니다.")

    return FortuneAISettings(
        provider=provider,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
