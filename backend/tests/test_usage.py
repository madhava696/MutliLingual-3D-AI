"""
Tests for Usage endpoint:
  GET /api/v1/usage?session_id=  — aggregated cost/usage data (requires X-Session-Token)
"""

import uuid

import pytest


class TestGetUsage:
    """GET /api/v1/usage?session_id=..."""

    async def test_usage_empty_session(self, client, create_test_session):
        """Session with no usage logs → zeroed totals and empty breakdowns."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sess["session_id"])},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_cost_usd"] == 0
        assert data["total_requests"] == 0
        assert data["by_provider"] == []
        assert data["by_task"] == []

    async def test_usage_with_logs(
        self, client, create_test_session, create_test_usage_log
    ):
        """Session with usage logs returns aggregated data."""
        sess = await create_test_session()
        sid = sess["session_id"]

        # Create two usage logs
        await create_test_usage_log(
            sid, provider="gemini", task_type="chat", estimated_cost_usd=0.001
        )
        await create_test_usage_log(
            sid, provider="gemini", task_type="research", estimated_cost_usd=0.005
        )

        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sid)},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 2
        assert data["total_cost_usd"] == pytest.approx(0.006, abs=1e-6)

    async def test_usage_by_provider_aggregation(
        self, client, create_test_session, create_test_usage_log
    ):
        """by_provider should group correctly."""
        sess = await create_test_session()
        sid = sess["session_id"]

        await create_test_usage_log(sid, provider="gemini", estimated_cost_usd=0.01)
        await create_test_usage_log(sid, provider="gemini", estimated_cost_usd=0.02)
        await create_test_usage_log(sid, provider="openai", estimated_cost_usd=0.05)

        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sid)},
            headers={"X-Session-Token": sess["session_token"]},
        )
        data = response.json()
        providers = {p["provider"]: p for p in data["by_provider"]}

        assert "gemini" in providers
        assert providers["gemini"]["total_requests"] == 2
        assert providers["gemini"]["total_cost_usd"] == pytest.approx(0.03, abs=1e-6)

        assert "openai" in providers
        assert providers["openai"]["total_requests"] == 1
        assert providers["openai"]["total_cost_usd"] == pytest.approx(0.05, abs=1e-6)

    async def test_usage_by_task_aggregation(
        self, client, create_test_session, create_test_usage_log
    ):
        """by_task should group by task_type."""
        sess = await create_test_session()
        sid = sess["session_id"]

        await create_test_usage_log(sid, task_type="chat", estimated_cost_usd=0.001)
        await create_test_usage_log(sid, task_type="chat", estimated_cost_usd=0.002)
        await create_test_usage_log(sid, task_type="tts", estimated_cost_usd=0.003)

        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sid)},
            headers={"X-Session-Token": sess["session_token"]},
        )
        data = response.json()
        tasks = {t["task_type"]: t for t in data["by_task"]}

        assert "chat" in tasks
        assert tasks["chat"]["total_requests"] == 2
        assert tasks["chat"]["total_cost_usd"] == pytest.approx(0.003, abs=1e-6)

        assert "tts" in tasks
        assert tasks["tts"]["total_requests"] == 1

    async def test_usage_missing_session_id(self, client, create_test_session):
        """Missing query param → 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_usage_session_id_mismatch(self, client, create_test_session):
        """session_id != authenticated session → 403."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(uuid.uuid4())},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 403

    async def test_usage_no_auth(self, client):
        """No token → 401."""
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(uuid.uuid4())},
        )
        assert response.status_code == 401

    async def test_usage_invalid_token(self, client):
        """Invalid token → 401."""
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(uuid.uuid4())},
            headers={"X-Session-Token": "invalid"},
        )
        assert response.status_code == 401

    async def test_usage_isolation(
        self, client, create_test_session, create_test_usage_log
    ):
        """Usage from session A should not appear in session B's response."""
        sess_a = await create_test_session()
        sess_b = await create_test_session()

        await create_test_usage_log(sess_a["session_id"], estimated_cost_usd=0.1)

        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sess_b["session_id"])},
            headers={"X-Session-Token": sess_b["session_token"]},
        )
        data = response.json()
        assert data["total_cost_usd"] == 0
        assert data["total_requests"] == 0

    async def test_usage_response_schema(
        self, client, create_test_session, create_test_usage_log
    ):
        """Verify complete response shape."""
        sess = await create_test_session()
        sid = sess["session_id"]
        await create_test_usage_log(sid)

        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sid)},
            headers={"X-Session-Token": sess["session_token"]},
        )
        data = response.json()
        assert "total_cost_usd" in data
        assert "total_requests" in data
        assert "by_provider" in data
        assert "by_task" in data
        assert isinstance(data["by_provider"], list)
        assert isinstance(data["by_task"], list)

        if data["by_provider"]:
            prov = data["by_provider"][0]
            assert "provider" in prov
            assert "total_cost_usd" in prov
            assert "total_requests" in prov

        if data["by_task"]:
            task = data["by_task"][0]
            assert "task_type" in task
            assert "total_cost_usd" in task
            assert "total_requests" in task


class TestUsageInvalidDataScenarios:
    """Invalid data and error handling tests for GET /api/v1/usage."""

    @pytest.mark.parametrize("bad_sid", ["not-a-uuid", "123", "' OR 1=1;--", "   ", "xyz-123"])
    async def test_usage_invalid_session_id_query_param(self, client, create_test_session, bad_sid):
        """Invalid session_id in query params should trigger 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": bad_sid},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_usage_empty_session_id_query_param(self, client, create_test_session):
        """Empty session_id query param should trigger 422."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage?session_id=",
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 422

    async def test_usage_empty_token_header(self, client, create_test_session):
        """Empty string in X-Session-Token header should return 401."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sess["session_id"])},
            headers={"X-Session-Token": ""},
        )
        assert response.status_code == 401

    async def test_usage_whitespace_token_header(self, client, create_test_session):
        """Whitespace in X-Session-Token header should return 401."""
        sess = await create_test_session()
        response = await client.get(
            "/api/v1/usage",
            params={"session_id": str(sess["session_id"])},
            headers={"X-Session-Token": "    "},
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("bad_method", ["post", "put", "delete", "patch"])
    async def test_usage_invalid_http_methods(self, client, create_test_session, bad_method):
        """Non-GET methods on /usage should return 405 Method Not Allowed."""
        sess = await create_test_session()
        method_caller = getattr(client, bad_method)
        response = await method_caller(
            "/api/v1/usage",
            params={"session_id": str(sess["session_id"])},
            headers={"X-Session-Token": sess["session_token"]},
        )
        assert response.status_code == 405

