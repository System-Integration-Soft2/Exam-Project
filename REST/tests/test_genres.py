"""Integration tests for GET /api/v1/genres (list, search, pagination, get by id)."""

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


async def test_list_genres_returns_envelope_with_5_seeded(monkeypatch, tmp_path):
    """GET /api/v1/genres returns 200 with envelope: items (5 genres), page, size, total, _links."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "page" in body
    assert "size" in body
    assert "total" in body
    assert "_links" in body
    assert isinstance(body["items"], list)
    assert body["total"] == 5
    assert len(body["items"]) == 5
    assert body["page"] == 1
    assert body["size"] == 20
    assert "self" in body["_links"]


async def test_each_genre_item_has_self_link(monkeypatch, tmp_path):
    """Every genre item in the list response has _links.self pointing at /api/v1/genres/{id}."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres")

    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert "_links" in item
        assert "self" in item["_links"]
        genre_id = item["id"]
        assert item["_links"]["self"]["href"] == f"/api/v1/genres/{genre_id}"
        assert item["_links"]["self"]["method"] == "GET"


async def test_list_genres_q_filters_case_insensitive(monkeypatch, tmp_path):
    """GET /api/v1/genres?q=action returns only the Action genre."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres?q=action")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Action"


async def test_list_genres_q_nope_returns_empty_with_no_first_last(monkeypatch, tmp_path):
    """GET /api/v1/genres?q=zzzzzz returns total=0, items=[], no _links.first or _links.last."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres?q=zzzzzz")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    links = body["_links"]
    assert "self" in links
    assert "first" not in links
    assert "last" not in links


async def test_list_genres_size_999_clamped_to_100(monkeypatch, tmp_path):
    """GET /api/v1/genres?size=999 returns 200 with envelope size == 100."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres?size=999")

    assert response.status_code == 200
    body = response.json()
    assert body["size"] == 100


async def test_list_genres_size_0_returns_422(monkeypatch, tmp_path):
    """GET /api/v1/genres?size=0 returns 422 (Query ge=1 validation)."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres?size=0")

    assert response.status_code == 422


async def test_get_genre_by_id_returns_self_link(monkeypatch, tmp_path):
    """GET /api/v1/genres/1 returns 200 with id, name, and _links.self."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres/1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 1
    assert "name" in body
    assert "_links" in body
    assert "self" in body["_links"]
    assert body["_links"]["self"]["href"] == "/api/v1/genres/1"
    assert body["_links"]["self"]["method"] == "GET"


async def test_get_genre_nonexistent_returns_404_with_list_link(monkeypatch, tmp_path):
    """GET /api/v1/genres/999999 returns 404 with _links.list == '/api/v1/genres'."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/genres/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "_links" in body
    assert "list" in body["_links"]
    assert body["_links"]["list"]["href"] == "/api/v1/genres"


async def test_list_genres_q_sql_injection_probe(monkeypatch, tmp_path):
    """SQLi probe in q returns 200; subsequent list still returns the seeded genres."""
    db_path = str(tmp_path / "genres.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        sqli = "'; DROP TABLE genres;--"
        response = client.get(f"/api/v1/genres", params={"q": sqli})
        assert response.status_code == 200

        # Genres table must still be intact
        response2 = client.get("/api/v1/genres")
        assert response2.status_code == 200
        body2 = response2.json()
        assert body2["total"] == 5
