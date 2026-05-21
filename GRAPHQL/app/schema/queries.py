"""GraphQL queries for read operations."""

from typing import Optional

import strawberry

from app.schema.types import Movie, movie_from_row
from app.services import movies_service


@strawberry.type
class Query:
    @strawberry.field
    def movie(self, id: strawberry.ID) -> Optional[Movie]:
        row = movies_service.get_by_id(int(str(id)))

        if row is None:
            return None

        return movie_from_row(row)

    @strawberry.field
    def movies(
        self,
        genre: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Movie]:
        rows = movies_service.get_all(
            genre=genre,
            year=year,
            search=search,
            limit=limit,
            offset=offset,
        )

        return [movie_from_row(row) for row in rows]