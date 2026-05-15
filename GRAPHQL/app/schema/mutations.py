"""
GraphQL Mutation type — the entry point for all write operations.

Two mutations are defined here:

  - addReview: create a new review on an existing movie.
  - addMovie:  create a new movie, optionally linking it to genres.

Mutations differ from queries in three important ways:

  1. They validate input before touching the database.
  2. They sanitise user-provided strings to prevent XSS, by escaping
     HTML-special characters so they render as text in any frontend.
  3. They raise GraphQLError on failure, which becomes a structured
     error in the response — distinct from "returned null because
     the object doesn't exist".

Auth note:
    In a production system, the userId for addReview would be derived
    from a JWT in the Authorization header — clients couldn't claim to
    be a different user. We accept userId in the input because this
    project has no auth on GraphQL by design. Field-level permission
    checks (slide 8 of the course materials) would be added here.
"""

import html
from typing import Optional
import strawberry
from graphql import GraphQLError

from app.utils.db import get_connection
from app.schema.types import (
    Movie,
    Review,
    _row_to_movie,
    _row_to_review,
)
from app.schema.inputs import (
    AddReviewInput,
    AddMovieInput,
)


# ---------------------------------------------------------------------
# Helper: escape user-supplied strings before storing them.
#
# We use Python's built-in html.escape() which converts:
#   <  -->  &lt;
#   >  -->  &gt;
#   &  -->  &amp;
#   "  -->  &quot;  (with quote=True)
#   '  -->  &#x27;  (with quote=True)
#
# This means "<script>alert(1)</script>" becomes harmless text in any
# HTML context — it renders as literal characters, not as a tag.
#
# Note: html.escape is a defense in depth. The PROPER place to handle
# XSS is at the rendering step (i.e. the frontend), but escaping on
# input prevents stored XSS payloads from ever reaching the database.
# ---------------------------------------------------------------------
def _sanitise(text: Optional[str]) -> Optional[str]:
    """Escape HTML-special characters in user-supplied text."""
    if text is None:
        return None
    return html.escape(text, quote=True)


@strawberry.type
class Mutation:
    """Root Mutation type — all write operations live here."""

    # -----------------------------------------------------------------
    # Mutation 1: add a review.
    #
    # Validation:
    #   - rating must be 1-10 (matches DB CHECK constraint)
    #   - movie must exist (we check before inserting)
    #   - user must exist (we check before inserting)
    #   - comment is sanitised against XSS
    # -----------------------------------------------------------------
    @strawberry.field
    def add_review(self, input: AddReviewInput) -> Review:
        """Create a new review on an existing movie."""
        # Validate rating range. The DB also enforces this via CHECK,
        # but failing here gives a friendlier error message.
        if input.rating < 1 or input.rating > 10:
            raise GraphQLError("Rating must be between 1 and 10.")

        # Validate comment length if provided.
        if input.comment is not None and len(input.comment) > 2000:
            raise GraphQLError("Comment must be 2000 characters or fewer.")

        clean_comment = _sanitise(input.comment)

        with get_connection() as conn:
            # Verify the movie exists. We could let the FK constraint
            # raise an IntegrityError on INSERT, but doing the check
            # explicitly gives us a clean, GraphQL-shaped error.
            movie_exists = conn.execute(
                "SELECT 1 FROM movies WHERE id = ?",
                (int(input.movie_id),),
            ).fetchone()
            if movie_exists is None:
                raise GraphQLError(f"Movie with id {input.movie_id} does not exist.")

            user_exists = conn.execute(
                "SELECT 1 FROM users WHERE id = ?",
                (int(input.user_id),),
            ).fetchone()
            if user_exists is None:
                raise GraphQLError(f"User with id {input.user_id} does not exist.")

            # Insert the review and get the new id back.
            cursor = conn.execute(
                """
                INSERT INTO reviews (movie_id, user_id, rating, comment)
                VALUES (?, ?, ?, ?)
                """,
                (int(input.movie_id), int(input.user_id), input.rating, clean_comment),
            )
            conn.commit()
            new_id = cursor.lastrowid

            # Fetch the newly inserted row so we can return it.
            row = conn.execute(
                """
                SELECT id, movie_id, user_id, rating, comment, created_at
                FROM reviews
                WHERE id = ?
                """,
                (new_id,),
            ).fetchone()
            return _row_to_review(row)

    # -----------------------------------------------------------------
    # Mutation 2: add a movie.
    #
    # Validation:
    #   - title must be non-empty after stripping whitespace
    #   - release_year must be 1888-2100 (matches DB CHECK constraint)
    #   - runtime_minutes, if provided, must be positive
    #   - all string fields are sanitised
    #   - genre_ids, if provided, must all reference existing genres
    # -----------------------------------------------------------------
    @strawberry.field
    def add_movie(self, input: AddMovieInput) -> Movie:
        """Create a new movie, optionally linking it to genres."""
        # Validate title is non-empty.
        title = input.title.strip()
        if not title:
            raise GraphQLError("Title must not be empty.")
        if len(title) > 500:
            raise GraphQLError("Title must be 500 characters or fewer.")

        # Validate release_year range.
        if input.release_year < 1888 or input.release_year > 2100:
            raise GraphQLError("Release year must be between 1888 and 2100.")

        # Validate runtime_minutes if provided.
        if input.runtime_minutes is not None and input.runtime_minutes <= 0:
            raise GraphQLError("Runtime must be a positive number of minutes.")

        clean_title = _sanitise(title)
        clean_director = _sanitise(input.director)
        clean_synopsis = _sanitise(input.synopsis)

        with get_connection() as conn:
            # Verify all genre_ids exist, if any were provided.
            if input.genre_ids:
                placeholders = ",".join(["?"] * len(input.genre_ids))
                existing = conn.execute(
                    f"SELECT id FROM genres WHERE id IN ({placeholders})",
                    [int(gid) for gid in input.genre_ids],
                ).fetchall()
                existing_ids = {row["id"] for row in existing}
                missing = [
                    gid for gid in input.genre_ids
                    if int(gid) not in existing_ids
                ]
                if missing:
                    raise GraphQLError(
                        f"Genre id(s) do not exist: {', '.join(map(str, missing))}"
                    )

            # Insert the movie.
            cursor = conn.execute(
                """
                INSERT INTO movies (title, release_year, runtime_minutes,
                                    director, synopsis)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    clean_title,
                    input.release_year,
                    input.runtime_minutes,
                    clean_director,
                    clean_synopsis,
                ),
            )
            new_id = cursor.lastrowid

            # Link the movie to the genres, if any.
            if input.genre_ids:
                conn.executemany(
                    "INSERT INTO movie_genres (movie_id, genre_id) VALUES (?, ?)",
                    [(new_id, int(gid)) for gid in input.genre_ids],
                )

            conn.commit()

            # Fetch and return the newly inserted movie.
            row = conn.execute(
                """
                SELECT id, title, release_year, runtime_minutes,
                       director, synopsis
                FROM movies
                WHERE id = ?
                """,
                (new_id,),
            ).fetchone()
            return _row_to_movie(row)