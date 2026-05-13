"""Tests for JWT sub claim coercion: encode as string, decode as int before DB lookup."""

import pytest

from tests.conftest import TEST_JWT_SECRET


def make_settings(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", "/tmp")
    from app.config import Settings
    return Settings(_env_file=None)


def test_encode_produces_sub_as_string(monkeypatch):
    """create_access_token stores sub as a string, not an int."""
    from app.utils.security import create_access_token, decode_token

    settings = make_settings(monkeypatch)
    token = create_access_token(99, "testuser", "user", settings)
    payload = decode_token(token, settings)

    assert isinstance(payload["sub"], str), "sub must be a string in the JWT payload"
    assert payload["sub"] == "99"


def test_decode_sub_can_be_converted_to_int(monkeypatch):
    """The sub claim from a decoded token can be converted to int for DB lookup."""
    from app.utils.security import create_access_token, decode_token

    settings = make_settings(monkeypatch)
    user_id = 42
    token = create_access_token(user_id, "user42", "user", settings)
    payload = decode_token(token, settings)

    # sub is stored as string per JWT spec; convert to int for DB lookup
    db_user_id = int(payload["sub"])
    assert db_user_id == user_id


def test_refresh_token_sub_is_also_string(monkeypatch):
    """create_refresh_token also stores sub as a string."""
    from app.utils.security import create_refresh_token, decode_token

    settings = make_settings(monkeypatch)
    token = create_refresh_token(7, "user7", "user", settings)
    payload = decode_token(token, settings)

    assert isinstance(payload["sub"], str)
    assert int(payload["sub"]) == 7
