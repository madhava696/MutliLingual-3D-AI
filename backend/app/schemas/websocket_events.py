"""Pydantic schemas for WebSocket event protocol."""

from typing import Optional, Any
from pydantic import BaseModel


# --- Client → Server Events ---

class WSAuthEvent(BaseModel):
    type: str = "auth"
    session_token: str


class WSTextMessage(BaseModel):
    type: str = "text.message"
    content: str
    language: Optional[str] = None


class WSAudioStop(BaseModel):
    type: str = "audio.stop"


class WSPlaybackInterrupt(BaseModel):
    type: str = "playback.interrupt"


class WSLanguageChange(BaseModel):
    type: str = "session.language"
    language: str


class WSToolConfirm(BaseModel):
    type: str = "tool.confirm"
    tool_call_id: str
    approved: bool


# --- Server → Client Events ---

class WSAuthResult(BaseModel):
    type: str = "auth.result"
    success: bool
    error: Optional[str] = None


class WSTranscriptionPartial(BaseModel):
    type: str = "transcription.partial"
    text: str
    language: Optional[str] = None


class WSTranscriptionFinal(BaseModel):
    type: str = "transcription.final"
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None


class WSAgentState(BaseModel):
    type: str = "agent.state"
    state: str  # "thinking" | "speaking" | "idle" | "listening"


class WSResponseText(BaseModel):
    type: str = "response.text"
    text: str
    is_final: bool = False


class WSToolConfirmationRequired(BaseModel):
    type: str = "tool.confirmation_required"
    tool_call_id: str
    tool: str
    args: dict
    description: str


class WSToolResult(BaseModel):
    type: str = "tool.result"
    tool: str
    success: bool
    result: Any = None


class WSTaskCompleted(BaseModel):
    type: str = "task.completed"
    task_type: str
    summary: str


class WSUsageUpdate(BaseModel):
    type: str = "usage.update"
    provider: str
    cost: Optional[float] = None
    tokens: Optional[int] = None


class WSReminderDue(BaseModel):
    type: str = "reminder.due"
    reminder_id: str
    title: str
    remind_at: str


class WSError(BaseModel):
    type: str = "error"
    code: str
    message: str
    recoverable: bool = True
