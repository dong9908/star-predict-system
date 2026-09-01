from datetime import date
from sqlalchemy import BigInteger, String, Date
from sqlalchemy.orm import Mapped, mapped_column
from database.connection import Base

class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)