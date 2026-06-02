"""
Database connection management for the GraphQL API.
"""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_DB_CANDIDATES = (
    _REPO_ROOT / "data" / "catalog.db",
    _REPO_ROOT / "catalog.db",
)

_configured_db_path = os.environ.get("DATABASE_PATH")
if _configured_db_path:
    DB_PATH = Path(_configured_db_path)
else:
    DB_PATH = next((path for path in _DEFAULT_DB_CANDIDATES if path.is_file()), _DEFAULT_DB_CANDIDATES[0])

if not DB_PATH.is_file():
    raise FileNotFoundError(
        f"Database not found at {DB_PATH}. "
        "Set DATABASE_PATH or ensure catalog.db exists at the repo root or data/catalog.db."
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