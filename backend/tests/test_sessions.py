"""
Tests for Session endpoints:
  POST   /api/v1/sessions          — create session
  DELETE /api/v1/sessions/{id}     — delete session (requires X-Session-Token)
"""

import uuid

import pytest


class TestCreateSession:
    """POST /api/v1/sessions"""

    async def test_create_session_defaults(self, client):
        """Default language='en', private_mode=False."""
        response = await client.post("/api/v1/sessions", json={})
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert "session_token" in data
        assert data["language"] == "en"
        assert data["private_mode"] is False
        assert "created_at" in data
        assert "expires_at" in data

    async def test_create_session_with_hindi(self, client):
        """Create a session with language='hi'."""
        response = await client.post(
            "/api/v1/sessions", json={"language": "hi"}
        )
        assert response.status_code == 201
        assert response.json()["language"] == "hi"

    async def test_create_session_with_telugu(self, client):
        """Create a session with language='te'."""
        response = await client.post(
            "/api/v1/sessions", json={"language": "te"}
        )
        assert response.status_code == 201
        assert response.json()["language"] == "te"

    async def test_create_session_private_mode(self, client):
        """Create a session with private_mode=True."""
        response = await client.post(
            "/api/v1/sessions", json={"private_mode": True}
        )
        assert response.status_code == 201
        assert response.json()["private_mode"] is True

    async def test_create_session_all_fields(self, client):
        """Create a session specifying both language and private_mode."""
        response = await client.post(
            "/api/v1/sessions",
            json={"language": "hi", "private_mode": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["language"] == "hi"
        assert data["private_mode"] is True

    async def test_create_session_invalid_language(self, client):
        """Language outside allowed pattern (en|hi|te) should fail 422."""
        response = await client.post(
            "/api/v1/sessions", json={"language": "fr"}
        )
        assert response.status_code == 422

    async def test_create_session_empty_language(self, client):
        """Empty string language should fail validation."""
        response = await client.post(
            "/api/v1/sessions", json={"language": ""}
        )
        assert response.status_code == 422

    async def test_create_session_token_is_unique(self, client):
        """Two sessions should have different tokens."""
        r1 = await client.post("/api/v1/sessions", json={})
        r2 = await client.post("/api/v1/sessions", json={})
        assert r1.json()["session_token"] != r2.json()["session_token"]

    async def test_create_session_id_is_valid_uuid(self, client):
        """session_id should be a valid UUID string."""
        response = await client.post("/api/v1/sessions", json={})
        sid = response.json()["session_id"]
        parsed = uuid.UUID(sid)  # should not raise
        assert str(parsed) == sid

    async def test_create_session_expires_in_future(self, client):
        """expires_at should be after created_at."""
        response = await client.post("/api/v1/sessions", json={})
        data = response.json()
        assert data["expires_at"] > data["created_at"]


class TestDeleteSession:
    """DELETE /api/v1/sessions/{session_id}"""

    async def test_delete_session_success(self, client, create_test_session):
        """Valid token + matching session_id → 200 with deleted=True."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/sessions/{sess['session_id']}",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert "details" in data

    async def test_delete_session_missing_token(self, client, create_test_session):
        """No X-Session-Token header → 401."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/sessions/{sess['session_id']}"
        )
        assert response.status_code == 401

    async def test_delete_session_wrong_token(self, client, create_test_session):
        """Invalid token → 401."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/sessions/{sess['session_id']}",
            headers={"X-Session-Token": "invalid-token-value"},
        )
        assert response.status_code == 401

    async def test_delete_session_wrong_session_id(self, client, create_test_session):
        """Valid token but mismatched session_id → 401."""
        sess = await create_test_session()
        fake_id = uuid.uuid4()
        response = await client.delete(
            f"/api/v1/sessions/{fake_id}",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 401

    async def test_delete_nonexistent_session(self, client):
        """Non-existent session_id → 401 (no matching token)."""
        fake_id = uuid.uuid4()
        response = await client.delete(
            f"/api/v1/sessions/{fake_id}",
            headers={"X-Session-Token": "no-such-token"},
        )
        assert response.status_code == 401

    async def test_delete_session_invalid_uuid(self, client):
        """Non-UUID session_id → 422."""
        response = await client.delete(
            "/api/v1/sessions/not-a-uuid",
            headers={"X-Session-Token": "some-token"},
        )
        assert response.status_code == 422

    async def test_delete_session_idempotent(self, client, create_test_session):
        """Deleting the same session twice → first is 200, second is 401."""
        sess = await create_test_session()
        token = sess["session_token"]
        sid = sess["session_id"]

        r1 = await client.delete(
            f"/api/v1/sessions/{sid}",
            headers={"X-Session-Token": token},
        )
        assert r1.status_code == 200

        r2 = await client.delete(
            f"/api/v1/sessions/{sid}",
            headers={"X-Session-Token": token},
        )
        assert r2.status_code == 401

    async def test_delete_session_response_has_details(self, client, create_test_session):
        """Details dict should contain cleanup metadata."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/sessions/{sess['session_id']}",
            headers={"X-Session-Token": sess["session_token"]},
        )
        details = response.json()["details"]
        assert "db_records_deleted" in details
        assert "redis_keys_deleted" in details
        assert "files_removed" in details

    async def test_delete_session_empty_token_header(self, client, create_test_session):
        """Empty string in X-Session-Token header -> 401."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/sessions/{sess['session_id']}",
            headers={"X-Session-Token": ""},
        )
        assert response.status_code == 401

    async def test_delete_session_whitespace_token(self, client, create_test_session):
        """Whitespace token in X-Session-Token header -> 401."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/sessions/{sess['session_id']}",
            headers={"X-Session-Token": "   "},
        )
        assert response.status_code == 401

    async def test_delete_session_special_characters_in_uuid(self, client):
        """Special characters or SQL injection string as session_id -> 422."""
        response = await client.delete(
            "/api/v1/sessions/' OR 1=1;--",
            headers={"X-Session-Token": "any-token"},
        )
        assert response.status_code == 422


class TestSessionInvalidDataPayloads:
    """Detailed invalid data payloads for POST /api/v1/sessions."""

    @pytest.mark.parametrize("bad_lang", ["de", "es", "ja", "EN", "english", "null"])
    async def test_create_session_invalid_language_codes(self, client, bad_lang):
        """Disallowed language codes should trigger validation error 422."""
        response = await client.post("/api/v1/sessions", json={"language": bad_lang})
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_type", [123, True, ["en"], {"code": "en"}])
    async def test_create_session_invalid_language_types(self, client, bad_type):
        """Non-string language values should trigger 422."""
        response = await client.post("/api/v1/sessions", json={"language": bad_type})
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_private_mode", [["invalid"], {"active": True}, "not-a-bool"])
    async def test_create_session_invalid_private_mode_types(self, client, bad_private_mode):
        """Non-boolean private_mode values should fail with 422."""
        response = await client.post("/api/v1/sessions", json={"private_mode": bad_private_mode})
        assert response.status_code == 422

    async def test_create_session_payload_as_list(self, client):
        """Array payload instead of JSON object should trigger 422."""
        response = await client.post("/api/v1/sessions", json=[{"language": "en"}])
        assert response.status_code == 422

    async def test_create_session_malformed_json_body(self, client):
        """Malformed raw JSON content should be rejected."""
        response = await client.post(
            "/api/v1/sessions",
            content=b"{invalid_json:",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

