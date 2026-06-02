"""
Database connection management for the GraphQL API.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# DATABASE_PATH Docker via .env
# catalog.db local dev from repo root
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "catalog.db"
DB_PATH = Path(os.environ.get("DATABASE_PATH", _DEFAULT_DB_PATH))

if not DB_PATH.is_file():
    raise FileNotFoundError(
        f"Database not found at {DB_PATH}. "
        "Set DATABASE_PATH or ensure catalog.db exists at the repo root."
    )


def get_connection() -> sqlite3.Connection:
    """Open a new SQLite connection with row factory and FKs enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """
    Yield a SQLite connection scoped to a single operation.

    Auto-commits on success, auto-rollbacks on exception.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()