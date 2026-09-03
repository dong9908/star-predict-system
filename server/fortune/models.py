from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base
from models.member import UserModel


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
