import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.utils.links import list_link, login_link
from app.models.common import LinksMap

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Application-level error that maps to a structured HTTP response.

    Instead of HTTPException so all error responses share the
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


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert AppError into the structured {detail, code, _links?} envelope."""
    links = exc.links

    if exc.status == 404 and links is None:
        links = list_link(request.url.path)

    if exc.status == 401:
        ll = login_link()
        if links is None:
            links = ll
        else:
            links = {**links, **ll}

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


# Maps known HTTPException status codes to envelope code strings.
# Unknown status codes fall back to "http_error".
_HTTP_EXCEPTION_CODES: dict[int, str] = {
    404: "not_found",
    405: "method_not_allowed",
    415: "unsupported_media_type",
}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert FastAPI/Starlette HTTPException into the structured envelope.

    404 responses include a best-effort _links.list entry so clients can
    navigate back to a known collection endpoint.
    """
    code = _HTTP_EXCEPTION_CODES.get(exc.status_code, "http_error")
    body: dict = {"detail": exc.detail, "code": code}

    if exc.status_code == 404:
        links = list_link(request.url.path)
        body["_links"] = {k: v.model_dump() for k, v in links.items()}

    return JSONResponse(status_code=exc.status_code, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for exceptions not covered by more specific handlers.

    Logs the full traceback at ERROR so the failure is visible in logs, then
    returns a sanitised 500 response that does not expose internal details.
    """
    logger.exception("Unhandled exception during request: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "internal_error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all structured envelope handlers on the FastAPI app."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
