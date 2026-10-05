"""Pydantic schemas for note API."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NoteCreate(BaseModel):
    """Request body for creating a note."""
    session_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_type: Optional[str] = Field(
        None, pattern="^(manual|pdf_summary|research)$"
    )


class NoteResponse(BaseModel):
    """Note response DTO."""
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    content: str
    language: str
    source_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NoteListResponse(BaseModel):
    """List of notes."""
    notes: list[NoteResponse]
