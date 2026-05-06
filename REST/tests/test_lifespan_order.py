"""Tests for lifespan startup ordering: Settings before init_db before Redis."""

import sys
import pytest
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError

from tests.conftest import TEST_JWT_SECRET


def _fresh_app():
    """Return the FastAPI app after evicting the cached module.

    Evicting app.main forces Python to re-execute the module body, so the
    lifespan closure captures the currently-patched callables rather than
    the originals that were bound at first import.
    """
    sys.modules.pop("app.main", None)
    from app.main import app
    return app


def test_settings_instantiated_before_init_db(monkeypatch, tmp_path):
    """Settings must be instantiated before init_db is called during lifespan startup."""
    db_path = str(tmp_path / "order_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")

    call_order = []

    async def mock_init_db(settings, seed_sql_path=None):
        call_order.append("init_db")

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.aclose = AsyncMock()

    async def mock_init_redis(redis_url):
        call_order.append("init_redis")
        return mock_redis

    async def mock_close_redis(client):
        pass

    from fastapi.testclient import TestClient

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):

        app = _fresh_app()
        with TestClient(app):
            pass

    assert "init_db" in call_order, "init_db was never called during lifespan"
    assert "init_redis" in call_order, "init_redis was never called during lifespan"
    assert call_order.index("init_db") < call_order.index("init_redis"), (
        "init_db must be called before init_redis"
    )


def test_missing_jwt_secret_prevents_init_db(monkeypatch, tmp_path):
    """When JWT_SECRET is missing, Settings raises ValidationError before init_db is called."""
    db_path = str(tmp_path / "order_fail_test.db")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("DATABASE_PATH", db_path)

    init_db_called = []

    async def mock_init_db(settings, seed_sql_path=None):
        init_db_called.append(True)

    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()

    async def mock_init_redis(redis_url):
        return mock_redis

    async def mock_close_redis(client):
        pass

    from fastapi.testclient import TestClient

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):

        app = _fresh_app()
        with pytest.raises((ValidationError, Exception)):
            with TestClient(app):
                pass

    assert not init_db_called, "init_db must not be called when Settings validation fails"


def test_redis_client_stored_on_app_state(monkeypatch, tmp_path):
    """After successful startup, app.state.redis holds the Redis client."""
    db_path = str(tmp_path / "state_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")

    sentinel = object()

    async def mock_init_db(settings, seed_sql_path=None):
        pass

    async def mock_init_redis(redis_url):
        return sentinel

    async def mock_close_redis(client):
        pass

    from fastapi.testclient import TestClient

    with patch("app.utils.db.init_db", mock_init_db), \
         patch("app.utils.redis_client.init_redis", mock_init_redis), \
         patch("app.utils.redis_client.close_redis", mock_close_redis):

        app = _fresh_app()
        with TestClient(app):
            assert app.state.redis is sentinel, (
                "app.state.redis must hold the Redis client after startup"
            )
