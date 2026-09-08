from datetime import datetime

from pydantic import BaseModel


class TitleStatusResponse(BaseModel):
    id: int
    name: str
    description: str | None
    acquired: bool
    acquiredAt: datetime | None = None
    selected: bool


class TitleListResponse(BaseModel):
    discoveredCount: int
    totalConstellations: int
    acquiredCount: int
    titles: list[TitleStatusResponse]


class TitleEvaluationResponse(BaseModel):
    awardedCount: int
    newTitles: list[TitleStatusResponse]


class TitleSelectionResponse(BaseModel):
    selectedTitle: TitleStatusResponse
