"""Pydantic schemas for session API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """Request body for creating a new session."""
    language: str = Field(default="en", pattern="^(en|hi|te)$", description="ISO 639-1 language code")
    private_mode: bool = Field(default=False, description="Enable conversational privacy mode")


class SessionResponse(BaseModel):
    """Response after creating a session. Contains both public ID and secret token."""
    session_id: uuid.UUID = Field(description="Public identifier — safe in URLs")
    session_token: str = Field(description="Secret credential — use for authentication")
    language: str
    private_mode: bool
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class SessionDeleteResponse(BaseModel):
    """Response after deleting a session."""
    deleted: bool = True
    details: dict = Field(default_factory=dict)
