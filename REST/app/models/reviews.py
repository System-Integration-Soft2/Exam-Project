from pydantic import BaseModel, Field

from app.models.common import LinksMap


class ReviewResponse(BaseModel):
    id: int
    movie_id: int
    user_id: int
    rating: int
    comment: str | None
    created_at: str
    links: LinksMap = Field(serialization_alias="_links")


class ReviewPage(BaseModel):
    items: list[ReviewResponse]
    page: int
    size: int
    total: int
    links: LinksMap = Field(serialization_alias="_links")
