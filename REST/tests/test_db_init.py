"""Tests for database initialisation: schema creation, idempotency, and seed data."""

import re
from pathlib import Path
import pytest
import aiosqlite
import bcrypt

from tests.conftest import TEST_JWT_SECRET


# seed.sql lives at repo root; tests run from REST/, so go two levels up.
SEED_SQL_PATH = str(Path(__file__).parent.parent.parent / "seed.sql")


def make_settings(tmp_path, monkeypatch):
    """Build a Settings instance pointing at a temp database."""
    db_path = str(tmp_path / "test_catalog.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")
    from app.utils.config import Settings
    return Settings(_env_file=None)


async def test_init_db_first_run_creates_schema(tmp_path, monkeypatch):
    """Running init_db on a fresh file creates all five expected tables."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}

    expected = {"users", "genres", "movies", "movie_genres", "reviews"}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


async def test_init_db_second_run_is_idempotent(tmp_path, monkeypatch):
    """Calling init_db twice on the same database raises no errors and keeps row counts stable."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        count_before = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM genres")
        genres_before = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM movies")
        movies_before = (await cursor.fetchone())[0]

    # Second run must be a no-op
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM users")
        count_after = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM genres")
        genres_after = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM movies")
        movies_after = (await cursor.fetchone())[0]

    assert count_after == count_before, "User count changed on second init_db run"
    assert genres_after == genres_before, "Genre count changed on second init_db run"
    assert movies_after == movies_before, "Movie count changed on second init_db run"


async def test_admin_seeded_with_bcrypt_direct_hash(tmp_path, monkeypatch):
    """Admin user is seeded and the stored hash is verifiable via bcrypt.checkpw."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT password_hash, role FROM users WHERE username = ?",
            (settings.SEED_ADMIN_USERNAME,),
        )
        row = await cursor.fetchone()

    assert row is not None, "Admin user was not seeded"
    password_hash, role = row
    assert role == "admin"
    assert bcrypt.checkpw(
        settings.SEED_ADMIN_PASSWORD.encode(),
        password_hash.encode(),
    ), "Stored hash does not verify against the configured admin password"


async def test_created_at_uses_T_separator(tmp_path, monkeypatch):
    """created_at timestamps stored by init_db use the ISO 8601 T separator."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT created_at FROM users WHERE username = ?",
            (settings.SEED_ADMIN_USERNAME,),
        )
        row = await cursor.fetchone()

    assert row is not None
    created_at = row[0]
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", created_at), (
        f"created_at does not match T-separator format: {created_at!r}"
    )


async def test_updated_at_uses_T_separator(tmp_path, monkeypatch):
    """updated_at timestamps stored by init_db use the ISO 8601 T separator."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT updated_at FROM users WHERE username = ?",
            (settings.SEED_ADMIN_USERNAME,),
        )
        row = await cursor.fetchone()

    assert row is not None
    updated_at = row[0]
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", updated_at), (
        f"updated_at does not match T-separator format: {updated_at!r}"
    )


async def test_seed_genres_present(tmp_path, monkeypatch):
    """Exactly 5 genres are seeded: Action, Drama, Sci-Fi, Comedy, Thriller."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT name FROM genres ORDER BY name")
        genres = {row[0] for row in await cursor.fetchall()}

    expected = {"Action", "Drama", "Sci-Fi", "Comedy", "Thriller"}
    assert genres == expected, f"Unexpected genres: {genres}"


async def test_seed_movies_present(tmp_path, monkeypatch):
    """At least 10 movies are seeded."""
    from app.utils.db import init_db

    settings = make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM movies")
        count = (await cursor.fetchone())[0]

    assert count >= 10, f"Expected at least 10 seeded movies, got {count}"
