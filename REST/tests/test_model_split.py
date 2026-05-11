"""Tests for the per-resource model split (PART 1 reorganisation).

Verifies that each model is importable from its dedicated submodule AND
from the top-level app.models package re-export.
"""

from __future__ import annotations

import pytest


class TestCommonModels:
    def test_link_importable_from_common(self):
        from app.models.common import Link
        link = Link(href="/foo", method="GET")
        assert link.href == "/foo"
        assert link.method == "GET"

    def test_links_map_importable_from_common(self):
        from app.models.common import Link, LinksMap
        lm: LinksMap = {"self": Link(href="/foo", method="GET")}
        assert "self" in lm

    def test_error_response_importable_from_common(self):
        from app.models.common import ErrorResponse
        err = ErrorResponse(detail="oops", code="err")
        assert err.detail == "oops"
        assert err.code == "err"


class TestAuthModels:
    def test_token_pair_importable_from_auth(self):
        from app.models.auth import TokenPair
        tp = TokenPair(access_token="a", refresh_token="r", expires_in=900)
        assert tp.token_type == "bearer"

    def test_refresh_request_importable_from_auth(self):
        from app.models.auth import RefreshRequest
        rr = RefreshRequest(refresh_token="x" * 20)
        assert rr.refresh_token == "x" * 20

    def test_logout_request_importable_from_auth(self):
        from app.models.auth import LogoutRequest
        lr = LogoutRequest(refresh_token="y" * 20)
        assert lr.refresh_token == "y" * 20

    def test_user_internal_importable_from_auth(self):
        from app.models.auth import UserInternal
        u = UserInternal(id=1, username="alice", email="alice@example.com", role="user")
        assert u.role == "user"


class TestMovieModels:
    def test_movie_request_importable_from_movies(self):
        from app.models.movies import MovieRequest
        mr = MovieRequest(title="Test", release_year=2020, genre_ids=[])
        assert mr.title == "Test"

    def test_movie_response_importable_from_movies(self):
        from app.models.movies import MovieResponse
        from app.models.common import Link
        resp = MovieResponse(
            id=1,
            title="Test",
            release_year=2020,
            runtime_minutes=None,
            director=None,
            synopsis=None,
            genres=[],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            links={"self": Link(href="/api/v1/movies/1", method="GET")},
        )
        assert resp.id == 1

    def test_movie_page_importable_from_movies(self):
        from app.models.movies import MoviePage
        from app.models.common import Link
        page = MoviePage(
            items=[],
            page=1,
            size=20,
            total=0,
            links={"self": Link(href="/api/v1/movies?page=1&size=20", method="GET"),
                   "first": Link(href="/api/v1/movies?page=1&size=20", method="GET"),
                   "last": Link(href="/api/v1/movies?page=1&size=20", method="GET")},
        )
        assert page.total == 0


class TestGenreModels:
    def test_genre_response_importable_from_genres(self):
        from app.models.genres import GenreResponse
        from app.models.common import Link
        gr = GenreResponse(
            id=1,
            name="Action",
            links={"self": Link(href="/api/v1/genres/1", method="GET")},
        )
        assert gr.name == "Action"

    def test_genre_page_importable_from_genres(self):
        from app.models.genres import GenrePage
        from app.models.common import Link
        gp = GenrePage(
            items=[],
            page=1,
            size=20,
            total=0,
            links={"self": Link(href="/api/v1/genres?page=1&size=20", method="GET"),
                   "first": Link(href="/api/v1/genres?page=1&size=20", method="GET"),
                   "last": Link(href="/api/v1/genres?page=1&size=20", method="GET")},
        )
        assert gp.total == 0


class TestTopLevelReExports:
    """All models must be importable from app.models directly."""

    def test_all_models_importable_from_package(self):
        from app.models import (
            Link, LinksMap, ErrorResponse,
            TokenPair, RefreshRequest, LogoutRequest, UserInternal,
            MovieRequest, MovieResponse, MoviePage,
            GenreResponse, GenrePage,
        )
        # Spot-check one from each submodule
        assert Link is not None
        assert TokenPair is not None
        assert MovieRequest is not None
        assert GenreResponse is not None

    def test_movie_response_genres_uses_genre_response(self):
        """MovieResponse.genres is typed as list[GenreResponse] — cross-module import."""
        from app.models.movies import MovieResponse
        from app.models.genres import GenreResponse
        from app.models.common import Link
        genre = GenreResponse(
            id=2,
            name="Drama",
            links={"self": Link(href="/api/v1/genres/2", method="GET")},
        )
        resp = MovieResponse(
            id=5,
            title="Drama Film",
            release_year=2021,
            runtime_minutes=120,
            director="Dir",
            synopsis=None,
            genres=[genre],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            links={"self": Link(href="/api/v1/movies/5", method="GET")},
        )
        assert resp.genres[0].name == "Drama"
