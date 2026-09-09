from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fortune.services.zodiac_service import calculate_zodiac
from models.constellation import ConstellationModel
from models.discovery import UserConstellationModel
from models.title import TitleModel, UserTitleModel


_CORE_DIFFICULTIES = ("1", "2", "3", "4")
_SERPENS_ABBREVIATIONS = frozenset({"SerH", "SerT"})
_OPHIUCHUS_ABBREVIATION = "Oph"


@dataclass(frozen=True)
class UserDiscoveryStats:
    user_id: int
    total_constellations: int
    discovered_count: int
    discovered_ids: frozenset[int]
    discovered_names: frozenset[str]
    discovered_abbreviations: frozenset[str]
    total_by_difficulty: dict[str, int]
    discovered_by_difficulty: dict[str, int]
    mythology_count: int
    discoveries_by_date: dict[date, int]
    longest_consecutive_days: int


@dataclass(frozen=True)
class UserTitleStatus:
    id: int
    name: str
    description: str | None
    level: int
    acquired: bool
    acquired_at: datetime | None
    selected: bool


def _normalize_difficulty(value: str | None) -> str:
    if value is None or not value.strip():
        return "UNSPECIFIED"
    return value.strip()


def _longest_consecutive_days(discovery_dates: set[date]) -> int:
    if not discovery_dates:
        return 0

    longest = 1
    current = 1
    ordered_dates = sorted(discovery_dates)

    for previous, current_date in zip(ordered_dates, ordered_dates[1:]):
        if current_date == previous + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1

    return longest


def build_user_discovery_stats(
    db: Session,
    user_id: int,
) -> UserDiscoveryStats:
    all_constellations = db.query(ConstellationModel).all()
    discovered_rows = (
        db.query(UserConstellationModel, ConstellationModel)
        .join(
            ConstellationModel,
            ConstellationModel.constellation_id
            == UserConstellationModel.constellation_id,
        )
        .filter(UserConstellationModel.user_id == user_id)
        .all()
    )

    total_by_difficulty = Counter(
        _normalize_difficulty(constellation.difficulty)
        for constellation in all_constellations
    )
    discovered_by_difficulty = Counter(
        _normalize_difficulty(constellation.difficulty)
        for _, constellation in discovered_rows
    )
    discoveries_by_date = Counter(
        discovery.discovered_at.date()
        for discovery, _ in discovered_rows
    )

    return UserDiscoveryStats(
        user_id=user_id,
        total_constellations=len(all_constellations),
        discovered_count=len(discovered_rows),
        discovered_ids=frozenset(
            constellation.constellation_id
            for _, constellation in discovered_rows
        ),
        discovered_names=frozenset(
            constellation.name_ko
            for _, constellation in discovered_rows
        ),
        discovered_abbreviations=frozenset(
            constellation.abbreviation
            for _, constellation in discovered_rows
        ),
        total_by_difficulty=dict(total_by_difficulty),
        discovered_by_difficulty=dict(discovered_by_difficulty),
        mythology_count=sum(
            1
            for _, constellation in discovered_rows
            if constellation.mythology and constellation.mythology.strip()
        ),
        discoveries_by_date=dict(discoveries_by_date),
        longest_consecutive_days=_longest_consecutive_days(
            set(discoveries_by_date),
        ),
    )


def _has_completed_difficulty(
    stats: UserDiscoveryStats,
    difficulty: str,
) -> bool:
    total = stats.total_by_difficulty.get(difficulty, 0)
    discovered = stats.discovered_by_difficulty.get(difficulty, 0)
    return total > 0 and discovered >= total


def get_qualified_title_ids(
    stats: UserDiscoveryStats,
    birth_date: date,
) -> frozenset[int]:
    """Return title IDs whose acquisition conditions are currently satisfied.

    This function only evaluates conditions. It does not insert or update rows in
    ``user_titles`` so callers can safely reuse it for previews and later award
    processing.
    """
    zodiac = calculate_zodiac(birth_date)
    same_day_maximum = max(stats.discoveries_by_date.values(), default=0)

    conditions = {
        1: stats.discovered_count >= 10,
        2: stats.discovered_count >= 25,
        3: stats.discovered_count >= 50,
        4: stats.discovered_count >= 75,
        5: (
            stats.total_constellations > 0
            and stats.discovered_count >= stats.total_constellations
        ),
        6: _SERPENS_ABBREVIATIONS.issubset(
            stats.discovered_abbreviations,
        ),
        7: _OPHIUCHUS_ABBREVIATION in stats.discovered_abbreviations,
        8: zodiac.name_ko in stats.discovered_names,
        9: _has_completed_difficulty(stats, "1"),
        10: _has_completed_difficulty(stats, "2"),
        11: _has_completed_difficulty(stats, "3"),
        12: stats.discovered_by_difficulty.get("4", 0) >= 10,
        13: _has_completed_difficulty(stats, "4"),
        14: all(
            stats.discovered_by_difficulty.get(difficulty, 0) >= 1
            for difficulty in _CORE_DIFFICULTIES
        ),
        15: stats.mythology_count >= 20,
        16: stats.longest_consecutive_days >= 7,
        17: same_day_maximum >= 3,
        121: stats.discovered_by_difficulty.get("관측불가", 0) >= 1,
    }

    return frozenset(
        title_id
        for title_id, is_qualified in conditions.items()
        if is_qualified
    )


def award_qualified_titles(
    db: Session,
    user_id: int,
    birth_date: date,
) -> list[TitleModel]:
    """Persist and return titles newly earned by a user.

    Only title IDs that both satisfy their condition and exist in ``titles`` are
    considered. Already-owned titles are excluded before insertion, while the
    database unique constraint remains the final duplicate safeguard.
    """
    stats = build_user_discovery_stats(db, user_id)
    qualified_ids = get_qualified_title_ids(stats, birth_date)
    if not qualified_ids:
        return []

    existing_title_ids = frozenset(
        title_id
        for (title_id,) in (
            db.query(UserTitleModel.title_id)
            .filter(
                UserTitleModel.user_id == user_id,
                UserTitleModel.title_id.in_(qualified_ids),
            )
            .all()
        )
    )
    new_title_ids = qualified_ids - existing_title_ids
    if not new_title_ids:
        return []

    new_titles = (
        db.query(TitleModel)
        .filter(TitleModel.id.in_(new_title_ids))
        .order_by(TitleModel.id)
        .all()
    )
    if not new_titles:
        return []

    db.add_all(
        UserTitleModel(user_id=user_id, title_id=title.id)
        for title in new_titles
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return new_titles


def list_user_title_statuses(
    db: Session,
    user_id: int,
) -> list[UserTitleStatus]:
    rows = (
        db.query(TitleModel, UserTitleModel)
        .outerjoin(
            UserTitleModel,
            and_(
                UserTitleModel.title_id == TitleModel.id,
                UserTitleModel.user_id == user_id,
            ),
        )
        .order_by(TitleModel.id)
        .all()
    )

    return [
        UserTitleStatus(
            id=title.id,
            name=title.name,
            description=title.description,
            level=title.level,
            acquired=user_title is not None,
            acquired_at=(
                user_title.acquired_at
                if user_title is not None
                else None
            ),
            selected=(
                user_title.is_selected
                if user_title is not None
                else False
            ),
        )
        for title, user_title in rows
    ]


def select_user_title(
    db: Session,
    user_id: int,
    title_id: int,
) -> TitleModel | None:
    owned_title = (
        db.query(UserTitleModel, TitleModel)
        .join(TitleModel, TitleModel.id == UserTitleModel.title_id)
        .filter(
            UserTitleModel.user_id == user_id,
            UserTitleModel.title_id == title_id,
        )
        .first()
    )
    if owned_title is None:
        return None

    user_title, title = owned_title
    try:
        db.query(UserTitleModel).filter(
            UserTitleModel.user_id == user_id,
            UserTitleModel.is_selected.is_(True),
        ).update(
            {UserTitleModel.is_selected: False},
            synchronize_session=False,
        )
        user_title.is_selected = True
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return title
