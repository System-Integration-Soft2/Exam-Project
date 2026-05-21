"""
Database connection management for the GraphQL API.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


# Absolute path to catalog.db, independent of the working directory.
DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "catalog.db"


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