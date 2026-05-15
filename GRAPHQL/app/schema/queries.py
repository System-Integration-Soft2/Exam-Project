"""
GraphQL Query type — the entry point for all read operations.

The Query class below becomes the root `type Query { ... }` in the SDL.
Each @strawberry.field on the class becomes a top-level query that
clients can call.

Two queries are defined here:

  - movie(id: ID!): fetches a single movie by id, or returns null
    if it doesn't exist (GraphQL convention for "not found").

  - movies(...): returns a list of movies with optional filtering
    (genre, year, search) and pagination (limit, offset).
"""

from typing import Optional
import strawberry

from app.utils.db import get_connection
from app.schema.types import Movie, _row_to_movie


@strawberry.type
class Query:
    """Root Query type — all read operations live here."""

    # -----------------------------------------------------------------
    # Query 1: fetch a single movie by id.
    #
    # Returns Optional[Movie] (i.e. Movie or null in GraphQL terms).
    # If the id doesn't exist, we return None — the client sees
    # `{"data": {"movie": null}}` rather than an error.
    # -----------------------------------------------------------------
    @strawberry.field
    def movie(self, id: strawberry.ID) -> Optional[Movie]:
        """Fetch a single movie by id, or null if not found."""
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, title, release_year, runtime_minutes,
                       director, synopsis
                FROM movies
                WHERE id = ?
                """,
                (int(id),),
            ).fetchone()

            if row is None:
                return None
            return _row_to_movie(row)

    # -----------------------------------------------------------------
    # Query 2: fetch a list of movies with optional filtering
    # and pagination.
    #
    # All arguments are optional. The default values (limit=20,
    # offset=0) become defaults in the SDL.
    #
    # SQL-injection note:
    #   The WHERE clause is built dynamically based on which filters
    #   the client provided, but EVERY user value is passed as a
    #   parameter (`?`), never concatenated into the query string.
    #   The dynamic part only adds clause TEMPLATES, never data.
    # -----------------------------------------------------------------
    @strawberry.field
    def movies(
        self,
        genre: Optional[str] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Movie]:
        """
        Return a list of movies, filtered and paginated.

        Args:
            genre:  filter on genre name (e.g. "Sci-Fi"). Case-sensitive.
            year:   filter on release year (exact match).
            search: case-insensitive substring search on title.
            limit:  max number of rows to return (1-100, default 20).
            offset: how many rows to skip, for pagination (default 0).
        """
        # Defensive: clamp limit to a safe range. Without this, a
        # client could request limit=1000000 and exhaust server
        # resources. This is part of our GraphQL DoS protection.
        if limit < 1:
            limit = 1
        elif limit > 100:
            limit = 100
        if offset < 0:
            offset = 0

        # Build the WHERE clause dynamically based on which filters
        # were provided. Each filter contributes a clause template
        # AND a parameter — the parameters go into a list, the
        # templates into a string.
        where_clauses: list[str] = []
        params: list = []

        if genre is not None:
            where_clauses.append(
                "id IN (SELECT mg.movie_id FROM movie_genres mg "
                "JOIN genres g ON g.id = mg.genre_id WHERE g.name = ?)"
            )
            params.append(genre)

        if year is not None:
            where_clauses.append("release_year = ?")
            params.append(year)

        if search is not None:
            where_clauses.append("LOWER(title) LIKE ?")
            params.append(f"%{search.lower()}%")

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        sql = f"""
            SELECT id, title, release_year, runtime_minutes,
                   director, synopsis
            FROM movies
            {where_sql}
            ORDER BY release_year DESC, title ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        with get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [_row_to_movie(row) for row in rows]