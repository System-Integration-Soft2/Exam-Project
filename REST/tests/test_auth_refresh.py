"""Integration tests for POST /api/v1/auth/refresh: rotation, denylist, reuse prevention."""

from __future__ import annotations

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
    from app.utils.config import Settings
    from app.utils.db import init_db
    settings = Settings(_env_file=None)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)
    return settings


def _fresh_app_with_seeded_db(db_path, monkeypatch):
    """Return a TestClient backed by a pre-seeded DB and a simulated Redis denylist."""
    sys.modules.pop("app.main", None)

    # Use a real in-memory dict to simulate Redis denylist behaviour
    denylist: dict[str, str] = {}

    async def mock_set(key, value, ex=None, nx=False):
        if nx and key in denylist:
            return None  # NX: key already exists, don't set
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
    """Helper: log in as admin and return the token pair."""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()


async def test_refresh_issues_new_pair(monkeypatch, tmp_path):
    """POST /api/v1/auth/refresh with valid refresh token returns a new token pair."""
    db_path = str(tmp_path / "auth_refresh_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    # New tokens should be different from old ones
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


async def test_refresh_old_jti_is_denylisted(monkeypatch, tmp_path):
    """After refresh, the old refresh token's jti is in the denylist."""
    import jwt as pyjwt
    from app.utils.redis_client import denylist_key

    db_path = str(tmp_path / "auth_refresh_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, denylist = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        old_refresh = tokens["refresh_token"]

        old_payload = pyjwt.decode(
            old_refresh,
            TEST_JWT_SECRET,
            algorithms=["HS256"],
        )
        old_jti = old_payload["jti"]

        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )

    assert denylist_key(old_jti) in denylist, "Old jti should be in denylist after rotation"


async def test_refresh_reuse_of_rotated_token_returns_401(monkeypatch, tmp_path):
    """Reusing a rotated-away refresh token returns 401 token_revoked."""
    db_path = str(tmp_path / "auth_refresh_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        old_refresh = tokens["refresh_token"]

        # First refresh succeeds
        r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert r1.status_code == 200

        # Reusing the old refresh token must fail
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

    assert r2.status_code == 401
    assert r2.json()["code"] == "token_revoked"


async def test_refresh_with_access_token_returns_401(monkeypatch, tmp_path):
    """Sending an access token to /refresh returns 401 (wrong token type)."""
    db_path = str(tmp_path / "auth_refresh_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_refresh_concurrent_second_call_loses(monkeypatch, tmp_path):
    """Concurrent refresh: second call with same token gets 401 token_revoked."""
    db_path = str(tmp_path / "auth_refresh_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        refresh_token = tokens["refresh_token"]

        # First call succeeds
        r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert r1.status_code == 200

        # Second call with same token (simulates concurrent loser)
        r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert r2.status_code == 401
    assert r2.json()["code"] == "token_revoked"
