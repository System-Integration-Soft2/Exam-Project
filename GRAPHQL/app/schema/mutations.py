"""GraphQL mutations for write operations.

Two write operations on the movie catalog: addMovie and updateMovie.
Both return the resulting Movie so the client can request whatever
fields it needs in the same request (e.g. the new id, or the updated
genre list).

updateMovie does a partial update: any field left out keeps its
existing value. The client only needs to send what it wants to change.
"""

from typing import Optional

import strawberry

from app.schema.types import Movie, movie_from_row
from app.services import movies_service


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
        """Create a movie and optionally link it to genres."""
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
    def update_movie(
        self,
        id: strawberry.ID,
        title: Optional[str] = None,
        release_year: Optional[int] = None,
        runtime_minutes: Optional[int] = None,
        director: Optional[str] = None,
        synopsis: Optional[str] = None,
        genre_ids: Optional[list[strawberry.ID]] = None,
    ) -> Movie:
        """Partial update. Any argument left out keeps its existing value.
        Pass genre_ids to replace the movie's genre links; omit it to keep them."""
        row = movies_service.update(
            movie_id=int(id),
            title=title,
            release_year=release_year,
            runtime_minutes=runtime_minutes,
            director=director,
            synopsis=synopsis,
            genre_ids=[int(gid) for gid in genre_ids] if genre_ids is not None else None,
        )
        return movie_from_row(row)