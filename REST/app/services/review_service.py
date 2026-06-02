from app.utils.db import escape_like
from app.utils.exceptions import AppError


async def list_reviews(
    db,
    q: str | None,
    movie_id: int | None,
    page: int,
    size: int,
) -> tuple[list[dict], int]:
    """Return a page of reviews and the total matching count.

    size is clamped to 100; the router enforces ge=1 via Query.
    If movie_id is provided, only reviews for that movie are returned.
    If q is provided, reviews are filtered to those whose comment
    contains the search text (case-insensitive). When both q and
    movie_id are given, both conditions must match.
    """
    size = min(size, 100)
    offset = (page - 1) * size

    conditions: list[str] = []
    params: list = []

    if movie_id is not None:
        conditions.append("movie_id = ?")
        params.append(movie_id)

    if q and q.strip():
        pattern = escape_like(q.strip())
        conditions.append("comment LIKE ? ESCAPE '\\'")
        params.append(pattern)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    count_cursor = await db.execute(
        f"SELECT COUNT(*) FROM reviews {where}",
        params,
    )
    total = (await count_cursor.fetchone())[0]

    cursor = await db.execute(
        f"SELECT id, movie_id, user_id, rating, comment, created_at "
        f"FROM reviews {where} ORDER BY id LIMIT ? OFFSET ?",
        params + [size, offset],
    )

    rows = await cursor.fetchall()
    items = [
        {
            "id": row["id"],
            "movie_id": row["movie_id"],
            "user_id": row["user_id"],
            "rating": row["rating"],
            "comment": row["comment"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return items, total


async def get_review(db, review_id: int) -> dict:
    """Return a single review by id.

    Raises AppError(404) if the review does not exist.
    """
    cursor = await db.execute(
        "SELECT id, movie_id, user_id, rating, comment, created_at "
        "FROM reviews WHERE id = ?",
        (review_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise AppError("not_found", "Review not found", 404)
    return {
        "id": row["id"],
        "movie_id": row["movie_id"],
        "user_id": row["user_id"],
        "rating": row["rating"],
        "comment": row["comment"],
        "created_at": row["created_at"],
    }
