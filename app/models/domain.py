import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # Null for OAuth only
    auth_provider: Mapped[str] = mapped_column(String, nullable=False, default="local")
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")

    # Security & Rate Limits
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    password_changes_today: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_password_change: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Store profiles, backgrounds, URLs in this JSONB column
    profile_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    otp_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
