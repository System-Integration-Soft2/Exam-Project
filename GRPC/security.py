"""
Security helpers for the gRPC catalog service.

XSS prevention:
  Even though gRPC doesn't render HTML directly, our string fields can
  end up in web frontends or logs. We escape HTML special characters in
  every outgoing string field, so any malicious script tag stored in the
  database becomes inert text on the consumer side.

CSRF: see README — gRPC is not vulnerable to CSRF because it does not
  use cookies for authentication and browsers cannot send cross-origin
  gRPC requests with the binary content-type required by the protocol.
"""

import html
import re

# Maximum lengths for input strings — protects against oversized payloads
MAX_COMMENT_LEN = 2000
MAX_TITLE_LEN = 500


def sanitize_output(value: str | None) -> str:
    """Escape HTML so any stored <script> becomes harmless text."""
    if value is None:
        return ""
    return html.escape(value, quote=True)


def validate_movie_id(movie_id: int) -> None:
    """Raise ValueError on invalid input."""
    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError(f"movie_id must be a positive integer, got: {movie_id!r}")


def validate_rating(rating: int) -> None:
    if not isinstance(rating, int) or not 1 <= rating <= 10:
        raise ValueError(f"rating must be an integer between 1 and 10, got: {rating!r}")


def validate_comment(comment: str | None) -> str:
    """Reject overly long comments and strip control characters."""
    if comment is None:
        return ""
    if len(comment) > MAX_COMMENT_LEN:
        raise ValueError(f"comment must be {MAX_COMMENT_LEN} characters or fewer")
    # Strip ASCII control characters (except tab/newline/carriage-return)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", comment)