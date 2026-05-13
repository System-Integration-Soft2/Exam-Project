"""Pydantic models for requests, responses, and HATEOAS links."""

from app.models.common import Link, LinksMap, ErrorResponse
from app.models.auth import TokenPair, RefreshRequest, LogoutRequest, UserInternal
from app.models.movies import MovieRequest, MovieResponse, MoviePage
from app.models.genres import GenreResponse, GenrePage
from app.models.reviews import ReviewResponse, ReviewPage

__all__ = [
    "Link", "LinksMap", "ErrorResponse",
    "TokenPair", "RefreshRequest", "LogoutRequest", "UserInternal",
    "MovieRequest", "MovieResponse", "MoviePage",
    "GenreResponse", "GenrePage",
    "ReviewResponse", "ReviewPage",
]
