"""
Reminder API endpoints.
All endpoints require session_token authentication.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.middleware.session_auth import get_authenticated_session
from app.models.session import Session
from app.schemas.reminder import (
    ReminderCreate,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdate,
)
from app.services import reminder_service

router = APIRouter(prefix="/tasks/reminders", tags=["reminders"])


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    body: ReminderCreate,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Create a new reminder. Persists even in private mode (explicit user action)."""
    if body.session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session ID does not match authenticated session",
        )
    reminder = await reminder_service.create_reminder(
        db=db,
        session_id=session.id,
        title=body.title,
        remind_at=body.remind_at,
        description=body.description,
        language=session.language,
    )
    return ReminderResponse.model_validate(reminder)


@router.get("", response_model=ReminderListResponse)
async def list_reminders(
    session_id: uuid.UUID = Query(...),
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """List all reminders for the authenticated session."""
    if session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session ID does not match authenticated session",
        )
    reminders = await reminder_service.get_reminders_by_session(db, session.id)
    return ReminderListResponse(
        reminders=[ReminderResponse.model_validate(r) for r in reminders]
    )


@router.patch("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdate,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Update a reminder (mark completed, reschedule)."""
    reminder = await reminder_service.get_reminder_by_id(db, reminder_id)
    if reminder is None or reminder.session_id != session.id:
        raise HTTPException(status_code=404, detail="Reminder not found")

    updated = await reminder_service.update_reminder(
        db, reminder, status=body.status, remind_at=body.remind_at
    )
    return ReminderResponse.model_validate(updated)


@router.delete("/{reminder_id}", status_code=status.HTTP_200_OK)
async def delete_reminder(
    reminder_id: uuid.UUID,
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Delete a reminder."""
    reminder = await reminder_service.get_reminder_by_id(db, reminder_id)
    if reminder is None or reminder.session_id != session.id:
        raise HTTPException(status_code=404, detail="Reminder not found")

    await reminder_service.delete_reminder(db, reminder)
    return {"deleted": True}
