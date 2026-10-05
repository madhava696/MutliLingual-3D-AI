"""
WebSocket handler.
Manages bidirectional real-time communication with auth, text messages,
and (later) audio frames.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, async_session_factory
from app.services.session_service import get_session_by_token, touch_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections keyed by session_id."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_event(self, session_id: str, event: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            try:
                await ws.send_json(event)
            except Exception:
                self.disconnect(session_id)

    def get_connection(self, session_id: str) -> WebSocket | None:
        return self.active_connections.get(session_id)


# Global connection manager — used by notification service
manager = ConnectionManager()


@router.websocket("/sessions/{session_id}/stream")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
):
    """
    WebSocket endpoint for real-time communication.
    
    Protocol:
    1. Client connects
    2. Client sends auth event: {"type": "auth", "session_token": "..."}
    3. Server responds with auth result
    4. Bidirectional text/audio communication begins
    """
    await websocket.accept()

    # --- Step 1: Authenticate ---
    authenticated_session = None
    try:
        # Wait for auth message (timeout could be added)
        raw = await websocket.receive_text()
        data = json.loads(raw)

        if data.get("type") != "auth" or "session_token" not in data:
            await websocket.send_json({
                "type": "auth.result",
                "success": False,
                "error": "First message must be auth event with session_token",
            })
            await websocket.close(code=4001)
            return

        # Validate token
        async with async_session_factory() as db:
            session = await get_session_by_token(db, data["session_token"])
            if session is None or str(session.id) != session_id:
                await websocket.send_json({
                    "type": "auth.result",
                    "success": False,
                    "error": "Invalid session token",
                })
                await websocket.close(code=4001)
                return

            authenticated_session = session
            await touch_session(db, session)
            await db.commit()

        await websocket.send_json({
            "type": "auth.result",
            "success": True,
        })

        # Register connection
        await manager.connect(session_id, websocket)
        logger.info(f"WebSocket authenticated for session {session_id}")

    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        try:
            await websocket.close(code=4000)
        except Exception:
            pass
        return

    # --- Step 2: Message loop ---
    try:
        while True:
            # Handle both text and binary frames
            message = await websocket.receive()

            if "text" in message:
                data = json.loads(message["text"])
                await handle_text_event(websocket, session_id, data)

            elif "bytes" in message:
                # Binary audio frames — to be handled by speech pipeline
                await handle_audio_frame(websocket, session_id, message["bytes"])

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        manager.disconnect(session_id)


async def handle_text_event(websocket: WebSocket, session_id: str, data: dict):
    """
    Handle incoming text events from the client.
    This is the entry point for the text-only vertical slice.
    """
    event_type = data.get("type")

    if event_type == "text.message":
        content = data.get("content", "")
        language = data.get("language", "en")

        if not content.strip():
            return

        # Emit thinking state
        await websocket.send_json({
            "type": "agent.state",
            "state": "thinking",
        })

        # TODO: Wire to orchestrator/router
        # For now, echo back as a placeholder
        await websocket.send_json({
            "type": "response.text",
            "text": f"[Echo] You said: {content}",
            "is_final": True,
        })

        await websocket.send_json({
            "type": "agent.state",
            "state": "idle",
        })

    elif event_type == "playback.interrupt":
        # Client interrupted audio playback
        # TODO: Cancel current TTS/LLM generation
        await websocket.send_json({
            "type": "agent.state",
            "state": "idle",
        })

    elif event_type == "session.language":
        language = data.get("language", "en")
        # Update session language
        async with async_session_factory() as db:
            session = await get_session_by_token(db, "")  # TODO: track token in connection
            # For now, acknowledge
            await db.commit()

    elif event_type == "tool.confirm":
        tool_call_id = data.get("tool_call_id")
        approved = data.get("approved", False)
        # TODO: Resume or cancel pending tool execution
        pass


async def handle_audio_frame(websocket: WebSocket, session_id: str, audio_data: bytes):
    """
    Handle incoming audio binary frames.
    To be connected to streaming ASR adapter.
    """
    # TODO: Forward to ASR streaming adapter
    # For now, this is a placeholder for Phase 3
    pass
