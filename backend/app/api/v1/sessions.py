"""
Session API endpoints.
POST /sessions — create (no auth)
DELETE /sessions/{id} — delete with full data cleanup (requires session_token)
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.middleware.session_auth import verify_session_ownership
from app.schemas.session import SessionCreate, SessionDeleteResponse, SessionResponse
from app.services import session_service
from app.services.deletion_service import delete_session_data

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new session.
    Returns session_id (public) and session_token (secret credential).
    No authentication required — this is how a session begins.
    """
    session = await session_service.create_session(
        db=db,
        language=body.language,
        private_mode=body.private_mode,
    )
    return SessionResponse(
        session_id=session.id,
        session_token=session.session_token,
        language=session.language,
        private_mode=session.private_mode,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


@router.delete("/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(
    session_id: uuid.UUID,
    session=Depends(verify_session_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a session and ALL associated data.
    Uses SessionDeletionService for comprehensive cleanup:
    DB records + Redis + filesystem + temp files + usage_log anonymization.
    Requires valid session_token.
    """
    # TODO: inject redis_client when Redis is initialized
    report = await delete_session_data(
        db=db,
        session=session,
        redis_client=None,
    )
    return SessionDeleteResponse(
        deleted=True,
        details=report.to_dict(),
    )
