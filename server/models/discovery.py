from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base
from models.constellation import ConstellationModel
from models.member import UserModel


class UserConstellationModel(Base):
    __tablename__ = "user_constellations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "constellation_id",
            name="uq_user_constellation",
        ),
        Index("idx_user_constellations_user_id", "user_id"),
        Index("idx_user_constellations_constellation_id", "constellation_id"),
    )

    user_constellation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    constellation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "constellations.constellation_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    image_url: Mapped[str | None] = mapped_column(String(500))
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    user: Mapped[UserModel] = relationship()
    constellation: Mapped[ConstellationModel] = relationship()
