from pydantic import BaseModel, Field

from app.models.common import LinksMap


class GenreResponse(BaseModel):
    id: int
    name: str
    links: LinksMap = Field(serialization_alias="_links")


class GenrePage(BaseModel):
    items: list[GenreResponse]
    page: int
    size: int
    total: int
    links: LinksMap = Field(serialization_alias="_links")
