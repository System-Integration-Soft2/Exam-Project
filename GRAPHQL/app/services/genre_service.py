"""Genre data access for the GraphQL API."""

from app.utils.db import get_db


def get_all():
    """Fetch all genres."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                id,
                name
            FROM genres
            ORDER BY name ASC
            """
        ).fetchall()


def get_by_id(genre_id: int):
    """Fetch a single genre by id."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                id,
                name
            FROM genres
            WHERE id = ?
            """,
            (genre_id,),
        ).fetchone()


def get_genres_by_movie_id(movie_id: int):
    """Fetch all genres linked to a movie."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                g.id,
                g.name
            FROM genres g
            JOIN movie_genres mg ON mg.genre_id = g.id
            WHERE mg.movie_id = ?
            ORDER BY g.name ASC
            """,
            (movie_id,),
        ).fetchall()