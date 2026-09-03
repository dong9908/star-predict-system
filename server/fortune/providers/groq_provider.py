import asyncio
import json
import socket
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from fortune.config import FortuneAISettings, get_fortune_ai_settings
from fortune.exceptions import (
    FortuneAIAuthenticationError,
    FortuneAIConfigurationError,
    FortuneAIRateLimitError,
    FortuneAIResponseError,
    FortuneAITimeoutError,
    FortuneAIUnavailableError,
)
from fortune.schemas import PromptBundle


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


class FortuneAIProvider(Protocol):
    async def generate(
        self,
        prompt: PromptBundle,
        response_model: type[BaseModel],
    ) -> str:
        ...


class GroqFortuneProvider:
    def __init__(self, settings: FortuneAISettings | None = None) -> None:
        try:
            self.settings = settings or get_fortune_ai_settings()
        except ValueError as error:
            raise FortuneAIConfigurationError(str(error)) from error

    async def generate(
        self,
        prompt: PromptBundle,
        response_model: type[BaseModel],
    ) -> str:
        return await asyncio.to_thread(
            self._generate_sync,
            prompt,
            response_model,
        )

    def _generate_sync(
        self,
        prompt: PromptBundle,
        response_model: type[BaseModel],
    ) -> str:
        payload = {
            "model": self.settings.model,
            "messages": [
                message.model_dump(mode="json")
                for message in prompt.messages
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": prompt.response_schema_name,
                    "strict": True,
                    "schema": response_model.model_json_schema(by_alias=True),
                },
            },
            "max_completion_tokens": 1800,
        }
        request = Request(
            GROQ_CHAT_COMPLETIONS_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ASTRA-Fortune-Server/1.0",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            self._raise_http_error(error)
        except (TimeoutError, socket.timeout) as error:
            raise FortuneAITimeoutError("Groq 요청 시간이 초과되었습니다.") from error
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise FortuneAITimeoutError("Groq 요청 시간이 초과되었습니다.") from error
            raise FortuneAIUnavailableError("Groq 서비스에 연결할 수 없습니다.") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FortuneAIResponseError("Groq 응답을 해석할 수 없습니다.") from error

        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise FortuneAIResponseError("Groq 응답에 메시지가 없습니다.") from error

        if not isinstance(content, str) or not content.strip():
            raise FortuneAIResponseError("Groq가 빈 응답을 반환했습니다.")
        return content

    @staticmethod
    def _raise_http_error(error: HTTPError) -> None:
        if error.code in (401, 403):
            raise FortuneAIAuthenticationError("Groq 인증에 실패했습니다.") from error
        if error.code == 429:
            raise FortuneAIRateLimitError("Groq 무료 사용 한도를 초과했습니다.") from error
        if 500 <= error.code < 600:
            raise FortuneAIUnavailableError("Groq 서비스가 일시적으로 불안정합니다.") from error
        if error.code == 408:
            raise FortuneAITimeoutError("Groq 요청 시간이 초과되었습니다.") from error
        raise FortuneAIResponseError("Groq 요청 형식 또는 모델 설정이 올바르지 않습니다.") from error
