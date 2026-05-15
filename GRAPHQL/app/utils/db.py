"""
Database connection management for the GraphQL API.

This module is the SOLE location in the codebase that knows where the
SQLite database lives on disk. All other modules request a connection
via get_connection() and remain agnostic of the underlying path.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


# Resolve the absolute path to catalog.db, independent of the working
# directory the server was started from.
#
# __file__ = .../GRAPHQL/app/utils/db.py
# .parent  = .../GRAPHQL/app/utils
# .parent  = .../GRAPHQL/app
# .parent  = .../GRAPHQL
# .parent  = .../Exam-Project  (repo root, where catalog.db lives)
DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "catalog.db"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """
    Yield a SQLite connection scoped to a single GraphQL operation.

    Usage:
        with get_connection() as conn:
            rows = conn.execute("SELECT ...").fetchall()

    The connection is closed automatically on exit, even if an
    exception is raised inside the `with` block.

    Notes:
        - row_factory = sqlite3.Row lets us access columns by name
          (row["title"]) instead of by index (row[0]). Cleaner code,
          easier to read at the exam.
        - PRAGMA foreign_keys = ON is required on every new connection
          because SQLite disables FK enforcement by default.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()