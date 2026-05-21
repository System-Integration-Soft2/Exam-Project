"""
Review data access for the GraphQL API.

All SQL related to reviews lives here.
Services return database rows, not Strawberry types.
"""

import html
from typing import Optional

from app.utils.db import get_db


def _sanitize(text: Optional[str]) -> Optional[str]:
    """Escape HTML-special characters in user-supplied text."""
    if text is None:
        return None

    text = text.strip()

    if not text:
        return None

    return html.escape(text, quote=True)


def get_by_movie_id(movie_id: int):
    """Fetch all reviews for a movie, newest first."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                id,
                movie_id,
                user_id,
                rating,
                comment,
                created_at
            FROM reviews
            WHERE movie_id = ?
            ORDER BY created_at DESC
            """,
            (movie_id,),
        ).fetchall()


def get_author(user_id: int):
    """Fetch public author information for a review."""
    with get_db() as conn:
        return conn.execute(
            """
            SELECT
                id,
                username
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()


def create(
    movie_id: int,
    user_id: int,
    rating: int,
    comment: Optional[str] = None,
):
    """Create a review for an existing movie."""
    if rating < 1 or rating > 10:
        raise ValueError("Rating must be between 1 and 10.")

    if comment is not None and len(comment) > 2000:
        raise ValueError("Comment must be 2000 characters or fewer.")

    clean_comment = _sanitize(comment)

    with get_db() as conn:
        movie_exists = conn.execute(
            """
            SELECT 1
            FROM movies
            WHERE id = ?
            """,
            (movie_id,),
        ).fetchone()

        if movie_exists is None:
            raise ValueError(f"Movie with id {movie_id} does not exist.")

        user_exists = conn.execute(
            """
            SELECT 1
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

        if user_exists is None:
            raise ValueError(f"User with id {user_id} does not exist.")

        cursor = conn.execute(
            """
            INSERT INTO reviews (
                movie_id,
                user_id,
                rating,
                comment
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                movie_id,
                user_id,
                rating,
                clean_comment,
            ),
        )

        review_id = cursor.lastrowid

        return conn.execute(
            """
            SELECT
                id,
                movie_id,
                user_id,
                rating,
                comment,
                created_at
            FROM reviews
            WHERE id = ?
            """,
            (review_id,),
        ).fetchone()


def delete(review_id: int) -> bool:
    """Delete a review by id."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            DELETE FROM reviews
            WHERE id = ?
            """,
            (review_id,),
        )

        return cursor.rowcount > 0