"""Auth service: login, refresh rotation, and logout flows."""

from __future__ import annotations

import time

import bcrypt

from app.utils.exceptions import AppError
from app.utils.models import TokenPair
from app.utils.redis_client import denylist_exists, denylist_set
from app.utils.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)


async def login(username: str, password: str, db, settings) -> TokenPair:
    """Authenticate a user and return a new access+refresh token pair.

    Runs a dummy bcrypt check on the unknown-user path to equalise timing
    and prevent username enumeration via response latency.
    """
    cursor = await db.execute(
        "SELECT id, username, email, role, password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = await cursor.fetchone()

    if row is None:
        # Equalise timing: run bcrypt even when the user doesn't exist
        bcrypt.checkpw(b"x", DUMMY_HASH)
        raise AppError("unauthorized", "Invalid credentials", 401)

    if not verify_password(password, row["password_hash"]):
        raise AppError("unauthorized", "Invalid credentials", 401)

    access_token = create_access_token(row["id"], row["username"], row["role"], settings)
    refresh_token = create_refresh_token(row["id"], row["username"], row["role"], settings)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
    )


async def refresh(refresh_token_str: str, redis_client, db, settings) -> TokenPair:
    """Rotate a refresh token: atomically claim the old jti, issue a new pair.

    Uses SET NX so that concurrent calls for the same token lose the race
    and receive 401 token_revoked.
    """
    payload = decode_token(refresh_token_str, settings)

    if payload.get("type") != "refresh":
        raise AppError("unauthorized", "Invalid token type", 401)

    old_jti = payload["jti"]
    exp = payload["exp"]
    remaining_ttl = max(0, exp - int(time.time()))

    # Atomic claim: SET NX returns False if the jti is already denylisted
    claimed = await denylist_set(redis_client, old_jti, max(remaining_ttl, 1))
    if not claimed:
        raise AppError("token_revoked", "Token has been revoked", 401)

    # sub is stored as string per JWT spec; convert to int for DB lookup
    user_id = int(payload["sub"])
    cursor = await db.execute(
        "SELECT id, username, role FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise AppError("unauthorized", "User not found", 401)

    access_token = create_access_token(row["id"], row["username"], row["role"], settings)
    new_refresh_token = create_refresh_token(row["id"], row["username"], row["role"], settings)

    return TokenPair(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_TTL_SECONDS,
    )


async def logout(
    access_token_str: str,
    refresh_token_str: str,
    redis_client,
    settings,
) -> None:
    """Revoke both the access and refresh tokens by adding their jtis to the denylist.

    Tokens with a non-positive remaining TTL are skipped (already expired).
    """
    now = int(time.time())

    access_payload = decode_token(access_token_str, settings)
    access_ttl = max(0, access_payload["exp"] - now)
    if access_ttl > 0:
        await denylist_set(redis_client, access_payload["jti"], access_ttl)

    refresh_payload = decode_token(refresh_token_str, settings)
    refresh_ttl = max(0, refresh_payload["exp"] - now)
    if refresh_ttl > 0:
        await denylist_set(redis_client, refresh_payload["jti"], refresh_ttl)
