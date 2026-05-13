from pydantic import BaseModel, Field

from app.models.common import LinksMap
from app.models.genres import GenreResponse


class MovieRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    release_year: int = Field(ge=1888, le=2100)
    runtime_minutes: int | None = Field(default=None, gt=0)
    director: str | None = Field(default=None, max_length=255)
    synopsis: str | None = Field(default=None, max_length=5000)
    genre_ids: list[int] = Field(default_factory=list, max_length=20)


class MovieResponse(BaseModel):
    id: int
    title: str
    release_year: int
    runtime_minutes: int | None
    director: str | None
    synopsis: str | None
    genres: list[GenreResponse]
    created_at: str
    updated_at: str
    links: LinksMap = Field(serialization_alias="_links")


class MoviePage(BaseModel):
    items: list[MovieResponse]
    page: int
    size: int
    total: int
    links: LinksMap = Field(serialization_alias="_links")
