from app.utils.db import escape_like
from app.utils.exceptions import AppError


async def _fetch_genres_for_movie(db, movie_id: int) -> list[dict]:
    """Return all genres associated with a movie as a list of dicts."""
    cursor = await db.execute(
        """
        SELECT g.id, g.name
        FROM genres g
        JOIN movie_genres mg ON mg.genre_id = g.id
        WHERE mg.movie_id = ?
        ORDER BY g.name
        """,
        (movie_id,),
    )
    rows = await cursor.fetchall()
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def _row_to_dict(row) -> dict:
    """Convert an aiosqlite Row to a plain dict."""
    return dict(row)


async def list_movies(
    db,
    q: str | None,
    page: int,
    size: int,
) -> tuple[list[dict], int]:
    """Return a page of movies and the total matching count.

    size is clamped to 100 here; the router enforces ge=1 via Query.
    If q is provided and non-empty after stripping, a case-insensitive
    LIKE search is applied to the title column using escape_like.
    """
    size = min(size, 100)
    offset = (page - 1) * size

    if q and q.strip():
        pattern = escape_like(q.strip())
        count_cursor = await db.execute(
            "SELECT COUNT(*) FROM movies WHERE title LIKE ? ESCAPE '\\'",
            (pattern,),
        )
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT id, title, release_year, runtime_minutes, director, synopsis,
                   created_at, updated_at
            FROM movies
            WHERE title LIKE ? ESCAPE '\\'
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (pattern, size, offset),
        )
    else:
        count_cursor = await db.execute("SELECT COUNT(*) FROM movies")
        total = (await count_cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT id, title, release_year, runtime_minutes, director, synopsis,
                   created_at, updated_at
            FROM movies
            ORDER BY id
            LIMIT ? OFFSET ?
            """,
            (size, offset),
        )

    rows = await cursor.fetchall()
    items = []
    for row in rows:
        movie = _row_to_dict(row)
        movie["genres"] = await _fetch_genres_for_movie(db, movie["id"])
        items.append(movie)

    return items, total


async def get_movie(db, movie_id: int) -> dict:
    """Return a single movie by id, with genres populated.

    Raises AppError(404) if the movie does not exist.
    """
    cursor = await db.execute(
        """
        SELECT id, title, release_year, runtime_minutes, director, synopsis,
               created_at, updated_at
        FROM movies
        WHERE id = ?
        """,
        (movie_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise AppError("not_found", f"Movie {movie_id} not found", 404)

    movie = _row_to_dict(row)
    movie["genres"] = await _fetch_genres_for_movie(db, movie_id)
    return movie


async def _validate_genre_ids(db, genre_ids: list[int]) -> None:
    """Raise AppError(422) if any genre_id does not exist in the genres table."""
    if not genre_ids:
        return
    placeholders = ",".join("?" * len(genre_ids))
    cursor = await db.execute(
        f"SELECT id FROM genres WHERE id IN ({placeholders})",
        genre_ids,
    )
    found = {row["id"] for row in await cursor.fetchall()}
    missing = set(genre_ids) - found
    if missing:
        raise AppError(
            "validation_error",
            f"Genre ids not found: {sorted(missing)}",
            422,
        )


async def create_movie(db, movie_in) -> dict:
    """Insert a new movie and its genre associations. Returns the created movie dict."""
    await _validate_genre_ids(db, movie_in.genre_ids)

    cursor = await db.execute(
        """
        INSERT INTO movies (title, release_year, runtime_minutes, director, synopsis)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            movie_in.title,
            movie_in.release_year,
            movie_in.runtime_minutes,
            movie_in.director,
            movie_in.synopsis,
        ),
    )
    await db.commit()
    new_id = cursor.lastrowid

    if movie_in.genre_ids:
        await db.executemany(
            "INSERT INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
            [(new_id, gid) for gid in movie_in.genre_ids],
        )
        await db.commit()

    return await get_movie(db, new_id)


async def update_movie(db, movie_id: int, movie_in) -> dict:
    """Update an existing movie's fields and genre associations.

    Raises AppError(404) if the movie does not exist.
    Raises AppError(422) if any genre_id does not exist.
    Sets updated_at explicitly because SQLite does not auto-update it.
    """
    # Verify the movie exists before updating
    cursor = await db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,))
    if await cursor.fetchone() is None:
        raise AppError("not_found", f"Movie {movie_id} not found", 404)

    await _validate_genre_ids(db, movie_in.genre_ids)

    await db.execute(
        """
        UPDATE movies
        SET title = ?,
            release_year = ?,
            runtime_minutes = ?,
            director = ?,
            synopsis = ?,
            updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')
        WHERE id = ?
        """,
        (
            movie_in.title,
            movie_in.release_year,
            movie_in.runtime_minutes,
            movie_in.director,
            movie_in.synopsis,
            movie_id,
        ),
    )
    await db.commit()

    # Replace genre associations atomically
    await db.execute("DELETE FROM movie_genres WHERE movie_id = ?", (movie_id,))
    if movie_in.genre_ids:
        await db.executemany(
            "INSERT INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
            [(movie_id, gid) for gid in movie_in.genre_ids],
        )
    await db.commit()

    return await get_movie(db, movie_id)


async def delete_movie(db, movie_id: int) -> None:
    """Delete a movie by id.

    Raises AppError(404) if the movie does not exist.
    """
    cursor = await db.execute("SELECT id FROM movies WHERE id = ?", (movie_id,))
    if await cursor.fetchone() is None:
        raise AppError("not_found", f"Movie {movie_id} not found", 404)

    await db.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    await db.commit()
