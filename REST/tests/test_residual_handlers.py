"""Tests for residual exception handlers: HTTPException dispatcher (404/405/415)
and generic Exception handler (500 with logged traceback)."""

import logging
import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET


def _env(monkeypatch, tmp_path):
    db_path = str(tmp_path / "residual_test.db")
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


def test_method_not_allowed_returns_structured_envelope(monkeypatch, tmp_path):
    """POST on a GET-only path returns 405 with code=method_not_allowed envelope."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        # /api/v1/genres/{id} only supports GET
        response = client.post("/api/v1/genres/1")
    assert response.status_code == 405
    body = response.json()
    assert body["code"] == "method_not_allowed"
    assert "detail" in body


def test_not_found_returns_structured_envelope_with_links(monkeypatch, tmp_path):
    """GET on an unknown path returns 404 with code=not_found and _links.list."""
    app, _ = _fresh_app(monkeypatch, tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/notathing")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "detail" in body
    assert "_links" in body
    assert "list" in body["_links"]


def test_unsupported_media_type_returns_structured_envelope(monkeypatch, tmp_path):
    """HTTPException(415) is converted to the structured envelope.

    FastAPI does not raise 415 natively for wrong content-type on form endpoints
    (it returns 422 instead). We verify the handler via a synthetic route that
    explicitly raises HTTPException(415), which is the realistic trigger path
    (e.g. a future endpoint that enforces its own media-type check).
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app, _ = _fresh_app(monkeypatch, tmp_path)

    @app.post("/__test_415")
    async def _raise_415():
        raise StarletteHTTPException(status_code=415, detail="Unsupported Media Type")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/__test_415")
    assert response.status_code == 415
    body = response.json()
    assert body["code"] == "unsupported_media_type"
    assert "detail" in body


def test_unhandled_exception_returns_500_without_traceback(monkeypatch, tmp_path, caplog):
    """An unhandled RuntimeError returns 500 with sanitised body; traceback is logged."""
    app, _ = _fresh_app(monkeypatch, tmp_path)

    # Register a test route that raises RuntimeError
    @app.get("/__test_boom")
    async def _boom():
        raise RuntimeError("boom")

    with caplog.at_level(logging.ERROR):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/__test_boom")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["detail"] == "Internal server error"
    # Traceback text must NOT leak into the response body
    assert "boom" not in response.text
    assert "RuntimeError" not in response.text
    # But the traceback MUST appear in the logs
    assert "boom" in caplog.text or "RuntimeError" in caplog.text
