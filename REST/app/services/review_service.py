from app.utils.exceptions import AppError


async def list_reviews(
    db,
    movie_id: int | None,
    page: int,
    size: int,
) -> tuple[list[dict], int]:
    """Return a page of reviews and the total matching count.

    size is clamped to 100; the router enforces ge=1 via Query.
    If movie_id is provided, only reviews for that movie are returned.
    """
    size = min(size, 100)
    offset = (page - 1) * size

    if movie_id is not None:
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM reviews WHERE movie_id = ?",
            (movie_id,),
        )
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT id, movie_id, user_id, rating, comment, created_at "
            "FROM reviews WHERE movie_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (movie_id, size, offset),
        )
    else:
        count_cursor = await db.execute("SELECT COUNT(*) FROM reviews")
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT id, movie_id, user_id, rating, comment, created_at "
            "FROM reviews ORDER BY id LIMIT ? OFFSET ?",
            (size, offset),
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
