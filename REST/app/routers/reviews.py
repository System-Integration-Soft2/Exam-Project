from fastapi import APIRouter, Depends, Query

from app.services.review_service import get_review, list_reviews
from app.utils.db import get_db
from app.utils.links import page_links
from app.models import ReviewResponse, ReviewPage, Link, LinksMap

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


def _review_links(review_id: int, movie_id: int) -> LinksMap:
    """Build the HATEOAS link set for a single review resource."""
    return {
        "self": Link(href=f"/api/v1/reviews/{review_id}", method="GET"),
        "movie": Link(href=f"/api/v1/movies/{movie_id}", method="GET"),
    }


def _build_review_response(row: dict) -> dict:
    """Assemble the dict to be serialized as ReviewResponse (includes _links via alias)."""
    return {
        "id": row["id"],
        "movie_id": row["movie_id"],
        "user_id": row["user_id"],
        "rating": row["rating"],
        "comment": row["comment"],
        "created_at": row["created_at"],
        "links": _review_links(row["id"], row["movie_id"]),
    }


@router.get("/", response_model=ReviewPage)
async def list_reviews_endpoint(
    movie_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1),
    db=Depends(get_db),
):
    """List reviews with optional movie_id filter and pagination."""
    items_raw, total = await list_reviews(db, movie_id, page, size)
    effective_size = min(size, 100)
    items = [
        ReviewResponse(**_build_review_response(row))
        for row in items_raw
    ]
    return ReviewPage(
        items=items,
        page=page,
        size=effective_size,
        total=total,
        links=page_links("/api/v1/reviews", page, effective_size, total, movie_id=movie_id),
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review_endpoint(
    review_id: int,
    db=Depends(get_db),
):
    """Retrieve a single review by id."""
    row = await get_review(db, review_id)
    return ReviewResponse(**_build_review_response(row))
