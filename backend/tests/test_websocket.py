"""
Tests for the WebSocket endpoint:
  WS /api/v1/sessions/{session_id}/stream

WebSocket testing requires special handling — we use httpx-ws or
FastAPI's built-in TestClient for WS. Since the test stack uses
httpx.AsyncClient (which doesn't support WS), these tests use
Starlette's TestClient synchronously.
"""

import json
import uuid

import pytest
from starlette.testclient import TestClient

from tests.conftest import TestSessionLocal, _noop_lifespan, _override_get_db

from app.db.database import get_db
from app.main import create_app
from app.models.session import Session

import secrets
from datetime import datetime, timedelta, timezone


def _create_sync_app():
    """Create a test app with dependency overrides (for sync TestClient)."""
    application = create_app()
    application.router.lifespan_context = _noop_lifespan
    application.dependency_overrides[get_db] = _override_get_db
    return application


class TestWebSocketAuth:
    """WebSocket authentication flow."""

    async def test_ws_auth_no_auth_message(self):
        """Connect but send non-auth message → closed with 4001."""
        # Create tables
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Create a session in the DB
        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            # Send a non-auth message
            ws.send_text(json.dumps({"type": "text.message", "content": "hello"}))
            data = ws.receive_json()
            assert data["type"] == "auth.result"
            assert data["success"] is False

        # Cleanup
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_auth_invalid_token(self):
        """Auth with invalid token → auth.result with success=False."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            ws.send_text(json.dumps({
                "type": "auth",
                "session_token": "wrong-token-value",
            }))
            data = ws.receive_json()
            assert data["type"] == "auth.result"
            assert data["success"] is False

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_auth_wrong_session_id(self):
        """Auth with valid token but wrong session_id in URL → failure."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        wrong_id = uuid.uuid4()
        with client.websocket_connect(f"/api/v1/sessions/{wrong_id}/stream") as ws:
            ws.send_text(json.dumps({
                "type": "auth",
                "session_token": token,
            }))
            data = ws.receive_json()
            assert data["type"] == "auth.result"
            assert data["success"] is False

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_auth_success(self):
        """Valid auth → auth.result with success=True."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            ws.send_text(json.dumps({
                "type": "auth",
                "session_token": token,
            }))
            data = ws.receive_json()
            assert data["type"] == "auth.result"
            assert data["success"] is True

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_auth_missing_token_field(self):
        """Auth event without session_token field → failure."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            ws.send_text(json.dumps({"type": "auth"}))  # missing session_token
            data = ws.receive_json()
            assert data["type"] == "auth.result"
            assert data["success"] is False

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


class TestWebSocketMessages:
    """Post-auth message handling (text events)."""

    async def test_ws_language_change(self):
        """After auth, send session.language event → get acknowledgement."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            # Auth
            ws.send_text(json.dumps({"type": "auth", "session_token": token}))
            auth_resp = ws.receive_json()
            assert auth_resp["success"] is True

            # Send language change
            ws.send_text(json.dumps({
                "type": "session.language",
                "language": "hi",
            }))
            lang_resp = ws.receive_json()
            assert lang_resp["type"] == "session.language_updated"
            assert lang_resp["language"] == "hi"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_playback_interrupt(self):
        """playback.interrupt → agent.state idle."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            # Auth
            ws.send_text(json.dumps({"type": "auth", "session_token": token}))
            auth_resp = ws.receive_json()
            assert auth_resp["success"] is True

            # Playback interrupt
            ws.send_text(json.dumps({"type": "playback.interrupt"}))
            state_resp = ws.receive_json()
            assert state_resp["type"] == "agent.state"
            assert state_resp["state"] == "idle"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_empty_text_message_ignored(self):
        """Empty text.message content should be silently ignored."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        token = secrets.token_urlsafe(48)
        now = datetime.now(timezone.utc)
        async with TestSessionLocal() as db:
            sess = Session(
                id=session_id,
                session_token=token,
                language="en",
                private_mode=False,
                created_at=now,
                expires_at=now + timedelta(minutes=30),
            )
            db.add(sess)
            await db.commit()

        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            # Auth
            ws.send_text(json.dumps({"type": "auth", "session_token": token}))
            auth_resp = ws.receive_json()
            assert auth_resp["success"] is True

            # Send empty text message
            ws.send_text(json.dumps({
                "type": "text.message",
                "content": "   ",
                "language": "en",
            }))

            # Send a follow-up to verify connection is still alive
            ws.send_text(json.dumps({"type": "playback.interrupt"}))
            state_resp = ws.receive_json()
            assert state_resp["type"] == "agent.state"
            assert state_resp["state"] == "idle"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


class TestWebSocketInvalidDataScenarios:
    """Invalid data scenarios for WS /api/v1/sessions/{session_id}/stream."""

    async def test_ws_auth_malformed_json_first_message(self):
        """Sending unparseable non-JSON text as first message triggers close."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        app = _create_sync_app()
        client = TestClient(app)

        with pytest.raises(Exception):
            with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
                ws.send_text("not json at all {{{")
                ws.receive_json()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_auth_empty_token_string(self):
        """Sending empty string token fails authentication and closes connection."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            ws.send_text(json.dumps({"type": "auth", "session_token": ""}))
            resp = ws.receive_json()
            assert resp["type"] == "auth.result"
            assert resp["success"] is False
            assert "error" in resp

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_ws_auth_wrong_token_types(self):
        """Sending non-string session_token (e.g. integer) is rejected."""
        from tests.conftest import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_id = uuid.uuid4()
        app = _create_sync_app()
        client = TestClient(app)

        with client.websocket_connect(f"/api/v1/sessions/{session_id}/stream") as ws:
            ws.send_text(json.dumps({"type": "auth", "session_token": 99999}))
            resp = ws.receive_json()
            assert resp["type"] == "auth.result"
            assert resp["success"] is False

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

