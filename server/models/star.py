from sqlalchemy import Integer, String, Double
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class StarModel(Base):
    __tablename__ = "star"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    proper: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    proper_ko: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    ra: Mapped[float | None] = mapped_column(
        Double,
        nullable=True
    )

    dec_val: Mapped[float | None] = mapped_column(
        Double,
        nullable=True
    )

    mag: Mapped[float | None] = mapped_column(
        Double,
        nullable=True
    )

    con: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True
    )