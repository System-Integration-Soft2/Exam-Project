"""
GraphQL output types for the movie catalog API.

Types describe the public GraphQL schema.
Services fetch database rows.
Mapper functions convert rows to Strawberry types.

"""

from __future__ import annotations

from typing import Optional

import strawberry

from app.services import genre_service, movies_service


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
        """All genres this movie belongs to. Resolved lazily."""
        rows = genre_service.get_genres_by_movie_id(int(self.id))
        return [genre_from_row(row) for row in rows]


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