"""
Helper script to insert a test review into the database.
Used to demonstrate the LiveReviewFeed streaming RPC.

Usage:
  python add_test_review.py <movie_id> <rating> "<comment>"
  python add_test_review.py 1 9 "Mind-blowing!"
"""

import sys
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / "catalog.db"


def ensure_test_user(conn: sqlite3.Connection) -> int:
    """Create a test user if none exists, return its id."""
    row = conn.execute("SELECT id FROM users WHERE username = ?", ("test_user",)).fetchone()
    if row:
        return row[0]
    cursor = conn.execute(
        """
        INSERT INTO users (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """,
        ("test_user", "test@example.com", "fake_hash_for_testing", "user"),
    )
    return cursor.lastrowid


def add_review(movie_id: int, rating: int, comment: str) -> None:
    if not 1 <= rating <= 10:
        raise ValueError("rating must be between 1 and 10")
    if len(comment) > 2000:
        raise ValueError("comment must be 2000 characters or fewer")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        user_id = ensure_test_user(conn)
        conn.execute(
            """
            INSERT INTO reviews (movie_id, user_id, rating, comment)
            VALUES (?, ?, ?, ?)
            """,
            (movie_id, user_id, rating, comment),
        )
        conn.commit()
        print(f"✓ Added review for movie_id={movie_id}: {rating}/10 — '{comment}'")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    add_review(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])