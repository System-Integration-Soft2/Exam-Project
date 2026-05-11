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
