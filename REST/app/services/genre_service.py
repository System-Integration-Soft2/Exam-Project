from __future__ import annotations

from app.utils.db import escape_like
from app.utils.exceptions import AppError


async def list_genres(
    db,
    q: str | None,
    page: int,
    size: int,
) -> tuple[list[dict], int]:
    """Return a page of genres and the total matching count.

    size is clamped to 100; the router enforces ge=1 via Query.
    If q is provided and non-empty after stripping, a case-insensitive
    LIKE search is applied to the name column using escape_like.
    """
    size = min(size, 100)
    offset = (page - 1) * size

    if q and q.strip():
        pattern = escape_like(q.strip())
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM genres WHERE name LIKE ? ESCAPE '\\'",
            (pattern,),
        )
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT id, name FROM genres WHERE name LIKE ? ESCAPE '\\' ORDER BY id LIMIT ? OFFSET ?",
            (pattern, size, offset),
        )
    else:
        count_cursor = await db.execute("SELECT COUNT(*) FROM genres")
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT id, name FROM genres ORDER BY id LIMIT ? OFFSET ?",
            (size, offset),
        )

    rows = await cursor.fetchall()
    items = [{"id": row["id"], "name": row["name"]} for row in rows]
    return items, total


async def get_genre(db, genre_id: int) -> dict:
    """Return a single genre by id.

    Raises AppError(404) if the genre does not exist.
    """
    cursor = await db.execute(
        "SELECT id, name FROM genres WHERE id = ?",
        (genre_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise AppError("not_found", "Genre not found", 404)
    return {"id": row["id"], "name": row["name"]}
