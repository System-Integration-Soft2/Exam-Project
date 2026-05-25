import redis.asyncio as aioredis


_DENYLIST_PREFIX = "rest:jwt:denylist:"


def denylist_key(jti: str) -> str:
    """Return the Redis key for a JWT denylist entry."""
    return f"{_DENYLIST_PREFIX}{jti}"


async def init_redis(redis_url: str) -> aioredis.Redis:
    """Create and return an async Redis client from the given URL.

    The client is not yet connected; the first command will establish
    the connection. Raises redis.exceptions.ConnectionError if the
    server is unreachable on first use.
    """
    return aioredis.from_url(redis_url, decode_responses=True)


async def close_redis(client: aioredis.Redis) -> None:
    """Close the Redis connection pool gracefully."""
    await client.aclose()


async def denylist_set(client: aioredis.Redis, jti: str, ttl_seconds: int) -> bool:
    """Add a JWT jti to the denylist with the given TTL.

    Uses SET NX (set if not exists) so that a concurrent call for the
    same jti loses the race and returns False. The caller can treat
    False as "already denylisted" — the token is revoked either way.

    Returns True if the key was set, False if it already existed.
    """
    key = denylist_key(jti)
    result = await client.set(key, "1", ex=ttl_seconds, nx=True)
    return result is True


async def denylist_exists(client: aioredis.Redis, jti: str) -> bool:
    """Return True if the jti is present in the denylist, False otherwise."""
    key = denylist_key(jti)
    count = await client.exists(key)
    return count > 0


async def ping_redis(client: aioredis.Redis) -> bool:
    """Send a PING to Redis and return True on success.
    Raises redis.exceptions.ConnectionError if the server is unreachable.
    """
    return await client.ping()
