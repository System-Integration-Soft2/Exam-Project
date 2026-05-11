"""Integration tests for GET /api/v1/reviews (list, movie_id filter, pagination, get by id)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tests.conftest import TEST_JWT_SECRET

SEED_SQL_PATH = str(Path(__file__).parent.parent.parent / "seed.sql")


def _env(monkeypatch, db_path):
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")


async def _seed_db(db_path, monkeypatch):
    """Seed the DB with schema, movies, genres, and sample reviews via init_db."""
    _env(monkeypatch, db_path)
    from app.config import Settings
    from app.utils.db import init_db
    settings = Settings(_env_file=None)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)
    return settings


async def _add_extra_reviews(db_path):
    """Add 2 more reviews for movie_id=1 so it has 3 total (for filter/pagination tests)."""
    import aiosqlite
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        # init_db already inserted 1 review for movie_id=1 (admin user).
        # Add 2 more so movie_id=1 has 3 reviews total.
        await db.execute(
            "INSERT INTO reviews (movie_id, user_id, rating, comment) "
            "SELECT 1, id, 8, 'Extra review A' FROM users WHERE username = 'admin'"
        )
        await db.execute(
            "INSERT INTO reviews (movie_id, user_id, rating, comment) "
            "SELECT 1, id, 7, 'Extra review B' FROM users WHERE username = 'admin'"
        )
        await db.commit()


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


async def test_list_reviews_returns_seeded_envelope(monkeypatch, tmp_path):
    """GET /api/v1/reviews returns 200 with envelope: items, page, size, total, _links.
    init_db seeds 4 sample reviews; all are returned on the first page.
    """
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "page" in body
    assert "size" in body
    assert "total" in body
    assert "_links" in body
    assert isinstance(body["items"], list)
    assert body["total"] == 4
    assert len(body["items"]) == 4
    assert body["page"] == 1
    assert "self" in body["_links"]


async def test_list_reviews_movie_id_filter(monkeypatch, tmp_path):
    """GET /api/v1/reviews?movie_id=1 returns only reviews for movie 1."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    # init_db seeds 1 review for movie_id=1; add 2 more so we have 3 to filter
    await _add_extra_reviews(db_path)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews?movie_id=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    for item in body["items"]:
        assert item["movie_id"] == 1


async def test_list_reviews_movie_id_nonexistent_returns_empty(monkeypatch, tmp_path):
    """GET /api/v1/reviews?movie_id=999999 returns 200, total=0, items=[]."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews?movie_id=999999")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_list_reviews_movie_id_invalid_returns_422(monkeypatch, tmp_path):
    """GET /api/v1/reviews?movie_id=0 returns 422 (ge=1 enforced)."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews?movie_id=0")

    assert response.status_code == 422


async def test_list_reviews_pagination(monkeypatch, tmp_path):
    """GET /api/v1/reviews?size=2&page=1 returns 2 items, total reflects full count (4)."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews?size=2&page=1")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 4
    assert body["size"] == 2
    assert body["page"] == 1


async def test_list_reviews_size_999_clamped_to_100(monkeypatch, tmp_path):
    """GET /api/v1/reviews?size=999 returns 200 with envelope size == 100."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews?size=999")

    assert response.status_code == 200
    body = response.json()
    assert body["size"] == 100


async def test_get_review_returns_self_and_movie_links(monkeypatch, tmp_path):
    """GET /api/v1/reviews/{id} returns 200 with _links.self and _links.movie."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    # Fetch the first review to get its id and movie_id dynamically
    with client:
        list_response = client.get("/api/v1/reviews?size=1")
        assert list_response.status_code == 200
        first_item = list_response.json()["items"][0]
        review_id = first_item["id"]
        movie_id = first_item["movie_id"]

        response = client.get(f"/api/v1/reviews/{review_id}")

    assert response.status_code == 200
    body = response.json()
    assert "_links" in body
    assert "self" in body["_links"]
    assert "movie" in body["_links"]
    assert body["_links"]["self"]["href"] == f"/api/v1/reviews/{review_id}"
    assert body["_links"]["self"]["method"] == "GET"
    assert body["_links"]["movie"]["href"] == f"/api/v1/movies/{movie_id}"
    assert body["_links"]["movie"]["method"] == "GET"


async def test_get_review_nonexistent_returns_404_with_list_link(monkeypatch, tmp_path):
    """GET /api/v1/reviews/999999 returns 404 with _links.list == '/api/v1/reviews'."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        response = client.get("/api/v1/reviews/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "_links" in body
    assert "list" in body["_links"]
    assert body["_links"]["list"]["href"] == "/api/v1/reviews"


async def test_review_response_has_no_updated_at_field(monkeypatch, tmp_path):
    """GET /api/v1/reviews/{id} response does NOT contain 'updated_at' (table has no such column)."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        list_response = client.get("/api/v1/reviews?size=1")
        assert list_response.status_code == 200
        review_id = list_response.json()["items"][0]["id"]

        response = client.get(f"/api/v1/reviews/{review_id}")

    assert response.status_code == 200
    body = response.json()
    assert "updated_at" not in body


async def test_list_reviews_filter_preserved_in_pagination_links(monkeypatch, tmp_path):
    """GET /api/v1/reviews?movie_id=1&size=1 — _links.next URL contains movie_id=1."""
    db_path = str(tmp_path / "reviews.db")
    await _seed_db(db_path, monkeypatch)
    # Add extra reviews for movie_id=1 so total > 1 and pagination links are generated
    await _add_extra_reviews(db_path)
    client = _fresh_app(db_path, monkeypatch)

    with client:
        # movie_id=1 now has 3 reviews; size=1 means there will be a next page
        response = client.get("/api/v1/reviews?movie_id=1&size=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert "next" in body["_links"], "Expected _links.next when total > size"
    next_href = body["_links"]["next"]["href"]
    assert "movie_id=1" in next_href, f"movie_id filter not preserved in next link: {next_href}"
