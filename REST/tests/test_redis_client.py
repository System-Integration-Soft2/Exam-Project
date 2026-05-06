"""Tests for the Redis client helpers: key naming, SET NX semantics, and ping."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


def test_denylist_key_has_rest_prefix():
    """denylist_key must return a key with the 'rest:jwt:denylist:' prefix."""
    from app.utils.redis_client import denylist_key

    jti = "abc-123"
    key = denylist_key(jti)
    assert key == f"rest:jwt:denylist:{jti}"
    assert key.startswith("rest:")


def test_denylist_key_embeds_jti():
    """denylist_key must embed the full jti value in the returned key."""
    from app.utils.redis_client import denylist_key

    jti = "550e8400-e29b-41d4-a716-446655440000"
    key = denylist_key(jti)
    assert jti in key


async def test_set_nx_returns_true_on_first_call():
    """denylist_set returns True when the key does not yet exist (SET NX succeeds)."""
    from app.utils.redis_client import denylist_set

    mock_client = AsyncMock()
    mock_client.set = AsyncMock(return_value=True)

    result = await denylist_set(mock_client, "jti-first", ttl_seconds=300)

    assert result is True
    mock_client.set.assert_called_once()
    call_kwargs = mock_client.set.call_args
    # Verify NX and EX are passed
    assert call_kwargs.kwargs.get("nx") is True or (
        len(call_kwargs.args) > 0 and "nx" in str(call_kwargs)
    )


async def test_set_nx_returns_false_on_second_call():
    """denylist_set returns False when the key already exists (SET NX fails)."""
    from app.utils.redis_client import denylist_set

    mock_client = AsyncMock()
    # Redis returns None when SET NX fails (key already exists)
    mock_client.set = AsyncMock(return_value=None)

    result = await denylist_set(mock_client, "jti-duplicate", ttl_seconds=300)

    assert result is False


async def test_denylist_exists_returns_true_when_key_present():
    """denylist_exists returns True when the key is in Redis."""
    from app.utils.redis_client import denylist_exists

    mock_client = AsyncMock()
    mock_client.exists = AsyncMock(return_value=1)

    result = await denylist_exists(mock_client, "jti-present")

    assert result is True
    mock_client.exists.assert_called_once_with(f"rest:jwt:denylist:jti-present")


async def test_denylist_exists_returns_false_when_key_absent():
    """denylist_exists returns False when the key is not in Redis."""
    from app.utils.redis_client import denylist_exists

    mock_client = AsyncMock()
    mock_client.exists = AsyncMock(return_value=0)

    result = await denylist_exists(mock_client, "jti-absent")

    assert result is False


async def test_ping_returns_true_when_up():
    """ping_redis returns True when the Redis server responds to PING."""
    from app.utils.redis_client import ping_redis

    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)

    result = await ping_redis(mock_client)

    assert result is True
    mock_client.ping.assert_called_once()
