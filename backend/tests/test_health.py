"""
Tests for the Health endpoint: GET /api/v1/health
"""

import pytest


class TestHealthCheck:
    """GET /api/v1/health — no auth required."""

    async def test_returns_200_with_status_ok(self, client):
        """Happy-path: endpoint is reachable and returns expected shape."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "name" in data

    async def test_response_contains_app_name(self, client):
        """The name field should be the configured APP_NAME."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert isinstance(data["name"], str)
        assert len(data["name"]) > 0

    async def test_response_contains_version_string(self, client):
        """Version should be a non-empty string (semver-like)."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert isinstance(data["version"], str)
        assert "." in data["version"]  # e.g. "0.1.0"

    async def test_head_request_not_allowed(self, client):
        """HEAD is not explicitly defined on GET route — returns 405 or 200."""
        response = await client.head("/api/v1/health")
        assert response.status_code in (200, 405)

    async def test_post_method_not_allowed(self, client):
        """POST to /health should return 405."""
        response = await client.post("/api/v1/health")
        assert response.status_code == 405

    async def test_put_method_not_allowed(self, client):
        """PUT to /health should return 405."""
        response = await client.put("/api/v1/health")
        assert response.status_code == 405

    async def test_delete_method_not_allowed(self, client):
        """DELETE to /health should return 405."""
        response = await client.delete("/api/v1/health")
        assert response.status_code == 405
