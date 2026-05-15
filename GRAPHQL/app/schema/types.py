"""
GraphQL object types and input types for the movie catalog API.

Each @strawberry.type class becomes a GraphQL object type in the SDL.
Nested fields use @strawberry.field with a resolver function so they
are only fetched when the client actually requests them — this is how
GraphQL avoids the overfetching problem REST suffers from.

Note on N+1 queries:
    When resolving a list (e.g. all movies) and the client asks for
    nested data (e.g. each movie's reviews), Strawberry calls the
    reviews-resolver once per movie. For our 10-movie catalog this is
    fine. In production, a DataLoader would batch these into a single
    SQL query — but that's optimisation we don't need here.
"""

from typing import Optional
import strawberry

from app.utils.db import get_connection


# ---------------------------------------------------------------------
# ReviewAuthor: a deliberately narrow view of the users table.
#
# The users table contains email, password_hash, and role — fields that
# must NEVER be exposed via GraphQL. By defining a separate type that
# only includes id and username, we enforce field-level access control
# at the schema layer: there is no way for a client to request fields
# that don't exist in the type.
# ---------------------------------------------------------------------
@strawberry.type
class ReviewAuthor:
    """The author of a review — only public-safe fields exposed."""
    id: strawberry.ID
    username: str


# ---------------------------------------------------------------------
# Genre: a movie genre.
#
# The `movies` field is a back-reference: from a genre you can navigate
# to all movies of that genre. This is what makes GraphQL a graph —
# relationships are traversable in both directions.
# ---------------------------------------------------------------------
@strawberry.type
class Genre:
    """A movie genre (e.g. Action, Drama, Sci-Fi)."""
    id: strawberry.ID
    name: str

    @strawberry.field
    def movies(self) -> list["Movie"]:
        """All movies belonging to this genre. Resolved lazily."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT m.id, m.title, m.release_year, m.runtime_minutes,
                       m.director, m.synopsis
                FROM movies m
                JOIN movie_genres mg ON mg.movie_id = m.id
                WHERE mg.genre_id = ?
                ORDER BY m.release_year DESC
                """,
                (self.id,),
            ).fetchall()
            return [_row_to_movie(row) for row in rows]


# ---------------------------------------------------------------------
# Review: a user's rating and comment on a movie.
#
# The `movie` and `user` fields are resolved lazily — they only hit
# the database if the client asks for them.
# ---------------------------------------------------------------------
@strawberry.type
class Review:
    """A user's rating (1-10) and optional comment on a movie."""
    id: strawberry.ID
    rating: int
    comment: Optional[str]
    created_at: str

    # Internal fields — not exposed in GraphQL, used to resolve
    # the nested `movie` and `user` fields below.
    _movie_id: strawberry.Private[int]
    _user_id: strawberry.Private[int]

    @strawberry.field
    def movie(self) -> "Movie":
        """The movie this review belongs to."""
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, release_year, runtime_minutes,
                       director, synopsis
                FROM movies
                WHERE id = ?
                """,
                (self._movie_id,),
            ).fetchone()
            return _row_to_movie(row)

    @strawberry.field
    def user(self) -> ReviewAuthor:
        """The author of this review. Only id and username are exposed."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, username FROM users WHERE id = ?",
                (self._user_id,),
            ).fetchone()
            return ReviewAuthor(id=strawberry.ID(str(row["id"])), username=row["username"])


# ---------------------------------------------------------------------
# Movie: the central type. Has nested genres, reviews, and a computed
# averageRating field.
# ---------------------------------------------------------------------
@strawberry.type
class Movie:
    """A movie in the catalog."""
    id: strawberry.ID
    title: str
    release_year: int
    runtime_minutes: Optional[int]
    director: Optional[str]
    synopsis: Optional[str]

    @strawberry.field
    def genres(self) -> list[Genre]:
        """The genres this movie belongs to. Resolved lazily."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT g.id, g.name
                FROM genres g
                JOIN movie_genres mg ON mg.genre_id = g.id
                WHERE mg.movie_id = ?
                ORDER BY g.name
                """,
                (self.id,),
            ).fetchall()
            return [Genre(id=strawberry.ID(str(r["id"])), name=r["name"]) for r in rows]

    @strawberry.field
    def reviews(self) -> list[Review]:
        """All reviews for this movie, newest first. Resolved lazily."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, movie_id, user_id, rating, comment, created_at
                FROM reviews
                WHERE movie_id = ?
                ORDER BY created_at DESC
                """,
                (self.id,),
            ).fetchall()
            return [_row_to_review(row) for row in rows]

    @strawberry.field
    def average_rating(self) -> Optional[float]:
        """
        The average rating across all reviews for this movie.

        Computed on demand — there is no averageRating column in the
        database. Returns None if the movie has no reviews yet.
        This demonstrates a GraphQL field that doesn't map directly
        to a database column.
        """
        with get_connection() as conn:
            row = conn.execute(
                "SELECT AVG(rating) AS avg FROM reviews WHERE movie_id = ?",
                (self.id,),
            ).fetchone()
            return float(row["avg"]) if row["avg"] is not None else None


# ---------------------------------------------------------------------
# Internal helpers — convert sqlite3.Row to Strawberry types.
#
# These are not GraphQL types; they exist to avoid duplicating the
# row-to-type mapping code in every resolver. The underscore prefix
# is a Python convention meaning "module-private".
# ---------------------------------------------------------------------
def _row_to_movie(row) -> Movie:
    """Convert a sqlite3.Row from the movies table to a Movie type."""
    return Movie(
        id=strawberry.ID(str(row["id"])),
        title=row["title"],
        release_year=row["release_year"],
        runtime_minutes=row["runtime_minutes"],
        director=row["director"],
        synopsis=row["synopsis"],
    )


def _row_to_review(row) -> Review:
    """Convert a sqlite3.Row from the reviews table to a Review type."""
    return Review(
        id=strawberry.ID(str(row["id"])),
        rating=row["rating"],
        comment=row["comment"],
        created_at=row["created_at"],
        _movie_id=row["movie_id"],
        _user_id=row["user_id"],
    )