from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from database.connection import get_db
from fortune.exceptions import (
    FortuneAIAuthenticationError,
    FortuneAIConfigurationError,
    FortuneAIRateLimitError,
    FortuneAIResponseError,
    FortuneAITimeoutError,
    FortuneAIUnavailableError,
    FortuneConversationNotFoundError,
)
from fortune.schemas import (
    FortuneChatInput,
    FortuneChatResponse,
    FortuneConversationDetail,
    FortuneConversationSummary,
    FortuneContextResponse,
    FortuneMessageResponse,
    InitialFortuneResponse,
)
from fortune.services.ai_service import (
    generate_chat_response,
    generate_initial_fortune,
)
from fortune.services.context_service import build_fortune_context
from fortune.services.conversation_service import (
    delete_user_conversation,
    get_or_create_conversation,
    get_recent_conversation_history,
    list_conversation_messages,
    list_user_conversations,
    save_assistant_message,
    save_user_message,
)
from models.member import UserModel


fortune_router = APIRouter()


def require_fortune_access(
    user: UserModel = Depends(get_current_user),
) -> UserModel:
    if not user.has_fortune_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="결제 후 이용할 수 있는 운세 서비스입니다.",
        )
    return user


@fortune_router.get("/context", response_model=FortuneContextResponse)
async def get_fortune_context(
    user: UserModel = Depends(get_current_user),
) -> FortuneContextResponse:
    return build_fortune_context(user)


@fortune_router.post("/initial", response_model=InitialFortuneResponse)
async def create_initial_fortune(
    user: UserModel = Depends(require_fortune_access),
) -> InitialFortuneResponse:
    try:
        return await generate_initial_fortune(build_fortune_context(user))
    except Exception as error:
        raise _to_http_exception(error) from error


@fortune_router.post("/chat", response_model=FortuneChatResponse)
async def create_fortune_chat_response(
    chat_input: FortuneChatInput,
    user: UserModel = Depends(require_fortune_access),
    db: Session = Depends(get_db),
) -> FortuneChatResponse:
    try:
        conversation = get_or_create_conversation(
            db,
            user.user_id,
            chat_input.conversation_id,
            chat_input.message,
        )
        stored_history = get_recent_conversation_history(
            db,
            conversation.conversation_id,
        )
        effective_history = stored_history or chat_input.history
        ai_input = chat_input.model_copy(update={"history": effective_history})

        save_user_message(
            db,
            conversation,
            chat_input.message,
            chat_input.category,
        )
        ai_response = await generate_chat_response(
            build_fortune_context(user),
            ai_input,
        )
        save_assistant_message(
            db,
            conversation,
            ai_response.answer,
            ai_response.category,
        )
        db.commit()
        return FortuneChatResponse(
            conversation_id=conversation.conversation_id,
            **ai_response.model_dump(),
        )
    except FortuneConversationNotFoundError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화방을 찾을 수 없습니다.",
        ) from error
    except Exception as error:
        db.rollback()
        raise _to_http_exception(error) from error


@fortune_router.get(
    "/conversations",
    response_model=list[FortuneConversationSummary],
)
async def get_fortune_conversations(
    user: UserModel = Depends(require_fortune_access),
    db: Session = Depends(get_db),
) -> list[FortuneConversationSummary]:
    conversations = list_user_conversations(db, user.user_id)
    return [
        FortuneConversationSummary.model_validate(conversation)
        for conversation in conversations
    ]


@fortune_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=FortuneConversationDetail,
)
async def get_fortune_conversation_messages(
    conversation_id: int,
    user: UserModel = Depends(require_fortune_access),
    db: Session = Depends(get_db),
) -> FortuneConversationDetail:
    try:
        conversation, messages = list_conversation_messages(
            db,
            user.user_id,
            conversation_id,
        )
    except FortuneConversationNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화방을 찾을 수 없습니다.",
        ) from error

    return FortuneConversationDetail(
        conversation_id=conversation.conversation_id,
        title=conversation.title,
        messages=[
            FortuneMessageResponse.model_validate(message)
            for message in messages
        ],
    )


@fortune_router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_fortune_conversation(
    conversation_id: int,
    user: UserModel = Depends(require_fortune_access),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_user_conversation(db, user.user_id, conversation_id)
        db.commit()
    except FortuneConversationNotFoundError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화방을 찾을 수 없습니다.",
        ) from error
    except Exception:
        db.rollback()
        raise

    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
