from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.services.genre_service import get_genre, list_genres
from app.utils.db import get_db
from app.utils.links import page_links
from app.models import GenreResponse, GenrePage, Link, LinksMap

router = APIRouter(prefix="/api/v1/genres", tags=["genres"])


def _genre_links(genre_id: int) -> LinksMap:
    """Build the HATEOAS link set for a single genre resource."""
    return {"self": Link(href=f"/api/v1/genres/{genre_id}", method="GET")}


def _build_genre_response(row: dict) -> dict:
    """Assemble the dict to be serialized as GenreResponse (includes _links via alias)."""
    return {
        "id": row["id"],
        "name": row["name"],
        "links": _genre_links(row["id"]),
    }


@router.get("/", response_model=GenrePage)
async def list_genres_endpoint(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
    db=Depends(get_db),
):
    """List genres with optional name search and pagination."""
    items_raw, total = await list_genres(db, q, page, size)
    effective_size = min(size, 100)
    items = [
        GenreResponse(**_build_genre_response(row))
        for row in items_raw
    ]
    return GenrePage(
        items=items,
        page=page,
        size=effective_size,
        total=total,
        links=page_links("/api/v1/genres", page, effective_size, total, q=q),
    )


@router.get("/{genre_id}", response_model=GenreResponse)
async def get_genre_endpoint(
    genre_id: int,
    db=Depends(get_db),
):
    """Retrieve a single genre by id."""
    row = await get_genre(db, genre_id)
    return GenreResponse(**_build_genre_response(row))
