"""Unit tests for security utilities: JWT encode/decode, password hashing, token validation."""

import time
import uuid

import bcrypt
import jwt
import pytest

from tests.conftest import TEST_JWT_SECRET


def make_settings(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", "/tmp")
    from app.config import Settings
    return Settings(_env_file=None)


def test_create_access_token_round_trip(monkeypatch):
    """create_access_token produces a JWT that decode_token can verify."""
    from app.utils.security import create_access_token, decode_token

    settings = make_settings(monkeypatch)
    token = create_access_token(1, "alice", "user", settings)
    payload = decode_token(token, settings)

    assert payload["sub"] == "1"
    assert payload["username"] == "alice"
    assert payload["role"] == "user"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload


def test_create_refresh_token_round_trip(monkeypatch):
    """create_refresh_token produces a JWT with type='refresh'."""
    from app.utils.security import create_refresh_token, decode_token

    settings = make_settings(monkeypatch)
    token = create_refresh_token(2, "bob", "admin", settings)
    payload = decode_token(token, settings)

    assert payload["sub"] == "2"
    assert payload["type"] == "refresh"


def test_decode_token_alg_none_raises(monkeypatch):
    """A token signed with alg:none must be rejected."""
    from app.utils.security import decode_token
    from app.utils.exceptions import AppError

    settings = make_settings(monkeypatch)
    # Craft an alg:none token manually
    payload = {"sub": "1", "exp": int(time.time()) + 900}
    none_token = jwt.encode(payload, "", algorithm="none")

    with pytest.raises(AppError) as exc_info:
        decode_token(none_token, settings)
    assert exc_info.value.status == 401


def test_decode_token_wrong_algorithm_raises(monkeypatch):
    """A token signed with HS384 (not HS256) must be rejected."""
    from app.utils.security import decode_token
    from app.utils.exceptions import AppError

    settings = make_settings(monkeypatch)
    payload = {"sub": "1", "exp": int(time.time()) + 900}
    hs384_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS384")

    with pytest.raises(AppError) as exc_info:
        decode_token(hs384_token, settings)
    assert exc_info.value.status == 401


def test_decode_token_tampered_signature_raises(monkeypatch):
    """A token with a tampered signature must be rejected."""
    from app.utils.security import create_access_token, decode_token
    from app.utils.exceptions import AppError

    settings = make_settings(monkeypatch)
    token = create_access_token(1, "alice", "user", settings)
    # Tamper with the signature
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + ".invalidsignature"

    with pytest.raises(AppError) as exc_info:
        decode_token(tampered, settings)
    assert exc_info.value.status == 401


def test_decode_token_expired_raises(monkeypatch):
    """An expired token must be rejected (expiry path, not missing-claim path)."""
    from app.utils.security import decode_token
    from app.utils.exceptions import AppError

    settings = make_settings(monkeypatch)
    # Include iss/aud so the token fails on expiry, not on missing claims.
    payload = {
        "sub": "1",
        "username": "alice",
        "role": "user",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()) - 10,
        "exp": int(time.time()) - 1,
        "type": "access",
        "iss": "rest-api",
        "aud": "rest-api",
    }
    expired_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    with pytest.raises(AppError) as exc_info:
        decode_token(expired_token, settings)
    assert exc_info.value.status == 401


def test_hash_and_verify_password():
    """hash_password produces a hash that verify_password accepts."""
    from app.utils.security import hash_password, verify_password

    plain = "s3cr3tP@ssw0rd"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_password_over_72_bytes_raises():
    """Passwords exceeding 72 bytes must raise a ValueError before hashing."""
    from app.utils.security import hash_password

    # 73 ASCII chars = 73 bytes
    long_password = "a" * 73
    with pytest.raises(ValueError, match="72"):
        hash_password(long_password)


def test_sub_is_string_in_access_token(monkeypatch):
    """JWT sub claim is stored as a string per JWT spec."""
    from app.utils.security import create_access_token, decode_token

    settings = make_settings(monkeypatch)
    token = create_access_token(42, "user42", "user", settings)
    payload = decode_token(token, settings)

    # sub must be a string
    assert isinstance(payload["sub"], str)
    # converting to int must yield the original user_id
    assert int(payload["sub"]) == 42


def test_iss_aud_round_trip(monkeypatch):
    """Tokens issued by create_access_token carry iss and aud claims."""
    from app.utils.security import create_access_token, decode_token

    settings = make_settings(monkeypatch)
    token = create_access_token(1, "alice", "user", settings)
    payload = decode_token(token, settings)

    assert payload["iss"] == "rest-api"
    assert payload["aud"] == "rest-api"


def test_wrong_audience_rejected(monkeypatch):
    """A token with a mismatched aud claim must be rejected with 401."""
    from app.utils.security import decode_token
    from app.utils.exceptions import AppError

    settings = make_settings(monkeypatch)
    # Craft a token with a different audience
    payload = {
        "sub": "1",
        "username": "alice",
        "role": "user",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
        "type": "access",
        "iss": "rest-api",
        "aud": "other-service",
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    with pytest.raises(AppError) as exc_info:
        decode_token(token, settings)
    assert exc_info.value.status == 401
    assert exc_info.value.code == "unauthorized"


def test_wrong_issuer_rejected(monkeypatch):
    """A token with a mismatched iss claim must be rejected with 401."""
    from app.utils.security import decode_token
    from app.utils.exceptions import AppError

    settings = make_settings(monkeypatch)
    # Craft a token with a different issuer
    payload = {
        "sub": "1",
        "username": "alice",
        "role": "user",
        "jti": str(uuid.uuid4()),
        "iat": int(time.time()),
        "exp": int(time.time()) + 900,
        "type": "access",
        "iss": "other-issuer",
        "aud": "rest-api",
    }
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    with pytest.raises(AppError) as exc_info:
        decode_token(token, settings)
    assert exc_info.value.status == 401
    assert exc_info.value.code == "unauthorized"
