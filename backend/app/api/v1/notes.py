"""
Note API endpoints.
All endpoints require session_token authentication.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.session import Session
from app.schemas.note import NoteCreate, NoteResponse, NoteListResponse
from app.services import note_service
from app.middleware.session_auth import get_authenticated_session

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteCreate,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Create a new note. Persists even in private mode (explicit user action)."""
    if body.session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session ID does not match authenticated session",
        )
    note = await note_service.create_note(
        db=db,
        session_id=session.id,
        title=body.title,
        content=body.content,
        language=session.language,
        source_type=body.source_type,
    )
    return NoteResponse.model_validate(note)


@router.get("", response_model=NoteListResponse)
async def list_notes(
    session_id: uuid.UUID = Query(...),
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """List all notes for the authenticated session."""
    if session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session ID does not match authenticated session",
        )
    notes = await note_service.get_notes_by_session(db, session.id)
    return NoteListResponse(
        notes=[NoteResponse.model_validate(n) for n in notes]
    )


@router.delete("/{note_id}", status_code=status.HTTP_200_OK)
async def delete_note(
    note_id: uuid.UUID,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Delete a note."""
    note = await note_service.get_note_by_id(db, note_id)
    if note is None or note.session_id != session.id:
        raise HTTPException(status_code=404, detail="Note not found")

    await note_service.delete_note(db, note)
    return {"deleted": True}
