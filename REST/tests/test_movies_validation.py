"""Integration tests for movie request body validation (Pydantic and service-layer)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

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


def _fresh_app(db_path, monkeypatch):
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
        pass

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        return client


def _login(client, username="admin", password="admin123"):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()


async def test_post_movie_invalid_release_year_returns_422_with_errors(monkeypatch, tmp_path):
    """POST /api/v1/movies with release_year=1500 returns 422 with errors[] (Pydantic)."""
    db_path = str(tmp_path / "movies_validation.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/movies",
            json={"title": "Old Movie", "release_year": 1500, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body.get("errors"), list)
    assert len(body["errors"]) > 0


async def test_post_movie_nonexistent_genre_ids_returns_422_no_errors(monkeypatch, tmp_path):
    """POST /api/v1/movies with genre_ids=[9999] returns 422 with errors=None (service-layer)."""
    db_path = str(tmp_path / "movies_validation.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/movies",
            json={"title": "Test Movie", "release_year": 2020, "genre_ids": [9999]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    # Service-layer path: errors is None (not populated by Pydantic)
    assert body.get("errors") is None


async def test_post_movie_missing_required_field_returns_422_with_errors(monkeypatch, tmp_path):
    """POST /api/v1/movies with missing title returns 422 with errors[] (Pydantic)."""
    db_path = str(tmp_path / "movies_validation.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/movies",
            json={"release_year": 2020, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body.get("errors"), list)
    assert len(body["errors"]) > 0
