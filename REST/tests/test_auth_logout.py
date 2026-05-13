"""Integration tests for POST /api/v1/auth/logout: denylist both jtis, reuse prevention."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
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


def _fresh_app_with_seeded_db(db_path, monkeypatch):
    """Return a TestClient backed by a pre-seeded DB and a simulated Redis denylist."""
    sys.modules.pop("app.main", None)

    denylist: dict[str, str] = {}

    async def mock_set(key, value, ex=None, nx=False):
        if nx and key in denylist:
            return None
        denylist[key] = value
        return True

    async def mock_exists(key):
        return 1 if key in denylist else 0

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis.set = AsyncMock(side_effect=mock_set)
    mock_redis.exists = AsyncMock(side_effect=mock_exists)

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
        return client, mock_redis, denylist


def _login(client):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()


async def test_logout_returns_204(monkeypatch, tmp_path):
    """POST /api/v1/auth/logout with valid tokens returns 204 No Content."""
    db_path = str(tmp_path / "auth_logout_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 204


async def test_logout_both_jtis_denylisted(monkeypatch, tmp_path):
    """After logout, both access and refresh jtis are in the denylist."""
    import jwt as pyjwt
    from app.utils.redis_client import denylist_key

    db_path = str(tmp_path / "auth_logout_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, denylist = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        access_payload = pyjwt.decode(
            tokens["access_token"], TEST_JWT_SECRET, algorithms=["HS256"],
            audience="rest-api",
        )
        refresh_payload = pyjwt.decode(
            tokens["refresh_token"], TEST_JWT_SECRET, algorithms=["HS256"],
            audience="rest-api",
        )

        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    access_key = denylist_key(access_payload["jti"])
    refresh_key = denylist_key(refresh_payload["jti"])
    assert access_key in denylist, "Access token jti not in denylist after logout"
    assert refresh_key in denylist, "Refresh token jti not in denylist after logout"


async def test_logout_access_token_reuse_returns_401(monkeypatch, tmp_path):
    """Using the access token after logout returns 401 token_revoked."""
    db_path = str(tmp_path / "auth_logout_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        # Logout
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Try to use the access token again
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "token_revoked"


async def test_logout_refresh_token_reuse_returns_401(monkeypatch, tmp_path):
    """Using the refresh token after logout returns 401 token_revoked."""
    db_path = str(tmp_path / "auth_logout_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        # Logout
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Try to use the refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "token_revoked"
