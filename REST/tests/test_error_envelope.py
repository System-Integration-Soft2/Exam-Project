"""Tests for the structured error envelope: AppError handler, 404 _links, 401 _links, validation errors."""

import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET


def _env(monkeypatch, tmp_path):
    db_path = str(tmp_path / "envelope_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")


def _fresh_app(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    sys.modules.pop("app.main", None)

    async def mock_init_db(settings, seed_sql_path=None):
        pass

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):
        from app.main import app
        return app, mock_redis


def test_app_error_produces_correct_envelope(monkeypatch, tmp_path):
    """AppError raised in a route produces {detail, code} envelope."""
    from app.utils.exceptions import AppError

    app, _ = _fresh_app(monkeypatch, tmp_path)

    @app.get("/test-app-error")
    async def _raise():
        raise AppError("not_found", "Resource not found", 404)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-app-error")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "detail" in body


def test_app_error_without_links_has_no_links_key(monkeypatch, tmp_path):
    """AppError without links produces envelope without _links key."""
    from app.utils.exceptions import AppError

    app, _ = _fresh_app(monkeypatch, tmp_path)

    @app.get("/test-no-links")
    async def _raise():
        raise AppError("forbidden", "Forbidden", 403)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-no-links")

    body = response.json()
    assert "_links" not in body


def test_404_on_auth_path_has_links_list(monkeypatch, tmp_path):
    """A 404 AppError on /api/v1/auth/nonexistent includes _links.list = /api/v1/auth."""
    from app.utils.exceptions import AppError

    app, _ = _fresh_app(monkeypatch, tmp_path)

    @app.get("/api/v1/auth/nonexistent")
    async def _raise():
        raise AppError("not_found", "Not found", 404)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/auth/nonexistent")

    body = response.json()
    assert response.status_code == 404
    assert "_links" in body
    assert "list" in body["_links"]
    assert body["_links"]["list"]["href"] == "/api/v1/auth"


def test_401_has_links_login(monkeypatch, tmp_path):
    """A 401 AppError includes _links.login pointing to /api/v1/auth/login."""
    from app.utils.exceptions import AppError

    app, _ = _fresh_app(monkeypatch, tmp_path)

    @app.get("/test-401")
    async def _raise():
        raise AppError("unauthorized", "Unauthorized", 401)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-401")

    body = response.json()
    assert response.status_code == 401
    assert "_links" in body
    assert "login" in body["_links"]
    assert body["_links"]["login"]["href"] == "/api/v1/auth/login"


def test_request_validation_error_has_errors_populated(monkeypatch, tmp_path):
    """RequestValidationError produces envelope with errors[] populated."""
    from pydantic import BaseModel

    app, _ = _fresh_app(monkeypatch, tmp_path)

    class Body(BaseModel):
        name: str
        age: int

    @app.post("/test-validation")
    async def _endpoint(body: Body):
        return body

    with TestClient(app, raise_server_exceptions=False) as client:
        # Send invalid body (age is not an int)
        response = client.post("/test-validation", json={"name": "Alice", "age": "notanint"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "errors" in body
    assert isinstance(body["errors"], list)
    assert len(body["errors"]) > 0


def test_service_layer_422_leaves_errors_none(monkeypatch, tmp_path):
    """AppError raised by service layer (not Pydantic) has no errors field."""
    from app.utils.exceptions import AppError

    app, _ = _fresh_app(monkeypatch, tmp_path)

    @app.post("/test-service-error")
    async def _raise():
        raise AppError("validation_error", "Invalid genre_ids", 422)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/test-service-error", json={})

    body = response.json()
    assert response.status_code == 422
    # errors key should be absent or None
    assert body.get("errors") is None
