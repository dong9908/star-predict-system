from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class UserConstellationModel(Base):
    __tablename__ = "user_constellations"

    user_constellation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    constellation_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )