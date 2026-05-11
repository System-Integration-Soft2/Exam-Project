"""HATEOAS link builders shared across routers and exception handlers."""

from __future__ import annotations

import re

from app.models.common import Link, LinksMap

_MOVIES_HREF = "/api/v1/movies"


def list_link(path: str) -> LinksMap:
    """Build a _links.list entry by stripping the trailing /{id} segment from path."""
    # Strip trailing path segment that looks like an ID (numeric or slug)
    list_path = re.sub(r"/[^/]+$", "", path) or path
    return {"list": Link(href=list_path, method="GET")}


def login_link() -> LinksMap:
    """Build a _links.login entry pointing at the login endpoint."""
    return {"login": Link(href="/api/v1/auth/login", method="POST")}


def page_links(page: int, size: int, total: int, q: str | None) -> LinksMap:
    """Build pagination _links for the movie list envelope (self, first, last, next?, prev?)."""
    def _href(p: int) -> str:
        base = f"{_MOVIES_HREF}?page={p}&size={size}"
        if q:
            base += f"&q={q}"
        return base

    last_page = max(1, (total + size - 1) // size)
    links: LinksMap = {
        "self": Link(href=_href(page), method="GET"),
        "first": Link(href=_href(1), method="GET"),
        "last": Link(href=_href(last_page), method="GET"),
    }
    if page > 1:
        links["prev"] = Link(href=_href(page - 1), method="GET")
    if page < last_page:
        links["next"] = Link(href=_href(page + 1), method="GET")
    return links
