"""
Reminder model.
Status includes 'notified' for scheduler-delivered reminders.
Index on remind_at WHERE status='pending' for efficient scheduler polling.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    remind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending | notified | completed | cancelled",
    )
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session = relationship("Session", back_populates="reminders")

    # Indexes for scheduler polling
    __table_args__ = (
        Index("idx_reminders_session_status", "session_id", "status"),
        Index(
            "idx_reminders_due",
            "remind_at",
            postgresql_where=text("status = 'pending'"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Reminder id={self.id} title={self.title!r} status={self.status}>"
