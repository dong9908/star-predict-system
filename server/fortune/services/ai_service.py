import asyncio
from json import JSONDecodeError
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from fortune.config import get_fortune_ai_settings
from fortune.exceptions import (
    FortuneAIAuthenticationError,
    FortuneAIConfigurationError,
    FortuneAIError,
    FortuneAIRateLimitError,
    FortuneAIResponseError,
    FortuneAITimeoutError,
    FortuneAIUnavailableError,
)
from fortune.providers.groq_provider import FortuneAIProvider, GroqFortuneProvider
from fortune.schemas import (
    FortuneChatInput,
    FortuneAIChatResponse,
    FortuneContextResponse,
    InitialFortuneResponse,
    PromptBundle,
)
from fortune.services.prompt_service import (
    build_chat_prompt,
    build_initial_fortune_prompt,
)


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)
RETRYABLE_ERRORS = (
    FortuneAIRateLimitError,
    FortuneAITimeoutError,
    FortuneAIUnavailableError,
    FortuneAIResponseError,
)


async def _generate_validated_response(
    prompt: PromptBundle,
    response_model: type[ResponseModel],
    provider: FortuneAIProvider | None = None,
    max_retries: int | None = None,
) -> ResponseModel:
    if provider is None:
        try:
            settings = get_fortune_ai_settings()
        except ValueError as error:
            raise FortuneAIConfigurationError(str(error)) from error
        active_provider = GroqFortuneProvider(settings)
        retry_limit = settings.max_retries if max_retries is None else max_retries
    else:
        active_provider = provider
        retry_limit = 1 if max_retries is None else max_retries

    for attempt in range(retry_limit + 1):
        try:
            raw_response = await active_provider.generate(prompt, response_model)
            return response_model.model_validate_json(raw_response)
        except (ValidationError, JSONDecodeError) as error:
            current_error: FortuneAIError = FortuneAIResponseError(
                "AI 응답이 요구한 JSON 형식과 일치하지 않습니다."
            )
            current_error.__cause__ = error
        except (FortuneAIAuthenticationError, FortuneAIConfigurationError):
            raise
        except RETRYABLE_ERRORS as error:
            current_error = error

        if attempt >= retry_limit:
            raise current_error
        await asyncio.sleep(0.25 * (attempt + 1))

    raise FortuneAIResponseError("운세 응답 생성에 실패했습니다.")


async def generate_initial_fortune(
    context: FortuneContextResponse,
    provider: FortuneAIProvider | None = None,
    max_retries: int | None = None,
) -> InitialFortuneResponse:
    return await _generate_validated_response(
        build_initial_fortune_prompt(context),
        InitialFortuneResponse,
        provider,
        max_retries,
    )


async def generate_chat_response(
    context: FortuneContextResponse,
    chat_input: FortuneChatInput,
    provider: FortuneAIProvider | None = None,
    max_retries: int | None = None,
) -> FortuneAIChatResponse:
    prompt = build_chat_prompt(
        context=context,
        message=chat_input.message,
        history=chat_input.history,
        category=chat_input.category,
    )
    return await _generate_validated_response(
        prompt,
        FortuneAIChatResponse,
        provider,
        max_retries,
    )
