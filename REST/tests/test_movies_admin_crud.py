"""Integration tests for admin-gated movie CRUD: POST, PUT, DELETE."""

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
        from fastapi.testclient import TestClient
        client = TestClient(app)
        return client, denylist


def _login(client, username="admin", password="admin123"):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()


async def test_post_movie_no_auth_returns_401(monkeypatch, tmp_path):
    """POST /api/v1/movies without auth returns 401."""
    db_path = str(tmp_path / "movies_crud.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.post(
            "/api/v1/movies",
            json={"title": "Test", "release_year": 2020, "genre_ids": []},
        )

    assert response.status_code == 401


async def test_post_movie_as_non_admin_returns_403(monkeypatch, tmp_path):
    """POST /api/v1/movies as tester (non-admin) returns 403 forbidden."""
    db_path = str(tmp_path / "movies_crud.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client, "tester", "tester123")
        response = client.post(
            "/api/v1/movies",
            json={"title": "Test", "release_year": 2020, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "forbidden"
    # 403 must not include _links per vision.md §4
    assert "_links" not in body


async def test_post_movie_as_admin_returns_201_with_location(monkeypatch, tmp_path):
    """POST /api/v1/movies as admin with valid body returns 201 with Location header."""
    db_path = str(tmp_path / "movies_crud.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        response = client.post(
            "/api/v1/movies",
            json={"title": "New Movie", "release_year": 2023, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 201
    assert "location" in response.headers
    location = response.headers["location"]
    assert location.startswith("/api/v1/movies/")
    body = response.json()
    assert body["title"] == "New Movie"
    assert body["release_year"] == 2023


async def test_put_movie_as_admin_returns_200_updated_at(monkeypatch, tmp_path):
    """PUT /api/v1/movies/{id} as admin returns 200; updated_at >= created_at."""
    db_path = str(tmp_path / "movies_crud.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        # Create a movie first
        create_resp = client.post(
            "/api/v1/movies",
            json={"title": "To Update", "release_year": 2020, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert create_resp.status_code == 201
        movie_id = create_resp.json()["id"]
        created_at = create_resp.json()["created_at"]

        # Update it
        update_resp = client.put(
            f"/api/v1/movies/{movie_id}",
            json={"title": "Updated Title", "release_year": 2021, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["title"] == "Updated Title"
    assert body["release_year"] == 2021
    # updated_at must be >= created_at
    assert body["updated_at"] >= created_at


async def test_delete_movie_as_admin_returns_204(monkeypatch, tmp_path):
    """DELETE /api/v1/movies/{id} as admin returns 204; subsequent GET returns 404."""
    db_path = str(tmp_path / "movies_crud.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        # Create a movie to delete
        create_resp = client.post(
            "/api/v1/movies",
            json={"title": "To Delete", "release_year": 2020, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert create_resp.status_code == 201
        movie_id = create_resp.json()["id"]

        # Delete it
        delete_resp = client.delete(
            f"/api/v1/movies/{movie_id}",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert delete_resp.status_code == 204

        # Subsequent GET must return 404
        get_resp = client.get(f"/api/v1/movies/{movie_id}")

    assert get_resp.status_code == 404


async def test_post_movie_with_revoked_token_returns_401(monkeypatch, tmp_path):
    """POST /api/v1/movies with a logged-out access token returns 401 token_revoked."""
    db_path = str(tmp_path / "movies_crud.db")
    await _seed_db(db_path, monkeypatch)
    client, _ = _fresh_app(db_path, monkeypatch)

    with client:
        tokens = _login(client)
        # Logout to revoke the token
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        # Try to use the revoked access token
        response = client.post(
            "/api/v1/movies",
            json={"title": "Test", "release_year": 2020, "genre_ids": []},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "token_revoked"
