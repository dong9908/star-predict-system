from sqlalchemy import func
from sqlalchemy.orm import Session

from fortune.exceptions import FortuneConversationNotFoundError
from fortune.models import FortuneConversationModel, FortuneMessageModel
from fortune.schemas import ConversationMessage, FortuneCategory


DEFAULT_CONVERSATION_TITLE = "새 운세 상담"
MAX_CONVERSATION_TITLE_LENGTH = 100
MAX_MESSAGE_CONTENT_LENGTH = 65_535


def _normalize_title(title: str | None) -> str:
    normalized = title.strip() if title else DEFAULT_CONVERSATION_TITLE
    return normalized[:MAX_CONVERSATION_TITLE_LENGTH] or DEFAULT_CONVERSATION_TITLE


def create_conversation(
    db: Session,
    user_id: int,
    title: str | None = None,
) -> FortuneConversationModel:
    conversation = FortuneConversationModel(
        user_id=user_id,
        title=_normalize_title(title),
    )
    db.add(conversation)
    db.flush()
    return conversation


def get_user_conversation(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> FortuneConversationModel:
    conversation = (
        db.query(FortuneConversationModel)
        .filter(
            FortuneConversationModel.conversation_id == conversation_id,
            FortuneConversationModel.user_id == user_id,
        )
        .first()
    )

    if conversation is None:
        raise FortuneConversationNotFoundError(
            "대화방을 찾을 수 없습니다.",
        )

    return conversation


def get_or_create_conversation(
    db: Session,
    user_id: int,
    conversation_id: int | None = None,
    title: str | None = None,
) -> FortuneConversationModel:
    if conversation_id is None:
        return create_conversation(db, user_id, title)

    return get_user_conversation(db, user_id, conversation_id)


def _normalize_message_content(content: str) -> str:
    normalized = content.strip()
    if not normalized:
        raise ValueError("메시지 내용은 비어 있을 수 없습니다.")
    if len(normalized) > MAX_MESSAGE_CONTENT_LENGTH:
        raise ValueError("메시지 내용이 저장 가능한 길이를 초과했습니다.")
    return normalized


def _category_value(category: FortuneCategory | str) -> str:
    if isinstance(category, FortuneCategory):
        return category.value
    return FortuneCategory(category).value


def save_message(
    db: Session,
    conversation: FortuneConversationModel,
    role: str,
    content: str,
    category: FortuneCategory | str = FortuneCategory.GENERAL,
) -> FortuneMessageModel:
    if role not in {"user", "assistant"}:
        raise ValueError("메시지 역할은 user 또는 assistant여야 합니다.")

    message = FortuneMessageModel(
        conversation=conversation,
        role=role,
        content=_normalize_message_content(content),
        category=_category_value(category),
    )
    conversation.updated_at = func.current_timestamp()
    db.add(message)
    db.flush()
    return message


def save_user_message(
    db: Session,
    conversation: FortuneConversationModel,
    content: str,
    category: FortuneCategory | str = FortuneCategory.GENERAL,
) -> FortuneMessageModel:
    return save_message(db, conversation, "user", content, category)


def save_assistant_message(
    db: Session,
    conversation: FortuneConversationModel,
    content: str,
    category: FortuneCategory | str = FortuneCategory.GENERAL,
) -> FortuneMessageModel:
    return save_message(db, conversation, "assistant", content, category)


def list_user_conversations(
    db: Session,
    user_id: int,
) -> list[FortuneConversationModel]:
    return (
        db.query(FortuneConversationModel)
        .filter(FortuneConversationModel.user_id == user_id)
        .order_by(FortuneConversationModel.updated_at.desc())
        .all()
    )


def list_conversation_messages(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> tuple[FortuneConversationModel, list[FortuneMessageModel]]:
    conversation = get_user_conversation(db, user_id, conversation_id)
    messages = (
        db.query(FortuneMessageModel)
        .filter(FortuneMessageModel.conversation_id == conversation_id)
        .order_by(
            FortuneMessageModel.created_at.asc(),
            FortuneMessageModel.message_id.asc(),
        )
        .all()
    )
    return conversation, messages


def get_recent_conversation_history(
    db: Session,
    conversation_id: int,
    limit: int = 10,
) -> list[ConversationMessage]:
    if limit < 1:
        return []

    messages = (
        db.query(FortuneMessageModel)
        .filter(FortuneMessageModel.conversation_id == conversation_id)
        .order_by(
            FortuneMessageModel.created_at.desc(),
            FortuneMessageModel.message_id.desc(),
        )
        .limit(limit)
        .all()
    )
    messages.reverse()
    return [
        ConversationMessage(role=message.role, content=message.content)
        for message in messages
    ]


def delete_user_conversation(
    db: Session,
    user_id: int,
    conversation_id: int,
) -> None:
    conversation = get_user_conversation(db, user_id, conversation_id)
    db.delete(conversation)
    db.flush()
