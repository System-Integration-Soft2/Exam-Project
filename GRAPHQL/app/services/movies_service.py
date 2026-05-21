"""
Movie data access for the GraphQL API.

All SQL related to movies lives here.
Services return database rows, not Strawberry types.
"""

from typing import Optional

from app.utils.db import get_db


def get_by_id(movie_id: int):
    """Fetch a single movie by id, or None if not found."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                id,
                title,
                release_year,
                runtime_minutes,
                director,
                synopsis
            FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        ).fetchone()


def get_all(
    genre: Optional[str] = None,
    year: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """
    Fetch movies with optional filtering and pagination.

    User values are always passed as SQL parameters.
    """
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    where_clauses: list[str] = []
    params: list[object] = []

    if genre:
        where_clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM movie_genres mg
                JOIN genres g ON g.id = mg.genre_id
                WHERE mg.movie_id = m.id
                AND LOWER(g.name) = LOWER(?)
            )
            """
        )
        params.append(genre)

    if year is not None:
        where_clauses.append("m.release_year = ?")
        params.append(year)

    if search:
        where_clauses.append(
            """
            (
                LOWER(m.title) LIKE ?
                OR LOWER(m.director) LIKE ?
                OR LOWER(m.synopsis) LIKE ?
            )
            """
        )
        pattern = f"%{search.lower()}%"
        params.extend([pattern, pattern, pattern])

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    params.extend([limit, offset])

    with get_db() as conn:
        return conn.execute(
            f"""
            SELECT
                m.id,
                m.title,
                m.release_year,
                m.runtime_minutes,
                m.director,
                m.synopsis
            FROM movies m
            {where_sql}
            ORDER BY m.release_year DESC, m.title ASC
            LIMIT ?
            OFFSET ?
            """,
            params,
        ).fetchall()


def get_by_genre_id(genre_id: int):
    """Fetch all movies belonging to a genre."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                m.id,
                m.title,
                m.release_year,
                m.runtime_minutes,
                m.director,
                m.synopsis
            FROM movies m
            JOIN movie_genres mg ON mg.movie_id = m.id
            WHERE mg.genre_id = ?
            ORDER BY m.release_year DESC, m.title ASC
            """,
            (genre_id,),
        ).fetchall()


def get_rating_summary(movie_id: int):
    """Fetch review count and average rating for a movie."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                COUNT(*) AS count,
                AVG(rating) AS average
            FROM reviews
            WHERE movie_id = ?
            """,
            (movie_id,),
        ).fetchone()


def create(
    title: str,
    release_year: int,
    runtime_minutes: Optional[int] = None,
    director: Optional[str] = None,
    synopsis: Optional[str] = None,
    genre_ids: Optional[list[int]] = None,
):
    """Create a movie and optionally link it to genres."""
    genre_ids = genre_ids or []

    title = title.strip()
    director = director.strip() if director else None
    synopsis = synopsis.strip() if synopsis else None

    if not title:
        raise ValueError("Title must not be empty.")

    if len(title) > 500:
        raise ValueError("Title must be 500 characters or fewer.")

    if release_year < 1888 or release_year > 2100:
        raise ValueError("Release year must be between 1888 and 2100.")

    if runtime_minutes is not None and runtime_minutes <= 0:
        raise ValueError("Runtime must be a positive number of minutes.")

    with get_db() as conn:
        if genre_ids:
            placeholders = ",".join("?" for _ in genre_ids)

            existing = conn.execute(
                f"""
                SELECT id
                FROM genres
                WHERE id IN ({placeholders})
                """,
                genre_ids,
            ).fetchall()

            existing_ids = {row["id"] for row in existing}
            missing_ids = [genre_id for genre_id in genre_ids if genre_id not in existing_ids]

            if missing_ids:
                raise ValueError(
                    f"Genre id(s) do not exist: {', '.join(map(str, missing_ids))}"
                )

        cursor = conn.execute(
            """
            INSERT INTO movies (
                title,
                release_year,
                runtime_minutes,
                director,
                synopsis
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title,
                release_year,
                runtime_minutes,
                director,
                synopsis,
            ),
        )

        movie_id = cursor.lastrowid

        if genre_ids:
            conn.executemany(
                """
                INSERT INTO movie_genres (movie_id, genre_id)
                VALUES (?, ?)
                """,
                [(movie_id, genre_id) for genre_id in genre_ids],
            )

        return conn.execute(
            """
            SELECT
                id,
                title,
                release_year,
                runtime_minutes,
                director,
                synopsis
            FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        ).fetchone()