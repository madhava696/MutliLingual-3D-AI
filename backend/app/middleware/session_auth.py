"""
Session token authentication middleware.
Validates session_token header — NOT the session UUID.
Session IDs are public identifiers; session_tokens are the secret credential.
"""

import uuid
from typing import Optional

from fastapi import Header, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.session import Session


async def get_session_token(
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token"),
) -> str:
    """Extract session token from header."""
    if not x_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Session-Token header",
        )
    return x_session_token


async def get_authenticated_session(
    session_token: str = Depends(get_session_token),
    db: AsyncSession = Depends(get_db),
) -> Session:
    """
    Authenticate a request using session_token.
    Returns the Session object if the token is valid.
    Rejects requests where only session_id is provided.
    """
    result = await db.execute(
        select(Session).where(Session.session_token == session_token)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )

    return session


async def verify_session_ownership(
    session_id: uuid.UUID,
    session_token: str = Depends(get_session_token),
    db: AsyncSession = Depends(get_db),
) -> Session:
    """
    Verify that the session_token matches the given session_id.
    Used for endpoints that take session_id as a path parameter.
    """
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.session_token == session_token,
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token for this session",
        )

    return session
