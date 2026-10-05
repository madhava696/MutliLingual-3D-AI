"""
Reminder service — CRUD operations for reminders.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import Reminder


async def create_reminder(
    db: AsyncSession,
    session_id: uuid.UUID,
    title: str,
    remind_at: datetime,
    description: str | None = None,
    language: str = "en",
) -> Reminder:
    """Create a new reminder."""
    reminder = Reminder(
        session_id=session_id,
        title=title,
        description=description,
        remind_at=remind_at,
        language=language,
        status="pending",
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def get_reminders_by_session(
    db: AsyncSession, session_id: uuid.UUID
) -> list[Reminder]:
    """List all reminders for a session."""
    result = await db.execute(
        select(Reminder)
        .where(Reminder.session_id == session_id)
        .order_by(Reminder.remind_at)
    )
    return list(result.scalars().all())


async def get_reminder_by_id(
    db: AsyncSession, reminder_id: uuid.UUID
) -> Reminder | None:
    """Get a single reminder by ID."""
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id)
    )
    return result.scalar_one_or_none()


async def update_reminder(
    db: AsyncSession,
    reminder: Reminder,
    status: str | None = None,
    remind_at: datetime | None = None,
) -> Reminder:
    """Update a reminder's status or scheduled time."""
    if status is not None:
        reminder.status = status
    if remind_at is not None:
        reminder.remind_at = remind_at
    reminder.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return reminder


async def delete_reminder(db: AsyncSession, reminder: Reminder) -> None:
    """Delete a reminder."""
    await db.delete(reminder)
    await db.flush()


async def get_due_reminders(db: AsyncSession) -> list[Reminder]:
    """Get all pending reminders that are now due. Used by the scheduler."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Reminder)
        .where(Reminder.status == "pending", Reminder.remind_at <= now)
        .order_by(Reminder.remind_at)
    )
    return list(result.scalars().all())


async def mark_reminders_notified(
    db: AsyncSession, reminder_ids: list[uuid.UUID]
) -> None:
    """Mark reminders as notified after scheduler delivery."""
    if not reminder_ids:
        return
    await db.execute(
        update(Reminder)
        .where(Reminder.id.in_(reminder_ids))
        .values(status="notified", updated_at=datetime.now(timezone.utc))
    )
    await db.flush()
