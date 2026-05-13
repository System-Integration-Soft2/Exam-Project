import time
import uuid
import bcrypt
import jwt
from fastapi.security import OAuth2PasswordBearer

from app.utils.exceptions import AppError

# Pre-computed bcrypt hash used to equalise timing on the unknown-user login path.
# When a username is not found, we still run bcrypt.checkpw against this dummy hash
# so the response time matches the known-user wrong-password path.
DUMMY_HASH: bytes = bcrypt.hashpw(b"dummy", bcrypt.gensalt())

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_MAX_PASSWORD_BYTES = 72  # bcrypt silently truncates at 72 bytes


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt.

    Raises ValueError if the password exceeds 72 bytes (bcrypt truncation limit).
    """
    encoded = plain.encode("utf-8")
    if len(encoded) > _MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must not exceed {_MAX_PASSWORD_BYTES} bytes "
            f"(got {len(encoded)} bytes)"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _make_token(
    user_id: int,
    username: str,
    role: str,
    token_type: str,
    ttl_seconds: int,
    settings,
) -> str:
    """Encode a JWT with the standard claim set."""
    now = int(time.time())
    payload = {
        # sub is stored as string per JWT spec; convert to int for DB lookup at decode
        "sub": str(user_id),
        "username": username,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + ttl_seconds,
        "type": token_type,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, username: str, role: str, settings) -> str:
    """Create a short-lived access JWT."""
    return _make_token(
        user_id, username, role, "access", settings.ACCESS_TOKEN_TTL_SECONDS, settings
    )


def create_refresh_token(user_id: int, username: str, role: str, settings) -> str:
    """Create a long-lived refresh JWT."""
    return _make_token(
        user_id, username, role, "refresh", settings.REFRESH_TOKEN_TTL_SECONDS, settings
    )


def decode_token(token: str, settings) -> dict:
    """Decode and verify a JWT.

    Raises AppError(401) on any PyJWT error (expired, invalid signature,
    wrong algorithm, alg:none, etc.).
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise AppError("unauthorized", "Invalid or expired token", 401) from exc


async def get_current_user(token: str, db, redis_client, settings):
    """FastAPI dependency: decode access token, check denylist, load user from DB.

    Raises AppError(401) if the token is invalid, revoked, or the user is not found.
    Raises redis.exceptions.ConnectionError if Redis is unreachable (fail loud — 503).
    """
    from app.utils.redis_client import denylist_exists
    from app.models import UserInternal

    payload = decode_token(token, settings)

    if payload.get("type") != "access":
        raise AppError("unauthorized", "Invalid token type", 401)

    jti = payload.get("jti", "")
    # denylist_exists raises ConnectionError if Redis is down — let it propagate
    if await denylist_exists(redis_client, jti):
        raise AppError("token_revoked", "Token has been revoked", 401)

    # sub is stored as string per JWT spec; convert to int for DB lookup
    user_id = int(payload["sub"])
    cursor = await db.execute(
        "SELECT id, username, email, role FROM users WHERE id = ?",
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise AppError("unauthorized", "User not found", 401)

    return UserInternal(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        role=row["role"],
    )


def require_admin(user) -> None:
    """Raise AppError(403) if the user does not have the admin role."""
    if user.role != "admin":
        raise AppError("forbidden", "Admin access required", 403)
