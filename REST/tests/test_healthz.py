"""Tests for the /healthz endpoint: healthy path and degraded-dependency paths."""

import sys
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET


def _env(monkeypatch, tmp_path):
    """Set a minimal valid environment pointing at a temp database."""
    db_path = str(tmp_path / "healthz_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")
    return db_path


def _fresh_app():
    """Return the FastAPI app, reloading app.main so lifespan picks up current patches."""
    # Drop cached module so the lifespan closure re-binds to the patched callables.
    sys.modules.pop("app.main", None)
    from app.main import app
    return app


def test_healthz_ok(monkeypatch, tmp_path):
    """GET /healthz returns 200 with {"db": "ok", "redis": "ok"} when both dependencies are healthy."""
    _env(monkeypatch, tmp_path)

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

        app = _fresh_app()
        with TestClient(app) as client:
            response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"db": "ok", "redis": "ok"}


def test_healthz_redis_down_returns_503(monkeypatch, tmp_path):
    """GET /healthz returns 503 when Redis ping raises a ConnectionError."""
    import redis.exceptions

    _env(monkeypatch, tmp_path)

    async def mock_init_db(settings, seed_sql_path=None):
        pass

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(side_effect=redis.exceptions.ConnectionError("Redis down"))
    mock_redis.aclose = AsyncMock()

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):

        app = _fresh_app()
        with TestClient(app) as client:
            response = client.get("/healthz")

    assert response.status_code == 503


def test_healthz_db_error_returns_503(monkeypatch, tmp_path):
    """GET /healthz returns 503 when the database connection raises an exception."""
    _env(monkeypatch, tmp_path)

    async def mock_init_db(settings, seed_sql_path=None):
        pass

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    async def mock_get_db_connection(db_path):
        raise Exception("DB unavailable")

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis), \
         patch("app.utils.db.get_db_connection", mock_get_db_connection):

        app = _fresh_app()
        with TestClient(app) as client:
            response = client.get("/healthz")

    assert response.status_code == 503
