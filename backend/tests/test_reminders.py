"""
Tests for Reminder endpoints:
  POST   /api/v1/tasks/reminders              — create reminder
  GET    /api/v1/tasks/reminders?session_id=   — list reminders
  PATCH  /api/v1/tasks/reminders/{id}          — update reminder
  DELETE /api/v1/tasks/reminders/{id}          — delete reminder
All require X-Session-Token.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest


def _future_iso(minutes: int = 60) -> str:
    """Return an ISO-8601 datetime string `minutes` in the future."""
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class TestCreateReminder:
    """POST /api/v1/tasks/reminders"""

    async def test_create_reminder_success(self, client, create_test_session):
        """Happy path: valid reminder creation."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Buy groceries",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Buy groceries"
        assert data["status"] == "pending"
        assert data["session_id"] == str(sess["session_id"])
        assert "id" in data
        assert "created_at" in data
        assert "remind_at" in data

    async def test_create_reminder_with_description(self, client, create_test_session):
        """Optional description field."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Meeting",
                "description": "Team standup at 10 AM",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["description"] == "Team standup at 10 AM"

    async def test_create_reminder_null_description(self, client, create_test_session):
        """No description → null in response."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Quick Reminder",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["description"] is None

    async def test_create_reminder_missing_title(self, client, create_test_session):
        """No title → 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_reminder_empty_title(self, client, create_test_session):
        """Empty title → 422 (min_length=1)."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_reminder_missing_remind_at(self, client, create_test_session):
        """No remind_at → 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "No Time",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_reminder_invalid_remind_at(self, client, create_test_session):
        """Bad datetime format → 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Bad Date",
                "remind_at": "not-a-date",
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_reminder_session_id_mismatch(self, client, create_test_session):
        """body.session_id != authenticated session → 403."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(uuid.uuid4()),
                "title": "Mismatch",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 403

    async def test_create_reminder_no_auth(self, client):
        """No token → 401."""
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(uuid.uuid4()),
                "title": "Unauthenticated",
                "remind_at": _future_iso(),
            },
        )
        assert response.status_code == 401

    async def test_create_reminder_inherits_session_language(self, client, create_test_session):
        """Reminder language should match session language."""
        sess = await create_test_session(language="te")
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Telugu Reminder",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 201
        assert response.json()["language"] == "te"


class TestListReminders:
    """GET /api/v1/tasks/reminders?session_id=..."""

    async def test_list_reminders_empty(self, client, create_test_session):
        """No reminders → empty list."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": str(sess["session_id"])},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 200
        assert response.json()["reminders"] == []

    async def test_list_reminders_returns_created(self, client, create_test_session):
        """Created reminders appear in the list."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}
        sid = str(sess["session_id"])

        await client.post(
            "/api/v1/tasks/reminders",
            json={"session_id": sid, "title": "R1", "remind_at": _future_iso(30)},
            headers=headers,
        )
        await client.post(
            "/api/v1/tasks/reminders",
            json={"session_id": sid, "title": "R2", "remind_at": _future_iso(60)},
            headers=headers,
        )

        response = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": sid},
            headers=headers,
        )
        assert response.status_code == 200
        reminders = response.json()["reminders"]
        assert len(reminders) == 2

    async def test_list_reminders_missing_session_id(self, client, create_test_session):
        """Missing query param → 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/tasks/reminders",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_list_reminders_session_id_mismatch(self, client, create_test_session):
        """Querying with different session_id → 403."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": str(uuid.uuid4())},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 403

    async def test_list_reminders_no_auth(self, client):
        """No token → 401."""
        response = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401

    async def test_list_reminders_isolation(self, client, create_test_session):
        """Reminders from session A don't leak into session B."""
        sess_a = await create_test_session()
        sess_b = await create_test_session()

        await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess_a["session_id"]),
                "title": "A's Reminder",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess_a["session_token"]},
        )

        response = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": str(sess_b["session_id"])},
            headers={"X-Session-Token": sess_b["session_token"]},
        )
        assert response.json()["reminders"] == []


class TestUpdateReminder:
    """PATCH /api/v1/tasks/reminders/{reminder_id}"""

    async def test_update_status_to_completed(self, client, create_test_session):
        """Mark a reminder as completed."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Complete Me",
                "remind_at": _future_iso(),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"status": "completed"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    async def test_update_status_to_cancelled(self, client, create_test_session):
        """Mark a reminder as cancelled."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Cancel Me",
                "remind_at": _future_iso(),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"status": "cancelled"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_update_invalid_status(self, client, create_test_session):
        """Invalid status value → 422."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Bad Status",
                "remind_at": _future_iso(),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"status": "invalid_status"},
            headers=headers,
        )
        assert response.status_code == 422

    async def test_update_reschedule(self, client, create_test_session):
        """Change the remind_at time."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Reschedule Me",
                "remind_at": _future_iso(30),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]
        new_time = _future_iso(120)

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"remind_at": new_time},
            headers=headers,
        )
        assert response.status_code == 200

    async def test_update_both_status_and_time(self, client, create_test_session):
        """Update both status and remind_at simultaneously."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Both",
                "remind_at": _future_iso(30),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"status": "completed", "remind_at": _future_iso(120)},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    async def test_update_empty_body(self, client, create_test_session):
        """Empty update body → still 200 (no fields changed)."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "No Change",
                "remind_at": _future_iso(),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={},
            headers=headers,
        )
        assert response.status_code == 200

    async def test_update_nonexistent_reminder(self, client, create_test_session):
        """Non-existent reminder_id → 404."""
        sess = await create_test_session()
        response = await client.patch(
            f"/api/v1/tasks/reminders/{uuid.uuid4()}",
            json={"status": "completed"},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 404

    async def test_update_reminder_wrong_session(self, client, create_test_session):
        """Reminder belongs to session A, token is session B → 404."""
        sess_a = await create_test_session()
        sess_b = await create_test_session()

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess_a["session_id"]),
                "title": "A's Reminder",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess_a["session_token"]},
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"status": "completed"},
            headers={"X-Session-Token": sess_b["session_token"]},
        )
        assert response.status_code == 404

    async def test_update_no_auth(self, client):
        """No token → 401."""
        response = await client.patch(
            f"/api/v1/tasks/reminders/{uuid.uuid4()}",
            json={"status": "completed"},
        )
        assert response.status_code == 401


class TestDeleteReminder:
    """DELETE /api/v1/tasks/reminders/{reminder_id}"""

    async def test_delete_reminder_success(self, client, create_test_session):
        """Delete existing reminder → 200."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Delete Me",
                "remind_at": _future_iso(),
            },
            headers=headers,
        )
        rid = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/tasks/reminders/{rid}", headers=headers
        )
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    async def test_delete_reminder_removes_from_list(self, client, create_test_session):
        """After deletion, reminder should not appear in list."""
        sess = await create_test_session()
        headers = {"X-Session-Token": sess["session_token"]}
        sid = str(sess["session_id"])

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={"session_id": sid, "title": "Temporary", "remind_at": _future_iso()},
            headers=headers,
        )
        rid = create_resp.json()["id"]

        await client.delete(f"/api/v1/tasks/reminders/{rid}", headers=headers)

        list_resp = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": sid},
            headers=headers,
        )
        assert len(list_resp.json()["reminders"]) == 0

    async def test_delete_nonexistent_reminder(self, client, create_test_session):
        """Non-existent → 404."""
        sess = await create_test_session()
        response = await client.delete(
            f"/api/v1/tasks/reminders/{uuid.uuid4()}",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 404

    async def test_delete_reminder_wrong_session(self, client, create_test_session):
        """Reminder from session A, token from session B → 404."""
        sess_a = await create_test_session()
        sess_b = await create_test_session()

        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess_a["session_id"]),
                "title": "A's",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess_a["session_token"]},
        )
        rid = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/tasks/reminders/{rid}",
            headers={"X-Session-Token": sess_b["session_token"]},
        )
        assert response.status_code == 404

    async def test_delete_reminder_no_auth(self, client):
        """No token → 401."""
        response = await client.delete(
            f"/api/v1/tasks/reminders/{uuid.uuid4()}"
        )
        assert response.status_code == 401

    async def test_delete_reminder_invalid_uuid(self, client, create_test_session):
        """Invalid UUID → 422."""
        sess = await create_test_session()
        response = await client.delete(
            "/api/v1/tasks/reminders/not-a-uuid",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_delete_reminder_sql_injection_id(self, client, create_test_session):
        """SQL injection string in reminder_id path param → 422."""
        sess = await create_test_session()
        response = await client.delete(
            "/api/v1/tasks/reminders/' OR 1=1;--",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_delete_reminder_empty_token(self, client):
        """Empty string in X-Session-Token header → 401."""
        response = await client.delete(
            f"/api/v1/tasks/reminders/{uuid.uuid4()}",
            headers={"X-Session-Token": ""},
        )
        assert response.status_code == 401


class TestReminderInvalidDataPayloads:
    """Detailed invalid data scenarios for reminders API."""

    async def test_create_reminder_title_too_long(self, client, create_test_session):
        """Title exceeding 255 characters should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "R" * 256,
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_title", [123, True, ["reminder"], {"k": "v"}])
    async def test_create_reminder_invalid_title_types(self, client, create_test_session, bad_title):
        """Non-string title values should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": bad_title,
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_date", ["not-a-date", "2025-99-99", "tomorrow", "", "not-iso-string", {"date": "now"}])
    async def test_create_reminder_invalid_remind_at_formats(self, client, create_test_session, bad_date):
        """Non-ISO datetime string in remind_at should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Doctor Appointment",
                "remind_at": bad_date,
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_sid", ["not-a-uuid", "123", "' OR 1=1;--"])
    async def test_create_reminder_invalid_session_id(self, client, create_test_session, bad_sid):
        """Invalid session_id format in body should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": bad_sid,
                "title": "Meeting",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_create_reminder_malformed_json_body(self, client, create_test_session):
        """Malformed JSON payload should fail with 422."""
        sess = await create_test_session()
        response = await client.post(
            "/api/v1/tasks/reminders",
            content=b"{invalid payload",
            headers={
                "Content-Type": "application/json",
                "X-Session-Token": sess["session_token"],
            },
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_sid_query", ["not-a-uuid", "123", "' OR 1=1;--"])
    async def test_list_reminders_invalid_session_id_query_param(self, client, create_test_session, bad_sid_query):
        """Invalid session_id in query params should fail with 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/tasks/reminders",
            params={"session_id": bad_sid_query},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_status", ["done", "archived", "in_progress", "deleted", 123])
    async def test_update_reminder_invalid_status_enum(self, client, create_test_session, bad_status):
        """Status not in (pending, completed, cancelled) should fail with 422."""
        sess = await create_test_session()
        # Create a reminder first
        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Test",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"status": bad_status},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_time", ["invalid-date", "yesterday", "not-iso", {"dt": 1}])
    async def test_update_reminder_invalid_remind_at(self, client, create_test_session, bad_time):
        """Invalid remind_at datetime in PATCH should fail with 422."""
        sess = await create_test_session()
        create_resp = await client.post(
            "/api/v1/tasks/reminders",
            json={
                "session_id": str(sess["session_id"]),
                "title": "Test",
                "remind_at": _future_iso(),
            },
            headers={"X-Session-Token": sess["session_token"]},
        )
        rid = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/tasks/reminders/{rid}",
            json={"remind_at": bad_time},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_rid", ["not-a-uuid", "123", "' OR 1=1;--"])
    async def test_update_reminder_invalid_uuid_path(self, client, create_test_session, bad_rid):
        """Invalid reminder_id path param should fail with 422."""
        sess = await create_test_session()
        response = await client.patch(
            f"/api/v1/tasks/reminders/{bad_rid}",
            json={"status": "completed"},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

