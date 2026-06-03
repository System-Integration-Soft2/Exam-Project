import html
import re

MAX_COMMENT_LEN = 2000


def sanitize_output(value: str | None) -> str:
    if value is None:
        return ""
    return html.escape(value, quote=True)


def validate_movie_id(movie_id: int) -> None:
    if not isinstance(movie_id, int) or movie_id <= 0:
        raise ValueError(f"movie_id must be a positive integer, got: {movie_id!r}")


def validate_rating(rating: int) -> None:
    if not isinstance(rating, int) or not 1 <= rating <= 10:
        raise ValueError(f"rating must be an integer between 1 and 10, got: {rating!r}")


def validate_comment(comment: str | None) -> str:
    if comment is None:
        return ""
    if len(comment) > MAX_COMMENT_LEN:
        raise ValueError(f"comment must be {MAX_COMMENT_LEN} characters or fewer")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", comment)
