"""Integration tests for GET /api/v1/movies/{movie_id}."""

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


async def test_get_movie_by_id_returns_200(monkeypatch, tmp_path):
    """GET /api/v1/movies/1 returns 200 with movie data and _links."""
    db_path = str(tmp_path / "movies_get.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies/1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "Inception"
    assert "genres" in body
    assert isinstance(body["genres"], list)
    assert len(body["genres"]) > 0


async def test_get_movie_has_required_links(monkeypatch, tmp_path):
    """GET /api/v1/movies/1 response has _links with self, update, delete, reviews."""
    db_path = str(tmp_path / "movies_get.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies/1")

    assert response.status_code == 200
    body = response.json()
    links = body["_links"]
    assert "self" in links
    assert "update" in links
    assert "delete" in links
    assert "reviews" in links


async def test_get_movie_not_found_returns_404(monkeypatch, tmp_path):
    """GET /api/v1/movies/999999 returns 404 with _links.list pointing to movies list."""
    db_path = str(tmp_path / "movies_get.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "_links" in body
    assert body["_links"]["list"]["href"] == "/api/v1/movies"


async def test_get_movie_genres_populated(monkeypatch, tmp_path):
    """GET /api/v1/movies/1 genres array contains GenreResponse objects with id, name, _links."""
    db_path = str(tmp_path / "movies_get.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies/1")

    assert response.status_code == 200
    body = response.json()
    for genre in body["genres"]:
        assert "id" in genre
        assert "name" in genre
        assert "_links" in genre
