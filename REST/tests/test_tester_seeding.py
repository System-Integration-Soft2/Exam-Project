"""Tests for tester user seeding in init_db() (PART 3 reorganisation).

Verifies that init_db() seeds the fixture tester user automatically,
without any external script invocation.
"""

from pathlib import Path

import aiosqlite
import bcrypt
import pytest

from tests.conftest import TEST_JWT_SECRET

SEED_SQL_PATH = str(Path(__file__).parent.parent.parent / "seed.sql")


def _make_settings(tmp_path, monkeypatch):
    db_path = str(tmp_path / "tester_seed_test.db")
    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("SEED_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("SEED_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("SEED_ADMIN_PASSWORD", "admin123")
    from app.config import Settings
    return Settings(_env_file=None)


async def test_init_db_seeds_tester_user(tmp_path, monkeypatch):
    """init_db() must create a 'tester' user with role='user' automatically."""
    from app.utils.db import init_db

    settings = _make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT username, email, role, password_hash FROM users WHERE username = 'tester'"
        )
        row = await cursor.fetchone()

    assert row is not None, "tester user was not seeded by init_db()"
    assert row["username"] == "tester"
    assert row["email"] == "tester@example.com"
    assert row["role"] == "user"
    assert bcrypt.checkpw(b"tester123", row["password_hash"].encode()), (
        "tester password hash does not verify against 'tester123'"
    )


async def test_init_db_tester_seeding_is_idempotent(tmp_path, monkeypatch):
    """Calling init_db() twice must not create duplicate tester rows."""
    from app.utils.db import init_db

    settings = _make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE username = 'tester'"
        )
        count = (await cursor.fetchone())[0]

    assert count == 1, f"Expected exactly 1 tester row, got {count}"


async def test_init_db_seeds_both_admin_and_tester(tmp_path, monkeypatch):
    """init_db() seeds both admin and tester users in a single call."""
    from app.utils.db import init_db

    settings = _make_settings(tmp_path, monkeypatch)
    await init_db(settings, seed_sql_path=SEED_SQL_PATH)

    async with aiosqlite.connect(settings.DATABASE_PATH) as conn:
        cursor = await conn.execute(
            "SELECT username, role FROM users WHERE username IN ('admin', 'tester') ORDER BY username"
        )
        rows = await cursor.fetchall()

    usernames = {row[0]: row[1] for row in rows}
    assert "admin" in usernames, "admin user not seeded"
    assert "tester" in usernames, "tester user not seeded"
    assert usernames["admin"] == "admin"
    assert usernames["tester"] == "user"
