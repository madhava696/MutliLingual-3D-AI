"""
Session model.
session_id = public identifier (safe in URLs).
session_token = cryptographically random secret credential.
"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _generate_session_token() -> str:
    """Generate a cryptographically random session token."""
    return secrets.token_urlsafe(48)


def _default_expiry() -> datetime:
    """Default session expiry: 30 minutes from now."""
    return datetime.now(timezone.utc) + timedelta(minutes=30)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    session_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=_generate_session_token,
        index=True,
        comment="Cryptographically random secret — never treat session_id as auth",
    )
    language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en"
    )
    private_mode: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    context: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_default_expiry,
    )

    # Relationships
    reminders = relationship(
        "Reminder", back_populates="session", cascade="all, delete-orphan"
    )
    notes = relationship(
        "Note", back_populates="session", cascade="all, delete-orphan"
    )
    uploaded_files = relationship(
        "UploadedFile", back_populates="session", cascade="all, delete-orphan"
    )
    usage_logs = relationship("UsageLog", back_populates="session")

    def __repr__(self) -> str:
        return f"<Session id={self.id} lang={self.language} private={self.private_mode}>"
