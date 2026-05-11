from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import redis.exceptions
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings
from app.utils.db import get_db_connection, init_db
from app.utils.exceptions import register_exception_handlers
from app.utils.redis_client import close_redis, init_redis, ping_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    app.state.settings = settings
    await init_db(settings)
    redis_client = await init_redis(settings.REDIS_URL)
    app.state.redis = redis_client
    yield
    await close_redis(redis_client)


app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)


@app.exception_handler(redis.exceptions.ConnectionError)
async def redis_connection_error_handler(
    request: Request, exc: redis.exceptions.ConnectionError
) -> JSONResponse:
    """Return 503 when Redis is unreachable during a request."""
    logger.error("Redis connection error: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Auth substrate unavailable", "code": "service_unavailable"},
    )


from app.routers.auth import router as auth_router
from app.routers.movies import router as movies_router
from app.routers.genres import router as genres_router
from app.routers.reviews import router as reviews_router
app.include_router(auth_router)
app.include_router(movies_router)
app.include_router(genres_router)
app.include_router(reviews_router)


@app.get("/healthz")
async def healthz():
    """Liveness and readiness probe.

    Checks both the SQLite database (SELECT 1) and Redis (PING).
    Returns 200 with {"db": "ok", "redis": "ok"} when both are healthy.
    Returns 503 with error details when either dependency is unavailable.
    """
    settings = app.state.settings
    db_status = "ok"
    redis_status = "ok"
    errors: dict[str, str] = {}

    try:
        conn = await get_db_connection(settings.DATABASE_PATH)
        try:
            await conn.execute("SELECT 1")
        finally:
            await conn.close()
    except Exception as exc:
        db_status = "error"
        errors["db"] = str(exc)
        logger.error("Health check: database unavailable: %s", exc)

    try:
        await ping_redis(app.state.redis)
    except redis.exceptions.ConnectionError as exc:
        redis_status = "error"
        errors["redis"] = str(exc)
        logger.error("Health check: Redis unavailable: %s", exc)
    except Exception as exc:
        redis_status = "error"
        errors["redis"] = str(exc)
        logger.error("Health check: Redis error: %s", exc)

    if db_status == "ok" and redis_status == "ok":
        return {"db": "ok", "redis": "ok"}

    body: dict = {"db": db_status, "redis": redis_status}
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=503, content=body)
