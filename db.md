# Database Guide

## What's in the repo

| File | What it is |
|------|-----------|
| `seed.sql` | Schema DDL + seed data (genres, movies, movie_genre links). Human-readable source of truth. |
| `data/catalog.db` | Pre-built SQLite database generated from `seed.sql`. Ready to use — open with any SQLite tool. |

`data/catalog.db` contains the schema, 5 genres, 10 movies, and 20 movie_genre links. It does **not** contain users or reviews — those are seeded by the REST service at startup (see below).

## Regenerate the database

From the repo root:

```bash
rm data/catalog.db
sqlite3 data/catalog.db < seed.sql
```

## Add more data

Option 1 — add INSERT statements to `seed.sql`, then regenerate:

```bash
rm data/catalog.db
sqlite3 data/catalog.db < seed.sql
```

Option 2 — insert directly into the existing file:

```bash
sqlite3 data/catalog.db "INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis) SELECT 11, 'Fight Club', 1999, 139, 'David Fincher', 'An insomniac office worker and a soap salesman form an underground fight club.' WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 11);"
```

## Start fresh

```bash
rm data/catalog.db
sqlite3 data/catalog.db < seed.sql
```

## Schema overview

5 tables:

- **users** — `id`, `username`, `email`, `password_hash`, `role` (user/admin), `created_at`, `updated_at`
- **genres** — `id`, `name`
- **movies** — `id`, `title`, `release_year`, `runtime_minutes`, `director`, `synopsis`, `created_at`, `updated_at`
- **movie_genres** — `movie_id`, `genre_id` (many-to-many join)
- **reviews** — `id`, `movie_id`, `user_id`, `rating` (1-10), `comment`, `created_at`

See `seed.sql` for the full DDL with constraints and indexes.
