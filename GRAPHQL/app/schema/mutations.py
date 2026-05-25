"""GraphQL mutations for write operations."""

from typing import Optional

import strawberry

from app.schema.types import Movie, Review, movie_from_row, review_from_row
from app.services import movies_service, review_service

# Reviews are attributed to a fixed seed user because this GraphQL service
# has no authentication (auth lives in the REST service). In a real system
# the user would come from an authenticated request context.
SEED_USER_ID = 1


@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_movie(
        self,
        title: str,
        release_year: int,
        runtime_minutes: Optional[int] = None,
        director: Optional[str] = None,
        synopsis: Optional[str] = None,
        genre_ids: Optional[list[strawberry.ID]] = None,
    ) -> Movie:
        row = movies_service.create(
            title=title,
            release_year=release_year,
            runtime_minutes=runtime_minutes,
            director=director,
            synopsis=synopsis,
            genre_ids=[int(gid) for gid in (genre_ids or [])],
        )
        return movie_from_row(row)

    @strawberry.mutation
    def add_review(
        self,
        movie_id: strawberry.ID,
        rating: int,
        comment: Optional[str] = None,
    ) -> Review:
        if not 1 <= rating <= 10:
            raise ValueError("rating must be between 1 and 10")

        row = review_service.create(
            movie_id=int(movie_id),
            user_id=SEED_USER_ID,
            rating=rating,
            comment=comment,
        )
        return review_from_row(row)

    @strawberry.mutation
    def delete_review(self, id: strawberry.ID) -> Optional[Review]:
        """Delete a review and return what was deleted. Returns null if not found."""
        row = review_service.delete(int(id))
        if row is None:
            return None
        return review_from_row(row)