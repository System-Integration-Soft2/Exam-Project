"""Pydantic models: HATEOAS links, error envelope, auth tokens, user identity."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Link(BaseModel):
    href: str
    method: str


LinksMap = dict[str, Link]


class ErrorResponse(BaseModel):
    detail: str
    code: str
    links: LinksMap | None = Field(default=None, serialization_alias="_links")
    errors: list | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class UserInternal(BaseModel):
    """Authenticated user identity returned by get_current_user."""
    id: int
    username: str
    email: str
    role: str
