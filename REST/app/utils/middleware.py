"""Security headers middleware.

Injects X-Content-Type-Options and Content-Security-Policy on every response.
Doc routes (/docs, /openapi.json, /redoc) receive a relaxed CSP that permits
the Swagger/ReDoc CDN and inline scripts; all other routes receive a strict CSP.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Paths that serve Swagger UI or ReDoc — these need a relaxed CSP to load
# CDN-hosted assets and inline bootstrap scripts.
_DOCS_PATHS = {"/docs", "/openapi.json", "/redoc"}

# Strict CSP for all non-doc endpoints: no scripts, no styles, no external resources.
_STRICT_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

# Relaxed CSP for doc endpoints: permits the Swagger/ReDoc CDN, inline scripts and styles
_DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; "
    "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add X-Content-Type-Options and Content-Security-Policy to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        csp = _DOCS_CSP if request.url.path in _DOCS_PATHS else _STRICT_CSP
        response.headers["Content-Security-Policy"] = csp
        return response
