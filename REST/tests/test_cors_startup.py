"""Tests for CORS middleware: wildcard rejection at config time, allow-listed origin
reflection, and non-allow-listed origin omission."""

import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET


def _env(monkeypatch, tmp_path, cors_origins="http://localhost:3000"):
    db_path = str(tmp_path / "cors_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", cors_origins)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")


def _fresh_app(monkeypatch, tmp_path, cors_origins="http://localhost:3000"):
    _env(monkeypatch, tmp_path, cors_origins=cors_origins)
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


def test_wildcard_cors_origin_rejected_at_config(monkeypatch, tmp_path):
    """Settings raises a validation error when CORS_ALLOWED_ORIGINS contains '*'."""
    from pydantic import ValidationError

    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path))
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    from app.config import Settings

    with pytest.raises((ValidationError, ValueError)):
        Settings(_env_file=None)


def test_cors_preflight_allow_listed_origin_reflected(monkeypatch, tmp_path):
    """OPTIONS preflight from an allow-listed origin returns Access-Control-Allow-Origin."""
    app, _ = _fresh_app(monkeypatch, tmp_path, cors_origins="http://localhost:3000")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.options(
            "/api/v1/movies",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_preflight_non_allow_listed_origin_omitted(monkeypatch, tmp_path):
    """OPTIONS preflight from a non-allow-listed origin omits Access-Control-Allow-Origin."""
    app, _ = _fresh_app(monkeypatch, tmp_path, cors_origins="http://localhost:3000")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.options(
            "/api/v1/movies",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
    assert "access-control-allow-origin" not in response.headers
