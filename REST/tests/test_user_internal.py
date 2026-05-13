"""Tests for UserInternal model: Pydantic model, attribute access, role field."""

import pytest


def test_user_internal_is_pydantic_model():
    """UserInternal is a Pydantic BaseModel with the expected fields."""
    from app.models import UserInternal

    user = UserInternal(id=1, username="alice", email="alice@example.com", role="user")
    assert user.id == 1
    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.role == "user"


def test_user_internal_role_attribute_access():
    """UserInternal.role is accessible as an attribute."""
    from app.models import UserInternal

    admin = UserInternal(id=2, username="admin", email="admin@example.com", role="admin")
    assert admin.role == "admin"


def test_user_internal_requires_all_fields():
    """UserInternal raises ValidationError when required fields are missing."""
    from pydantic import ValidationError
    from app.models import UserInternal

    with pytest.raises(ValidationError):
        UserInternal(id=1, username="alice")  # missing email and role
