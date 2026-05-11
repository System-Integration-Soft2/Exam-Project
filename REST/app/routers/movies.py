from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from app.services.movie_service import (
    create_movie,
    delete_movie,
    get_movie,
    list_movies,
    update_movie,
)
from app.utils.db import get_db
from app.utils.links import page_links
from app.models import Link, LinksMap, MovieRequest, MovieResponse, MoviePage
from app.utils.security import get_current_user, oauth2_scheme, require_admin

router = APIRouter(prefix="/api/v1/movies", tags=["movies"])


def _get_redis():
    from app.main import app
    return app.state.redis


def _get_settings():
    from app.main import app
    return app.state.settings


def _movie_links(movie_id: int) -> LinksMap:
    """Build the standard HATEOAS link set for a single movie resource."""
    base = f"/api/v1/movies/{movie_id}"
    return {
        "self": Link(href=base, method="GET"),
        "update": Link(href=base, method="PUT"),
        "delete": Link(href=base, method="DELETE"),
        "reviews": Link(href=f"/api/v1/reviews?movie_id={movie_id}", method="GET"),
    }


def _genre_links(genre_id: int) -> LinksMap:
    """Build the standard HATEOAS link set for a genre embedded in a movie response."""
    return {"self": Link(href=f"/api/v1/genres/{genre_id}", method="GET")}



def _build_movie_response(row: dict) -> MovieResponse:
    """Assemble a MovieResponse from a service-layer dict (includes genres list)."""
    from app.models import GenreResponse

    genres = [
        GenreResponse(
            id=g["id"],
            name=g["name"],
            links=_genre_links(g["id"]),
        )
        for g in row.get("genres", [])
    ]
    return MovieResponse(
        id=row["id"],
        title=row["title"],
        release_year=row["release_year"],
        runtime_minutes=row["runtime_minutes"],
        director=row["director"],
        synopsis=row["synopsis"],
        genres=genres,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        links=_movie_links(row["id"]),
    )


@router.get("/", response_model=MoviePage)
async def list_movies_endpoint(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
    db=Depends(get_db),
):
    """List movies with optional title search and pagination."""
    items_raw, total = await list_movies(db, q, page, size)
    # Clamp size to 100 after Query validation (ge=1 already enforced above)
    effective_size = min(size, 100)
    items = [_build_movie_response(row) for row in items_raw]
    envelope = MoviePage(
        items=items,
        page=page,
        size=effective_size,
        total=total,
        links=page_links(page, effective_size, total, q),
    )
    return envelope


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie_endpoint(
    movie_id: int,
    db=Depends(get_db),
):
    """Retrieve a single movie by id."""
    row = await get_movie(db, movie_id)
    return _build_movie_response(row)


@router.post("/", response_model=MovieResponse, status_code=201)
async def create_movie_endpoint(
    movie_in: MovieRequest,
    response: Response,
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
    redis_client=Depends(_get_redis),
    settings=Depends(_get_settings),
):
    """Create a new movie. Requires admin role."""
    user = await get_current_user(token, db, redis_client, settings)
    require_admin(user)
    row = await create_movie(db, movie_in)
    response.headers["Location"] = f"/api/v1/movies/{row['id']}"
    return _build_movie_response(row)


@router.put("/{movie_id}", response_model=MovieResponse)
async def update_movie_endpoint(
    movie_id: int,
    movie_in: MovieRequest,
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
    redis_client=Depends(_get_redis),
    settings=Depends(_get_settings),
):
    """Update an existing movie. Requires admin role."""
    user = await get_current_user(token, db, redis_client, settings)
    require_admin(user)
    row = await update_movie(db, movie_id, movie_in)
    return _build_movie_response(row)


@router.delete("/{movie_id}", status_code=204)
async def delete_movie_endpoint(
    movie_id: int,
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
    redis_client=Depends(_get_redis),
    settings=Depends(_get_settings),
):
    """Delete a movie. Requires admin role."""
    user = await get_current_user(token, db, redis_client, settings)
    require_admin(user)
    await delete_movie(db, movie_id)
