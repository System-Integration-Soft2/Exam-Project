"""GraphQL queries for read operations."""

from typing import Optional

import strawberry

from app.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schema.types import Movie, movie_from_row
from app.services import movies_service


@strawberry.type
class Query:
    @strawberry.field
    def movie(self, id: strawberry.ID) -> Optional[Movie]:
        row = movies_service.get_by_id(int(id))
        if row is None:
            return None
        return movie_from_row(row)

    @strawberry.field
    def movies(
        self,
        genre: Optional[str] = None,
        year: Optional[int] = None,
        limit: int = DEFAULT_PAGE_SIZE,
        offset: int = 0,
    ) -> list[Movie]:
        # Clamp pagination to safe bounds. See app.config for rationale.
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        offset = max(0, offset)

        rows = movies_service.get_all(
            genre=genre,
            year=year,
            limit=limit,
            offset=offset,
        )
        return [movie_from_row(row) for row in rows]