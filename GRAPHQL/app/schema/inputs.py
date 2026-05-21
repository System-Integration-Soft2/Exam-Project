"""
GraphQL input types for mutations.

Input types describe data clients send to the GraphQL API.
They are separate from output types and contain no resolvers or SQL.
"""

from typing import Optional

import strawberry


@strawberry.input
class CreateReviewInput:
    """Input for creating a review."""

    movie_id: strawberry.ID
    user_id: strawberry.ID
    rating: int
    comment: Optional[str] = None


@strawberry.input
class CreateMovieInput:
    """Input for creating a movie."""

    title: str
    release_year: int
    runtime_minutes: Optional[int] = None
    director: Optional[str] = None
    synopsis: Optional[str] = None
    genre_ids: list[strawberry.ID] = strawberry.field(default_factory=list)