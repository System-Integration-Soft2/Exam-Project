from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.services.auth_service import login, logout, refresh
from app.utils.db import get_db
from app.models import LogoutRequest, RefreshRequest, TokenPair, UserInternal
from app.utils.security import get_current_user, oauth2_scheme

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_redis():
    """FastAPI dependency: return the Redis client from app state."""
    from app.main import app
    return app.state.redis


def _get_settings():
    """FastAPI dependency: return Settings from app state."""
    from app.main import app
    return app.state.settings


@router.post("/login", response_model=TokenPair)
async def login_endpoint(
    form: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
    settings=Depends(_get_settings),
):
    """Authenticate with username and password (form-encoded). Returns a token pair."""
    return await login(form.username, form.password, db, settings)


@router.post("/refresh", response_model=TokenPair)
async def refresh_endpoint(
    body: RefreshRequest,
    redis_client=Depends(_get_redis),
    db=Depends(get_db),
    settings=Depends(_get_settings),
):
    """Rotate a refresh token. Returns a new access+refresh token pair."""
    return await refresh(body.refresh_token, redis_client, db, settings)


@router.post("/logout", status_code=204)
async def logout_endpoint(
    body: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    redis_client=Depends(_get_redis),
    db=Depends(get_db),
    settings=Depends(_get_settings),
):
    """Revoke the current access and refresh tokens. Returns 204 No Content."""
    current_user: UserInternal = await get_current_user(token, db, redis_client, settings)
    await logout(token, body.refresh_token, redis_client, settings)
