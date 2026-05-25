"""
Movie data access for the GraphQL API.

All SQL related to movies lives here.
Services return database rows, not Strawberry types.

All user values are passed as SQL parameters (?-placeholders), never
string-concatenated, so the layer is safe against SQL injection.
"""

from typing import Optional

from app.utils.db import get_db


# --- Read operations --------------------------------------------------------


def get_by_id(movie_id: int):
    """Fetch a single movie by id, or None if not found."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, title, release_year, runtime_minutes, director, synopsis
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
    """Fetch movies with optional filtering and pagination."""
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

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    params.extend([limit, offset])

    with get_db() as conn:
        return conn.execute(
            f"""
            SELECT m.id, m.title, m.release_year, m.runtime_minutes,
                   m.director, m.synopsis
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
            SELECT m.id, m.title, m.release_year, m.runtime_minutes,
                   m.director, m.synopsis
            FROM movies m
            JOIN movie_genres mg ON mg.movie_id = m.id
            WHERE mg.genre_id = ?
            ORDER BY m.release_year DESC, m.title ASC
            """,
            (genre_id,),
        ).fetchall()


# --- Write operations -------------------------------------------------------


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

    _validate_title(title)
    _validate_release_year(release_year)
    _validate_runtime(runtime_minutes)

    with get_db() as conn:
        if genre_ids:
            _validate_genres_exist(conn, genre_ids)

        cursor = conn.execute(
            """
            INSERT INTO movies (title, release_year, runtime_minutes, director, synopsis)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, release_year, runtime_minutes, director, synopsis),
        )

        movie_id = cursor.lastrowid

        if genre_ids:
            _insert_genre_links(conn, movie_id, genre_ids)

        return _fetch_movie_row(conn, movie_id)


def update(
    movie_id: int,
    title: Optional[str] = None,
    release_year: Optional[int] = None,
    runtime_minutes: Optional[int] = None,
    director: Optional[str] = None,
    synopsis: Optional[str] = None,
    genre_ids: Optional[list[int]] = None,
):
    """
    Partial update. Any argument that is None is left unchanged.

    Pass genre_ids to replace the movie's genre links (full replace of
    that one relationship). Omit genre_ids (None) to keep them.
    """
    # Normalize and validate provided fields
    if title is not None:
        title = title.strip()
        _validate_title(title)
    if director is not None:
        director = director.strip() or None
    if synopsis is not None:
        synopsis = synopsis.strip() or None
    if release_year is not None:
        _validate_release_year(release_year)
    if runtime_minutes is not None:
        _validate_runtime(runtime_minutes)

    with get_db() as conn:
        # Verify movie exists before doing any work
        existing = conn.execute(
            "SELECT 1 FROM movies WHERE id = ?", (movie_id,)
        ).fetchone()
        if existing is None:
            raise ValueError(f"Movie with id {movie_id} does not exist.")

        # Validate genre IDs (if provided) before opening any updates
        if genre_ids:
            _validate_genres_exist(conn, genre_ids)

        # Build dynamic UPDATE only with the fields the client sent
        set_clauses: list[str] = []
        params: list[object] = []

        if title is not None:
            set_clauses.append("title = ?")
            params.append(title)
        if release_year is not None:
            set_clauses.append("release_year = ?")
            params.append(release_year)
        if runtime_minutes is not None:
            set_clauses.append("runtime_minutes = ?")
            params.append(runtime_minutes)
        if director is not None:
            set_clauses.append("director = ?")
            params.append(director)
        if synopsis is not None:
            set_clauses.append("synopsis = ?")
            params.append(synopsis)

        if set_clauses:
            set_clauses.append("updated_at = strftime('%Y-%m-%dT%H:%M:%S', 'now')")
            params.append(movie_id)
            conn.execute(
                f"UPDATE movies SET {', '.join(set_clauses)} WHERE id = ?",
                params,
            )

        # Replace genre links only if the client sent genre_ids.
        # An empty list [] clears all genres; None leaves them untouched.
        if genre_ids is not None:
            conn.execute(
                "DELETE FROM movie_genres WHERE movie_id = ?", (movie_id,)
            )
            if genre_ids:
                _insert_genre_links(conn, movie_id, genre_ids)

        return _fetch_movie_row(conn, movie_id)


# --- Private helpers --------------------------------------------------------


def _validate_title(title: str) -> None:
    if not title:
        raise ValueError("Title must not be empty.")
    if len(title) > 500:
        raise ValueError("Title must be 500 characters or fewer.")


def _validate_release_year(year: int) -> None:
    if year < 1888 or year > 2100:
        raise ValueError("Release year must be between 1888 and 2100.")


def _validate_runtime(minutes: Optional[int]) -> None:
    if minutes is not None and minutes <= 0:
        raise ValueError("Runtime must be a positive number of minutes.")


def _validate_genres_exist(conn, genre_ids: list[int]) -> None:
    """Raise ValueError if any of the given genre ids does not exist."""
    placeholders = ",".join("?" for _ in genre_ids)
    rows = conn.execute(
        f"SELECT id FROM genres WHERE id IN ({placeholders})",
        genre_ids,
    ).fetchall()
    existing = {row["id"] for row in rows}
    missing = [gid for gid in genre_ids if gid not in existing]
    if missing:
        raise ValueError(
            f"Genre id(s) do not exist: {', '.join(map(str, missing))}"
        )


def _insert_genre_links(conn, movie_id: int, genre_ids: list[int]) -> None:
    """Insert (movie_id, genre_id) pairs into movie_genres."""
    conn.executemany(
        "INSERT INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
        [(movie_id, gid) for gid in genre_ids],
    )


def _fetch_movie_row(conn, movie_id: int):
    """Fetch a movie row by id using an already-open connection."""
    return conn.execute(
        """
        SELECT id, title, release_year, runtime_minutes, director, synopsis
        FROM movies
        WHERE id = ?
        """,
        (movie_id,),
    ).fetchone()