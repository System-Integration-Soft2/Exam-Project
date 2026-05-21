"""GraphQL mutations for write operations."""

import strawberry

from app.schema.inputs import CreateMovieInput, CreateReviewInput
from app.schema.types import Movie, Review, movie_from_row, review_from_row
from app.services import movies_service, review_service


def _id_to_int(value: strawberry.ID, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid integer ID.") from exc


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_movie(self, input: CreateMovieInput) -> Movie:
        row = movies_service.create(
            title=input.title,
            release_year=input.release_year,
            runtime_minutes=input.runtime_minutes,
            director=input.director,
            synopsis=input.synopsis,
            genre_ids=[
                _id_to_int(genre_id, "genreId")
                for genre_id in input.genre_ids
            ],
        )
        return movie_from_row(row)

    @strawberry.mutation
    def create_review(self, input: CreateReviewInput) -> Review:
        row = review_service.create(
            movie_id=_id_to_int(input.movie_id, "movieId"),
            user_id=_id_to_int(input.user_id, "userId"),
            rating=input.rating,
            comment=input.comment,
        )
        return review_from_row(row)