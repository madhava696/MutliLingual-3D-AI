"""Pydantic schemas for reminder API."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    """Request body for creating a reminder."""
    session_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    remind_at: datetime


class ReminderUpdate(BaseModel):
    """Request body for updating a reminder."""
    status: Optional[str] = Field(None, pattern="^(pending|completed|cancelled)$")
    remind_at: Optional[datetime] = None


class ReminderResponse(BaseModel):
    """Reminder response DTO."""
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    description: Optional[str]
    remind_at: datetime
    status: str
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReminderListResponse(BaseModel):
    """List of reminders."""
    reminders: list[ReminderResponse]
