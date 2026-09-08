from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.security import get_current_user
from database.connection import get_db
from models.member import UserModel
from schemas.title import (
    TitleEvaluationResponse,
    TitleListResponse,
    TitleSelectionResponse,
    TitleStatusResponse,
)
from services.title_service import (
    award_qualified_titles,
    build_user_discovery_stats,
    list_user_title_statuses,
    select_user_title,
)


title_router = APIRouter()


def _to_response(status) -> TitleStatusResponse:
    return TitleStatusResponse(
        id=status.id,
        name=status.name,
        description=status.description,
        acquired=status.acquired,
        acquiredAt=status.acquired_at,
        selected=status.selected,
    )


@title_router.get("/me", response_model=TitleListResponse)
def get_my_titles(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TitleListResponse:
    stats = build_user_discovery_stats(db, user.user_id)
    statuses = list_user_title_statuses(db, user.user_id)
    return TitleListResponse(
        discoveredCount=stats.discovered_count,
        totalConstellations=stats.total_constellations,
        acquiredCount=sum(status.acquired for status in statuses),
        titles=[_to_response(status) for status in statuses],
    )


@title_router.post("/evaluate", response_model=TitleEvaluationResponse)
def evaluate_my_titles(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TitleEvaluationResponse:
    awarded_titles = award_qualified_titles(
        db=db,
        user_id=user.user_id,
        birth_date=user.birth_date,
    )
    awarded_ids = {title.id for title in awarded_titles}
    newly_awarded = [
        status
        for status in list_user_title_statuses(db, user.user_id)
        if status.id in awarded_ids
    ]

    return TitleEvaluationResponse(
        awardedCount=len(newly_awarded),
        newTitles=[_to_response(status) for status in newly_awarded],
    )


@title_router.put(
    "/me/selected/{title_id}",
    response_model=TitleSelectionResponse,
)
def update_my_selected_title(
    title_id: int,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TitleSelectionResponse:
    selected_title = select_user_title(db, user.user_id, title_id)
    if selected_title is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="획득한 칭호만 대표 칭호로 선택할 수 있습니다.",
        )

    selected_status = next(
        item
        for item in list_user_title_statuses(db, user.user_id)
        if item.id == selected_title.id
    )
    return TitleSelectionResponse(
        selectedTitle=_to_response(selected_status),
    )
