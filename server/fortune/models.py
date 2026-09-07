from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base
from models.member import UserModel


class FortuneDailyResultModel(Base):
    __tablename__ = "fortune_daily_results"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "fortune_date",
            name="uq_fortune_daily_user_date",
        ),
        Index("idx_fortune_daily_user_id", "user_id"),
        Index("idx_fortune_daily_date", "fortune_date"),
    )

    fortune_result_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    fortune_date: Mapped[date] = mapped_column(Date, nullable=False)
    zodiac_code: Mapped[str] = mapped_column(String(20), nullable=False)
    result_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped[UserModel] = relationship()


class FortuneConversationModel(Base):
    __tablename__ = "fortune_conversations"
    __table_args__ = (
        Index("idx_fortune_conversations_user_id", "user_id"),
        Index("idx_fortune_conversations_updated_at", "updated_at"),
    )

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="새 운세 상담",
        server_default="새 운세 상담",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped[UserModel] = relationship()
    messages: Mapped[list["FortuneMessageModel"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="FortuneMessageModel.created_at",
    )


class FortuneMessageModel(Base):
    __tablename__ = "fortune_messages"
    __table_args__ = (
        Index("idx_fortune_messages_conversation_id", "conversation_id"),
        Index("idx_fortune_messages_created_at", "created_at"),
    )

    message_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "fortune_conversations.conversation_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="general",
        server_default="general",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    conversation: Mapped[FortuneConversationModel] = relationship(
        back_populates="messages",
    )
