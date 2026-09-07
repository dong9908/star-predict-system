from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class ConstellationModel(Base):
    __tablename__ = "constellations"

    constellation_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    name_ko: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True
    )

    name_en: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    mythology: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    difficulty: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    abbreviation: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True
    )