"""Integration tests for GET /api/v1/movies (list, search, pagination)."""

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
        pass

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        return client


async def test_list_movies_happy_path(monkeypatch, tmp_path):
    """GET /api/v1/movies returns 200 with envelope: items, page, size, total, _links."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "page" in body
    assert "size" in body
    assert "total" in body
    assert "_links" in body
    assert isinstance(body["items"], list)
    assert len(body["items"]) > 0
    assert body["page"] == 1
    assert body["total"] >= 10  # 10 seeded movies


async def test_list_movies_size_zero_returns_422(monkeypatch, tmp_path):
    """GET /api/v1/movies?size=0 returns 422 with errors[] populated (Query ge=1)."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies?size=0")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert isinstance(body.get("errors"), list)
    assert len(body["errors"]) > 0


async def test_list_movies_size_negative_returns_422(monkeypatch, tmp_path):
    """GET /api/v1/movies?size=-1 returns 422."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies?size=-1")

    assert response.status_code == 422


async def test_list_movies_size_clamped_to_100(monkeypatch, tmp_path):
    """GET /api/v1/movies?size=999 returns 200 with response.size == 100 (upper clamp)."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies?size=999")

    assert response.status_code == 200
    body = response.json()
    assert body["size"] == 100


async def test_list_movies_search_case_insensitive(monkeypatch, tmp_path):
    """GET /api/v1/movies?q=incep returns Inception (case-insensitive LIKE)."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies?q=incep")

    assert response.status_code == 200
    body = response.json()
    titles = [item["title"] for item in body["items"]]
    assert "Inception" in titles


async def test_list_movies_sqli_probe(monkeypatch, tmp_path):
    """SQLi probe in q returns 200 with empty/non-matching results; subsequent list still works."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        # SQLi probe — parameterised queries must prevent any injection
        sqli = "'; DROP TABLE movies;--"
        response = client.get(f"/api/v1/movies?q={sqli}")
        assert response.status_code == 200

        # Subsequent list must still return the full seeded set
        response2 = client.get("/api/v1/movies")
        assert response2.status_code == 200
        body2 = response2.json()
        assert body2["total"] >= 10


async def test_list_movies_percent_in_q(monkeypatch, tmp_path):
    """GET /api/v1/movies?q=50% returns 200 — literal % is escaped, no SQL error."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies", params={"q": "50%"})

    assert response.status_code == 200
    body = response.json()
    assert "items" in body


async def test_list_movies_items_have_genres(monkeypatch, tmp_path):
    """Each movie item in the list response includes a genres array."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies")

    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert "genres" in item
        assert isinstance(item["genres"], list)


async def test_list_movies_items_have_links(monkeypatch, tmp_path):
    """Each movie item in the list response includes _links.self."""
    db_path = str(tmp_path / "movies_list.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/movies")

    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert "_links" in item
        assert "self" in item["_links"]
