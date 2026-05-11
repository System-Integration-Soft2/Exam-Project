"""Integration tests for POST /api/v1/auth/login."""

from __future__ import annotations

import sys
import time
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
    """Seed the test database with admin user."""
    _env(monkeypatch, db_path)
    from app.config import Settings
    from app.utils.db import init_db
    settings = Settings(_env_file=None)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)
    return settings


def _fresh_app_with_seeded_db(db_path, monkeypatch):
    """Return a TestClient backed by a pre-seeded DB and a mock Redis."""
    sys.modules.pop("app.main", None)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=0)
    mock_redis.set = AsyncMock(return_value=True)

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    async def mock_init_db(settings, seed_sql_path=None):
        pass  # DB already seeded; skip re-init in lifespan

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):
        from app.main import app
        client = TestClient(app)
        return client, mock_redis


async def test_login_happy_path(monkeypatch, tmp_path):
    """POST /api/v1/auth/login with valid credentials returns 200 with token pair."""
    db_path = str(tmp_path / "auth_login_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900


async def test_login_wrong_password_returns_401(monkeypatch, tmp_path):
    """POST /api/v1/auth/login with wrong password returns 401 unauthorized."""
    db_path = str(tmp_path / "auth_login_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "wrongpassword"},
        )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "unauthorized"


async def test_login_unknown_user_returns_401(monkeypatch, tmp_path):
    """POST /api/v1/auth/login with unknown username returns 401 unauthorized."""
    db_path = str(tmp_path / "auth_login_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nobody", "password": "whatever"},
        )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "unauthorized"


async def test_login_unknown_user_latency_within_envelope(monkeypatch, tmp_path):
    """Unknown-user login latency is within ±50ms of wrong-password latency (timing equalisation)."""
    db_path = str(tmp_path / "auth_login_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        # Warm up bcrypt (first call is slower due to module loading)
        client.post("/api/v1/auth/login", data={"username": "admin", "password": "wrong"})
        client.post("/api/v1/auth/login", data={"username": "nobody", "password": "whatever"})

        # Measure wrong-password latency (user exists, bcrypt runs)
        t0 = time.monotonic()
        client.post("/api/v1/auth/login", data={"username": "admin", "password": "wrong"})
        wrong_pw_latency = time.monotonic() - t0

        # Measure unknown-user latency (dummy bcrypt must run)
        t0 = time.monotonic()
        client.post("/api/v1/auth/login", data={"username": "nobody", "password": "whatever"})
        unknown_user_latency = time.monotonic() - t0

    # Both paths run bcrypt; latency should be within 50ms of each other
    diff = abs(unknown_user_latency - wrong_pw_latency)
    assert diff < 0.05, (
        f"Timing difference too large: wrong_pw={wrong_pw_latency:.3f}s, "
        f"unknown_user={unknown_user_latency:.3f}s, diff={diff:.3f}s"
    )


async def test_login_missing_password_returns_422(monkeypatch, tmp_path):
    """POST /api/v1/auth/login with missing password field returns 422 with errors[]."""
    db_path = str(tmp_path / "auth_login_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "admin"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body.get("errors"), list)
    assert len(body["errors"]) > 0


async def test_login_json_body_returns_422_or_415(monkeypatch, tmp_path):
    """POST /api/v1/auth/login with JSON body returns 422 (form required)."""
    db_path = str(tmp_path / "auth_login_test.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app_with_seeded_db(db_path, monkeypatch)

    with client:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )

    # FastAPI returns 422 when form data is expected but JSON is sent
    assert response.status_code in (415, 422)
