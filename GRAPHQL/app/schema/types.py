"""
GraphQL output types for the movie catalog API.

Types describe the public GraphQL schema.
Services fetch database rows (returned as plain dicts).
Mapper functions convert rows to Strawberry types.

Nested fields (@strawberry.field) are resolved lazily: a client that
asks only for `movie { title }` never triggers genre or review queries.
The bidirectional traversal (Movie -> Genre -> Movie) is safe because
QueryDepthLimiter caps document depth at 10 (see app.config).
"""

from __future__ import annotations

from typing import Optional

import strawberry

from app.services import genre_service, movies_service, review_service


@strawberry.type
class ReviewAuthor:
    """Public author information for a review."""

    id: strawberry.ID
    username: str


@strawberry.type
class RatingSummary:
    """Rating count and average for a movie."""

    count: int
    average: Optional[float]


@strawberry.type
class Genre:
    """A movie genre."""

    id: strawberry.ID
    name: str

    @strawberry.field
    def movies(self) -> list[Movie]:
        """All movies belonging to this genre. Resolved lazily."""
        rows = movies_service.get_by_genre_id(int(self.id))
        return [movie_from_row(row) for row in rows]


@strawberry.type
class Review:
    """A user's review of a movie."""

    id: strawberry.ID
    rating: int
    comment: Optional[str]
    created_at: str

    _movie_id: strawberry.Private[int]
    _user_id: strawberry.Private[int]

    @strawberry.field
    def movie(self) -> Movie:
        row = movies_service.get_by_id(self._movie_id)
        return movie_from_row(row)

    @strawberry.field
    def user(self) -> ReviewAuthor:
        row = review_service.get_author(self._user_id)
        return ReviewAuthor(
            id=strawberry.ID(str(row["id"])),
            username=row["username"],
        )


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
        rows = genre_service.get_genres_by_movie_id(int(self.id))
        return [genre_from_row(row) for row in rows]

    @strawberry.field
    def reviews(self) -> list[Review]:
        rows = review_service.get_by_movie_id(int(self.id))
        return [review_from_row(row) for row in rows]

    @strawberry.field
    def rating_summary(self) -> RatingSummary:
        row = movies_service.get_rating_summary(int(self.id))
        return RatingSummary(count=row["count"], average=row["average"])


# --- dict -> type mappers --------------------------------------------------


def movie_from_row(row) -> Movie:
    return Movie(
        id=strawberry.ID(str(row["id"])),
        title=row["title"],
        release_year=row["release_year"],
        runtime_minutes=row["runtime_minutes"],
        director=row["director"],
        synopsis=row["synopsis"],
    )


def genre_from_row(row) -> Genre:
    return Genre(
        id=strawberry.ID(str(row["id"])),
        name=row["name"],
    )


def review_from_row(row) -> Review:
    return Review(
        id=strawberry.ID(str(row["id"])),
        rating=row["rating"],
        comment=row["comment"],
        created_at=row["created_at"],
        _movie_id=row["movie_id"],
        _user_id=row["user_id"],
    )