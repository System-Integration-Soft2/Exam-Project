"""
Database helper for the gRPC catalog service.

Uses SQLite with parameterized queries (prepared statements) to prevent
SQL-injection — every value is passed as a parameter, never concatenated
into the query string.
"""

import sqlite3
from pathlib import Path

# The shared catalog.db lives in the data/ directory at the Exam-Project root, one level above GRPC/
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.db"


def get_connection() -> sqlite3.Connection:
    """Open a new SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def fetch_movie(movie_id: int) -> dict | None:
    """Return a single movie with its genres, or None if not found."""
    with get_connection() as conn:
        movie_row = conn.execute(
            """
            SELECT id, title, release_year, runtime_minutes, director, synopsis
            FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        ).fetchone()

        if movie_row is None:
            return None

        genre_rows = conn.execute(
            """
            SELECT g.name
            FROM genres g
            JOIN movie_genres mg ON mg.genre_id = g.id
            WHERE mg.movie_id = ?
            """,
            (movie_id,),
        ).fetchall()

        return {
            "id": movie_row["id"],
            "title": movie_row["title"],
            "release_year": movie_row["release_year"],
            "runtime_minutes": movie_row["runtime_minutes"] or 0,
            "director": movie_row["director"] or "",
            "synopsis": movie_row["synopsis"] or "",
            "genres": [row["name"] for row in genre_rows],
        }


def fetch_latest_review_id() -> int:
    """Return the highest review ID currently in the database (0 if none)."""
    with get_connection() as conn:
        row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM reviews").fetchone()
        return row["max_id"]


def fetch_new_reviews_for_movies(movie_ids: list[int], since_review_id: int) -> list[dict]:
    """
    Return reviews for any of the given movie IDs that have an ID greater
    than `since_review_id`. Used by the streaming RPC to push new reviews
    to subscribed clients.
    """
    if not movie_ids:
        return []

    # Build a parameterized IN clause: one ? per movie ID
    placeholders = ",".join("?" for _ in movie_ids)
    params = (*movie_ids, since_review_id)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT r.id          AS review_id,
                   r.movie_id    AS movie_id,
                   m.title       AS movie_title,
                   r.rating      AS rating,
                   r.comment     AS comment,
                   r.created_at  AS created_at
            FROM reviews r
            JOIN movies m ON m.id = r.movie_id
            WHERE r.movie_id IN ({placeholders})
              AND r.id > ?
            ORDER BY r.id ASC
            """,
            params,
        ).fetchall()

        return [dict(row) for row in rows]