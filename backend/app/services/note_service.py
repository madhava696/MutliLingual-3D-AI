"""
Note service — CRUD operations for notes.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


async def create_note(
    db: AsyncSession,
    session_id: uuid.UUID,
    title: str,
    content: str,
    language: str = "en",
    source_type: str | None = None,
) -> Note:
    """Create a new note."""
    note = Note(
        session_id=session_id,
        title=title,
        content=content,
        language=language,
        source_type=source_type,
    )
    db.add(note)
    await db.flush()
    return note


async def get_notes_by_session(
    db: AsyncSession, session_id: uuid.UUID
) -> list[Note]:
    """List all notes for a session."""
    result = await db.execute(
        select(Note)
        .where(Note.session_id == session_id)
        .order_by(Note.created_at.desc())
    )
    return list(result.scalars().all())


async def get_note_by_id(
    db: AsyncSession, note_id: uuid.UUID
) -> Note | None:
    """Get a single note by ID."""
    result = await db.execute(select(Note).where(Note.id == note_id))
    return result.scalar_one_or_none()


async def delete_note(db: AsyncSession, note: Note) -> None:
    """Delete a note."""
    await db.delete(note)
    await db.flush()
