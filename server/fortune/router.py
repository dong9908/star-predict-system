from fastapi import APIRouter, Depends, HTTPException, status

from core.security import get_current_user
from fortune.exceptions import (
    FortuneAIAuthenticationError,
    FortuneAIConfigurationError,
    FortuneAIRateLimitError,
    FortuneAIResponseError,
    FortuneAITimeoutError,
    FortuneAIUnavailableError,
)
from fortune.schemas import (
    FortuneChatInput,
    FortuneChatResponse,
    FortuneContextResponse,
    InitialFortuneResponse,
)
from fortune.services.ai_service import (
    generate_chat_response,
    generate_initial_fortune,
)
from fortune.services.context_service import build_fortune_context
from models.member import UserModel


fortune_router = APIRouter()


@fortune_router.get("/context", response_model=FortuneContextResponse)
async def get_fortune_context(
    user: UserModel = Depends(get_current_user),
) -> FortuneContextResponse:
    return build_fortune_context(user)


@fortune_router.post("/initial", response_model=InitialFortuneResponse)
async def create_initial_fortune(
    user: UserModel = Depends(get_current_user),
) -> InitialFortuneResponse:
    try:
        return await generate_initial_fortune(build_fortune_context(user))
    except Exception as error:
        raise _to_http_exception(error) from error


@fortune_router.post("/chat", response_model=FortuneChatResponse)
async def create_fortune_chat_response(
    chat_input: FortuneChatInput,
    user: UserModel = Depends(get_current_user),
) -> FortuneChatResponse:
    try:
        return await generate_chat_response(
            build_fortune_context(user),
            chat_input,
        )
    except Exception as error:
        raise _to_http_exception(error) from error


def _to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, FortuneAITimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="운세 AI 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
        )
    if isinstance(error, FortuneAIResponseError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="운세 AI 응답을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.",
        )
    if isinstance(error, FortuneAIRateLimitError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="무료 운세 AI 사용량이 많습니다. 잠시 후 다시 시도해주세요.",
        )
    if isinstance(
        error,
        (
            FortuneAIAuthenticationError,
            FortuneAIConfigurationError,
            FortuneAIUnavailableError,
        ),
    ):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="운세 AI 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="운세 처리 중 오류가 발생했습니다.",
    )
