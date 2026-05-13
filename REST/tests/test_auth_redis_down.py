"""Tests for Redis-down failure mode: get_current_user must return 503, never 200."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import redis.exceptions
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET

SEED_SQL_PATH = str(Path(__file__).parent.parent.parent / "seed.sql")


def _env(monkeypatch, db_path):
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")


async def _seed_db(db_path, monkeypatch):
    _env(monkeypatch, db_path)
    from app.config import Settings
    from app.utils.db import init_db
    settings = Settings(_env_file=None)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)
    return settings


def _fresh_app_with_seeded_db(db_path, monkeypatch, redis_exists_side_effect=None):
    """Return a TestClient with pre-seeded DB and configurable Redis mock."""
    sys.modules.pop("app.main", None)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)

    if redis_exists_side_effect is not None:
        mock_redis.exists = AsyncMock(side_effect=redis_exists_side_effect)
    else:
        mock_redis.exists = AsyncMock(return_value=0)

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    async def mock_init_db(settings, seed_sql_path=None):
        pass

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):
        from app.main import app
        client = TestClient(app)
        return client, mock_redis


async def test_redis_connection_error_during_auth_returns_503(monkeypatch, tmp_path):
    """When Redis raises ConnectionError during denylist check, the response is 503."""
    db_path = str(tmp_path / "redis_down_test.db")
    await _seed_db(db_path, monkeypatch)

    # First, get a valid token with a working Redis
    client_ok, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)
    with client_ok:
        r = client_ok.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        assert r.status_code == 200
        access_token = r.json()["access_token"]
        refresh_token = r.json()["refresh_token"]

    # Now simulate Redis going down for the denylist check
    client_down, _ = _fresh_app_with_seeded_db(
        db_path,
        monkeypatch,
        redis_exists_side_effect=redis.exceptions.ConnectionError("Redis is down"),
    )

    with client_down:
        # Attempt to use the access token — Redis is down during denylist check
        response = client_down.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "service_unavailable"


async def test_redis_down_never_returns_200_with_valid_claims(monkeypatch, tmp_path):
    """Redis-down must never allow a protected endpoint to return 200."""
    db_path = str(tmp_path / "redis_down_test2.db")
    await _seed_db(db_path, monkeypatch)

    client_ok, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)
    with client_ok:
        r = client_ok.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        access_token = r.json()["access_token"]
        refresh_token = r.json()["refresh_token"]

    client_down, _ = _fresh_app_with_seeded_db(
        db_path,
        monkeypatch,
        redis_exists_side_effect=redis.exceptions.ConnectionError("Redis is down"),
    )

    with client_down:
        response = client_down.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    # Must not be 200 — fail loud
    assert response.status_code != 200
    assert response.status_code == 503
