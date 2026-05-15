"""
GraphQL input types for mutations.

Input types (defined with @strawberry.input) are a separate kind of
type in the GraphQL specification — they describe data that CLIENTS
send to the server, distinct from the output types in types.py that
describe data the server RETURNS to clients.

Per the GraphQL spec, input types have stricter rules than output
types: they cannot have resolvers, cannot have arguments on fields,
and cannot reference output types (only other input types).
"""

from typing import Optional
import strawberry


@strawberry.input
class AddReviewInput:
    """Input for creating a new review."""
    movie_id: strawberry.ID
    user_id: strawberry.ID
    rating: int
    comment: Optional[str] = None


@strawberry.input
class AddMovieInput:
    """Input for creating a new movie."""
    title: str
    release_year: int
    runtime_minutes: Optional[int] = None
    director: Optional[str] = None
    synopsis: Optional[str] = None
    genre_ids: Optional[list[strawberry.ID]] = None