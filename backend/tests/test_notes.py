"""
Tests for Notes endpoints:
  POST   /api/v1/notes               — create note  (requires X-Session-Token)
  GET    /api/v1/notes?session_id=    — list notes   (requires X-Session-Token)
  DELETE /api/v1/notes/{note_id}      — delete note  (requires X-Session-Token)
"""

import uuid

import pytest


class TestCreateNote:
    """POST /api/v1/notes"""

    async def test_create_note_success(self, client, create_test_session):
        """Happy path: create a note with valid session."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "My First Note",
                "content": "Some useful content",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My First Note"
        assert data["content"] == "Some useful content"
        assert data["session_id"] == str(sess["session_id"])
        assert data["language"] == "en"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_note_with_source_type_manual(self, client, create_test_session):
        """source_type = 'manual' should be accepted."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Manual Note",
                "content": "Manually typed",
                "source_type": "manual",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["source_type"] == "manual"

    async def test_create_note_with_source_type_pdf_summary(self, client, create_test_session):
        """source_type = 'pdf_summary' should be accepted."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "PDF Summary",
                "content": "Extracted from PDF",
                "source_type": "pdf_summary",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["source_type"] == "pdf_summary"

    async def test_create_note_with_source_type_research(self, client, create_test_session):
        """source_type = 'research' should be accepted."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Research",
                "content": "Research notes",
                "source_type": "research",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["source_type"] == "research"

    async def test_create_note_invalid_source_type(self, client, create_test_session):
        """Invalid source_type should fail 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Bad Source",
                "content": "Body",
                "source_type": "unknown",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_null_source_type(self, client, create_test_session):
        """No source_type (null) should be fine — field is optional."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "No Source",
                "content": "Body",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["source_type"] is None

    async def test_create_note_missing_title(self, client, create_test_session):
        """Missing title → 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "content": "Body without title",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_empty_title(self, client, create_test_session):
        """Empty string title → 422 (min_length=1)."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "",
                "content": "Body",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_missing_content(self, client, create_test_session):
        """Missing content → 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "No Content",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_empty_content(self, client, create_test_session):
        """Empty content → 422 (min_length=1)."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Title",
                "content": "",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_missing_session_id(self, client, create_test_session):
        """Missing session_id in body → 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "title": "No Session",
                "content": "Body",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_session_id_mismatch(self, client, create_test_session):
        """body.session_id != authenticated session → 403."""
        sess = await create_test_session()
        fake_id = str(uuid.uuid4())
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": fake_id,
                "title": "Mismatch",
                "content": "Body",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 403

    async def test_create_note_no_auth(self, client):
        """No X-Session-Token → 401."""
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(uuid.uuid4()),
                "title": "No Auth",
                "content": "Body",
            },
        )
        assert response.status_code == 401

    async def test_create_note_invalid_token(self, client):
        """Invalid X-Session-Token → 401."""
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(uuid.uuid4()),
                "title": "Bad Token",
                "content": "Body",
            },
            headers={"X-Session-Token": "bad-token"},
        )
        assert response.status_code == 401

    async def test_create_note_inherits_session_language(self, client, create_test_session):
        """Note language should match the session language."""
        sess = await create_test_session(language="hi")
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Hindi Note",
                "content": "हिंदी में",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["language"] == "hi"


class TestListNotes:
    """GET /api/v1/notes?session_id=..."""

    async def test_list_notes_empty(self, client, create_test_session):
        """No notes → empty list."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/notes",
            params={"session_id": str(sess["session_id"])},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == []

    async def test_list_notes_returns_created_notes(self, client, create_test_session):
        """Created notes should appear in the list."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}
        sid = str(sess["session_id"])

        # Create 2 notes
        await client.post(
            "/api/v1/notes",
            json={"session_id": sid, "title": "Note 1", "content": "C1"},
            headers=headers,
        )
        await client.post(
            "/api/v1/notes",
            json={"session_id": sid, "title": "Note 2", "content": "C2"},
            headers=headers,
        )

        response = await client.get(
            "/api/v1/notes",
            params={"session_id": sid},
            headers=headers,
        )
        assert response.status_code == 200
        notes = response.json()["notes"]
        assert len(notes) == 2
        titles = {n["title"] for n in notes}
        assert titles == {"Note 1", "Note 2"}

    async def test_list_notes_missing_session_id(self, client, create_test_session):
        """Missing session_id query param → 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/notes",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_list_notes_session_id_mismatch(self, client, create_test_session):
        """session_id != authenticated session → 403."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/notes",
            params={"session_id": str(uuid.uuid4())},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 403

    async def test_list_notes_no_auth(self, client):
        """No token → 401."""
        response = await client.get(
            "/api/v1/notes",
            params={"session_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401

    async def test_list_notes_isolation(self, client, create_test_session):
        """Notes from session A should not appear in session B's list."""
        sess_a = await create_test_session()
        sess_b = await create_test_session()

        # Create note in session A
        await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess_a["session_id"]),
                "title": "A's note",
                "content": "Content A",
            },
            headers={"X-Session-Token": sess_a["session_token"]},
        )

        # List notes for session B
        response = await client.get(
            "/api/v1/notes",
            params={"session_id": str(sess_b["session_id"])},
            headers={"X-Session-Token": sess_b["session_token"]},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == []


class TestDeleteNote:
    """DELETE /api/v1/notes/{note_id}"""

    async def test_delete_note_success(self, client, create_test_session):
        """Delete an existing note → 200 + deleted=True."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        # Create a note
        create_resp = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "To Delete",
                "content": "Goodbye",
            },
            headers=headers,
        )
        note_id = create_resp.json()["id"]

        # Delete it
        response = await client.delete(
            f"/api/v1/notes/{note_id}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    async def test_delete_note_removes_from_list(self, client, create_test_session):
        """After deletion, note should no longer appear in list."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}
        sid = str(sess["session_id"])

        create_resp = await client.post(
            "/api/v1/notes",
            json={"session_id": sid, "title": "Ephemeral", "content": "Gone"},
            headers=headers,
        )
        note_id = create_resp.json()["id"]

        await client.delete(f"/api/v1/notes/{note_id}", headers=headers)

        list_resp = await client.get(
            "/api/v1/notes", params={"session_id": sid}, headers=headers
        )
        assert len(list_resp.json()["notes"]) == 0

    async def test_delete_note_not_found(self, client, create_test_session):
        """Non-existent note_id → 404."""
        sess = await create_test_session()
        fake_note_id = uuid.uuid4()
        response = await client.delete(
            f"/api/v1/notes/{fake_note_id}",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 404

    async def test_delete_note_wrong_session(self, client, create_test_session):
        """Note belongs to session A, token is session B → 404."""
        sess_a = await create_test_session()
        sess_b = await create_test_session()

        # Create note in session A
        create_resp = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess_a["session_id"]),
                "title": "A's note",
                "content": "Private",
            },
            headers={"X-Session-Token": sess_a["session_token"]},
        )
        note_id = create_resp.json()["id"]

        # Try to delete with session B's token
        response = await client.delete(
            f"/api/v1/notes/{note_id}",
            headers={"X-Session-Token": sess_b["session_token"]},
        )
        assert response.status_code == 404

    async def test_delete_note_no_auth(self, client):
        """No token → 401."""
        response = await client.delete(
            f"/api/v1/notes/{uuid.uuid4()}"
        )
        assert response.status_code == 401

    async def test_delete_note_invalid_uuid(self, client, create_test_session):
        """Invalid UUID → 422."""
        sess = await create_test_session()
        response = await client.delete(
            "/api/v1/notes/not-a-uuid",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_delete_note_sql_injection_id(self, client, create_test_session):
        """SQL injection attempt in note_id path param → 422."""
        sess = await create_test_session()
        response = await client.delete(
            "/api/v1/notes/' OR 1=1;--",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_delete_note_empty_token(self, client):
        """Empty string in X-Session-Token header → 401."""
        response = await client.delete(
            f"/api/v1/notes/{uuid.uuid4()}",
            headers={"X-Session-Token": ""},
        )
        assert response.status_code == 401


class TestNoteInvalidDataPayloads:
    """Detailed invalid data scenarios for notes API."""

    async def test_create_note_title_too_long(self, client, create_test_session):
        """Title exceeding 255 characters should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "A" * 256,
                "content": "Valid content",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_title", [123, True, ["title"], {"t": "test"}])
    async def test_create_note_invalid_title_types(self, client, create_test_session, bad_title):
        """Non-string title values should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": bad_title,
                "content": "Valid content",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_content", [123, True, ["content"], {"c": "test"}])
    async def test_create_note_invalid_content_types(self, client, create_test_session, bad_content):
        """Non-string content values should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Valid title",
                "content": bad_content,
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_source", ["wiki", "automated", "123", "AI", "random"])
    async def test_create_note_disallowed_source_types(self, client, create_test_session, bad_source):
        """source_type not matching (manual|pdf_summary|research) should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Valid title",
                "content": "Valid content",
                "source_type": bad_source,
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_sid", ["not-a-uuid", "12345", "uuid-here", "", "   "])
    async def test_create_note_invalid_session_id_format(self, client, create_test_session, bad_sid):
        """Invalid session_id format in body should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            json={
                "session_id": bad_sid,
                "title": "Valid title",
                "content": "Valid content",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_note_malformed_json_body(self, client, create_test_session):
        """Raw malformed JSON body should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/notes",
            content=b"{{{bad json content",
            headers={
                "Content-Type": "application/json",
                "X-Session-Token": sess["session_token"],
            },
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_query_sid", ["not-a-uuid", "123", "' OR 1=1;--", "   "])
    async def test_list_notes_invalid_session_id_query_param(self, client, create_test_session, bad_query_sid):
        """Invalid UUID format in session_id query param should fail with 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/notes",
            params={"session_id": bad_query_sid},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

