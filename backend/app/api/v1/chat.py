"""
Chat API endpoint.
Supports REST-based chat execution through the orchestrator.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.middleware.session_auth import verify_session_ownership
from app.models.session import Session
from app.orchestrator.engine import get_orchestrator

router = APIRouter(tags=["chat"])


class ChatMessageRequest(BaseModel):
    """Chat message request."""
    message: str = Field(..., min_length=1)
    language: Optional[str] = "en"
    conversation_history: Optional[list[dict]] = None


class ChatMessageResponse(BaseModel):
    """Chat message response."""
    response: str
    is_tool_result: bool
    model_used: Optional[str] = None
    cost_usd: float = 0.0
    latency_ms: int = 0
    tool_data: Optional[dict] = None


@router.post("/sessions/{session_id}/chat", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: uuid.UUID,
    body: ChatMessageRequest,
    session: Session = Depends(verify_session_ownership),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to the AI Companion orchestrator via REST.
    Routes through intent classifier → deterministic tool OR LLM provider.
    """
    orchestrator = get_orchestrator()
    try:
        result = await orchestrator.process_message(
            db=db,
            session_id=session.id,
            text=body.message,
            language=body.language or session.language or "en",
            conversation_history=body.conversation_history or [],
        )
        return ChatMessageResponse(
            response=result.text,
            is_tool_result=result.is_tool_result,
            model_used=result.model_used,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            tool_data=result.tool_data,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}",
        )
