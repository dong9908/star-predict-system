from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ZodiacInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    code: str
    name_ko: str = Field(alias="nameKo")
    name_en: str = Field(alias="nameEn")
    symbol: str


class FortuneContextResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_id: int = Field(alias="userId")
    birth_date: date = Field(alias="birthDate")
    today: date
    zodiac: ZodiacInfo


class FortuneCategory(str, Enum):
    GENERAL = "general"
    LOVE = "love"
    WEALTH = "wealth"
    HEALTH = "health"
    CAREER = "career"
    RELATIONSHIP = "relationship"


class ConversationMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class FortuneChatInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=500)
    category: FortuneCategory = FortuneCategory.GENERAL
    history: list[ConversationMessage] = Field(default_factory=list, max_length=10)

    @field_validator("message", mode="before")
    @classmethod
    def reject_blank_message(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("질문을 입력해주세요.")
        return value


class PromptMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class PromptBundle(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    messages: list[PromptMessage] = Field(min_length=2)
    response_type: Literal["initial", "chat"] = Field(serialization_alias="responseType")
    response_schema_name: str = Field(serialization_alias="responseSchemaName")


class FortuneCategorySummary(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: FortuneCategory
    label: str = Field(min_length=1, max_length=20)
    score: int = Field(ge=1, le=5)
    summary: str = Field(min_length=1, max_length=500)


class InitialFortuneResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    greeting: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    fortune_score: int = Field(ge=0, le=100, alias="fortuneScore")
    keywords: list[str] = Field(min_length=1, max_length=5)
    category_summaries: list[FortuneCategorySummary] = Field(
        min_length=5,
        max_length=5,
        alias="categorySummaries",
    )
    suggested_questions: list[str] = Field(
        min_length=2,
        max_length=4,
        alias="suggestedQuestions",
    )
    disclaimer: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_categories(self) -> "InitialFortuneResponse":
        expected = {
            FortuneCategory.LOVE,
            FortuneCategory.WEALTH,
            FortuneCategory.HEALTH,
            FortuneCategory.CAREER,
            FortuneCategory.RELATIONSHIP,
        }
        actual = {item.category for item in self.category_summaries}
        if actual != expected or len(actual) != len(self.category_summaries):
            raise ValueError("다섯 운세 카테고리가 중복 없이 모두 필요합니다.")
        return self


class FortuneChatResponse(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )

    answer: str = Field(min_length=1, max_length=2000)
    category: FortuneCategory
    suggested_questions: list[str] = Field(
        min_length=1,
        max_length=3,
        alias="suggestedQuestions",
    )
    disclaimer: str = Field(min_length=1, max_length=300)
