from __future__ import annotations

import re

from app.models.common import Link, LinksMap


def list_link(path: str) -> LinksMap:
    """Build a _links.list entry by stripping the trailing /{id} segment from path."""
    # Strip trailing path segment that looks like an ID (numeric or slug)
    list_path = re.sub(r"/[^/]+$", "", path) or path
    return {"list": Link(href=list_path, method="GET")}


def login_link() -> LinksMap:
    """Build a _links.login entry pointing at the login endpoint."""
    return {"login": Link(href="/api/v1/auth/login", method="POST")}


def page_links(base_path: str, page: int, size: int, total: int, **filters) -> LinksMap:
    """Build pagination _links for a list envelope (self, first, last, next?, prev?).

    first and last are omitted when total is 0 — there are no pages to navigate.
    Keyword filters (e.g. q="hello", movie_id=1) are appended to every navigation URL;
    """
    active = {k: v for k, v in filters.items() if v not in (None, "")}

    def _href(p: int) -> str:
        href = f"{base_path}?page={p}&size={size}"
        for key, value in active.items():
            href += f"&{key}={value}"
        return href

    links: LinksMap = {"self": Link(href=_href(page), method="GET")}

    if total > 0:
        last_page = max(1, (total + size - 1) // size)
        links["first"] = Link(href=_href(1), method="GET")
        links["last"] = Link(href=_href(last_page), method="GET")
        if page > 1:
            links["prev"] = Link(href=_href(page - 1), method="GET")
        if page < last_page:
            links["next"] = Link(href=_href(page + 1), method="GET")

    return links
