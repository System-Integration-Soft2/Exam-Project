from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
import bcrypt

logger = logging.getLogger(__name__)


async def get_db_connection(db_path: str) -> aiosqlite.Connection:
    """Open an aiosqlite connection with foreign-key enforcement and a busy timeout."""
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db(settings, seed_sql_path: str = "seed.sql") -> None:
    """Initialise the database idempotently."""
    sql_path = Path(seed_sql_path)
    if not sql_path.exists():
        raise FileNotFoundError(
            f"seed.sql not found at {sql_path.resolve()}. "
            "Ensure the file is present at the configured path."
        )

    seed_sql = sql_path.read_text(encoding="utf-8")

    conn = await get_db_connection(settings.DATABASE_PATH)
    try:
        # Step 1: shared schema + seed data (idempotent for any service)
        await conn.executescript(seed_sql)
        await conn.commit()

        # Step 2: admin user (REST-specific; guarded by row count)
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        user_count = (await cursor.fetchone())[0]

        if user_count == 0:
            password_bytes = settings.SEED_ADMIN_PASSWORD.encode("utf-8")
            password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")
            await conn.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (?, ?, ?, 'admin')
                """,
                (settings.SEED_ADMIN_USERNAME, settings.SEED_ADMIN_EMAIL, password_hash),
            )
            await conn.commit()
            logger.info("Admin user '%s' seeded.", settings.SEED_ADMIN_USERNAME)
        else:
            logger.debug("Users table already populated; skipping admin seed.")

        # Step 3: sample reviews (REST-specific; guarded by row count)
        cursor = await conn.execute("SELECT COUNT(*) FROM reviews")
        review_count = (await cursor.fetchone())[0]

        if review_count == 0:
            cursor = await conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (settings.SEED_ADMIN_USERNAME,),
            )
            admin_row = await cursor.fetchone()
            if admin_row is not None:
                admin_id = admin_row[0]
                sample_reviews = [
                    (1, admin_id, 9, "A mind-bending masterpiece of science fiction."),
                    (2, admin_id, 10, "The definitive superhero film. Heath Ledger is unforgettable."),
                    (9, admin_id, 10, "A timeless classic. Brando is extraordinary."),
                    (5, admin_id, 9, "Groundbreaking visuals and a compelling story."),
                ]
                await conn.executemany(
                    "INSERT INTO reviews (movie_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
                    sample_reviews,
                )
                await conn.commit()
                logger.info("Sample reviews seeded.")
    finally:
        await conn.close()


def escape_like(term: str) -> str:
    """Escape user input for use in a SQLite LIKE clause with ESCAPE '\\'.

    Order matters: escape the backslash first, then percent and underscore,
    then wrap with % wildcards. Reversing the order would double-escape
    the newly introduced backslashes.
    """
    term = term.replace("\\", "\\\\")
    term = term.replace("%", "\\%")
    term = term.replace("_", "\\_")
    return f"%{term}%"


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    """FastAPI dependency that yields a per-request aiosqlite connection.

    The connection is closed automatically when the request completes,
    whether it succeeds or raises an exception.
    """
    from app.main import app  # local import to avoid circular dependency at module load

    conn = await get_db_connection(app.state.settings.DATABASE_PATH)
    try:
        yield conn
    finally:
        await conn.close()
