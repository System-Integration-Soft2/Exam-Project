from __future__ import annotations
import re
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.models import Link, LinksMap


class AppError(Exception):
    """Application-level error that maps to a structured HTTP response.

    Raise this instead of HTTPException so all error responses share the
    same {detail, code, _links?, errors?} envelope.
    """

    def __init__(
        self,
        code: str,
        detail: str,
        status: int,
        links: LinksMap | None = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status
        self.links = links


def _build_list_link(path: str) -> LinksMap:
    """Build a _links.list entry by stripping the trailing /{id} segment from path."""
    # Strip trailing path segment that looks like an ID (numeric or slug)
    list_path = re.sub(r"/[^/]+$", "", path) or path
    return {"list": Link(href=list_path, method="GET")}


def _build_login_link() -> LinksMap:
    """Build a _links.login entry pointing at the login endpoint."""
    return {"login": Link(href="/api/v1/auth/login", method="POST")}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert AppError into the structured {detail, code, _links?} envelope."""
    links = exc.links

    if exc.status == 404 and links is None:
        links = _build_list_link(request.url.path)

    if exc.status == 401:
        login_link = _build_login_link()
        if links is None:
            links = login_link
        else:
            links = {**links, **login_link}

    body: dict = {"detail": exc.detail, "code": exc.code}
    if links is not None:
        body["_links"] = {k: v.model_dump() for k, v in links.items()}

    return JSONResponse(status_code=exc.status, content=body)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Convert Pydantic RequestValidationError into the structured envelope with errors[]."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "code": "validation_error",
            "errors": exc.errors(),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register AppError and RequestValidationError handlers on the FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
