"""
Session service — create, retrieve, touch (extend expiry), delete sessions.
"""

import uuid
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.config import get_settings


async def create_session(
    db: AsyncSession,
    language: str = "en",
    private_mode: bool = False,
) -> Session:
    """Create a new session with a cryptographically random token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    session = Session(
        session_token=secrets.token_urlsafe(settings.SESSION_TOKEN_BYTES),
        language=language,
        private_mode=private_mode,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.SESSION_TTL_MINUTES),
    )
    db.add(session)
    await db.flush()
    return session


async def get_session_by_id(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    """Retrieve a session by its public ID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()


async def get_session_by_token(db: AsyncSession, session_token: str) -> Session | None:
    """Retrieve a session by its secret token."""
    result = await db.execute(
        select(Session).where(Session.session_token == session_token)
    )
    return result.scalar_one_or_none()


async def touch_session(db: AsyncSession, session: Session) -> Session:
    """Extend session expiry on activity."""
    settings = get_settings()
    session.expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.SESSION_TTL_MINUTES
    )
    await db.flush()
    return session


async def delete_session(db: AsyncSession, session: Session) -> None:
    """Delete a session (cascade deletes reminders, notes, files)."""
    await db.delete(session)
    await db.flush()
