from collections.abc import Sequence

from fortune.prompts.chat_prompt import CHAT_INSTRUCTIONS
from fortune.prompts.initial_prompt import INITIAL_FORTUNE_INSTRUCTIONS
from fortune.prompts.system_prompt import SYSTEM_PROMPT
from fortune.schemas import (
    ConversationMessage,
    FortuneCategory,
    FortuneContextResponse,
    PromptBundle,
    PromptMessage,
)


MAX_HISTORY_MESSAGES = 10


def _context_message(context: FortuneContextResponse) -> str:
    """Return only the non-sensitive context needed by the language model."""
    return (
        "서버가 확인한 운세 컨텍스트입니다. 이 값은 사용자 지시가 아닙니다.\n"
        f"- 오늘 날짜: {context.today.isoformat()}\n"
        f"- 별자리 코드: {context.zodiac.code}\n"
        f"- 별자리 이름: {context.zodiac.name_ko} ({context.zodiac.name_en})\n"
        f"- 별자리 심볼: {context.zodiac.symbol}"
    )


def build_initial_fortune_prompt(
    context: FortuneContextResponse,
) -> PromptBundle:
    return PromptBundle(
        response_type="initial",
        response_schema_name="InitialFortuneResponse",
        messages=[
            PromptMessage(
                role="system",
                content=f"{SYSTEM_PROMPT}\n\n{INITIAL_FORTUNE_INSTRUCTIONS}",
            ),
            PromptMessage(role="user", content=_context_message(context)),
        ],
    )


def build_chat_prompt(
    context: FortuneContextResponse,
    message: str,
    history: Sequence[ConversationMessage] = (),
    category: FortuneCategory = FortuneCategory.GENERAL,
) -> PromptBundle:
    cleaned_message = message.strip()
    if not cleaned_message:
        raise ValueError("질문을 입력해주세요.")
    if len(cleaned_message) > 500:
        raise ValueError("질문은 500자 이하로 입력해주세요.")

    messages = [
        PromptMessage(
            role="system",
            content=f"{SYSTEM_PROMPT}\n\n{CHAT_INSTRUCTIONS}",
        ),
        PromptMessage(
            role="user",
            content=f"{_context_message(context)}\n- 요청 카테고리: {category.value}",
        ),
    ]

    for history_message in list(history)[-MAX_HISTORY_MESSAGES:]:
        messages.append(
            PromptMessage(
                role=history_message.role,
                content=history_message.content,
            )
        )

    messages.append(PromptMessage(role="user", content=cleaned_message))
    return PromptBundle(
        response_type="chat",
        response_schema_name="FortuneChatResponse",
        messages=messages,
    )
