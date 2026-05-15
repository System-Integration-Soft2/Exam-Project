from app.utils.db import get_connection

with get_connection() as conn:
    row = conn.execute("SELECT COUNT(*) AS n FROM movies").fetchone()
    print(f"Movies in database: {row['n']}")

    # Tjek også at foreign keys er slået til
    fk_status = conn.execute("PRAGMA foreign_keys").fetchone()
    print(f"Foreign keys enabled: {bool(fk_status[0])}")