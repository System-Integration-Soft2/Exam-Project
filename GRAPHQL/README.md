# GraphQL API

Strawberry + FastAPI service for a movie catalog. Single `/graphql` endpoint serving queries and mutations against the shared `data/catalog.db` SQLite file (read-only — no seeding). Defenses are GraphQL-specific: query-depth limiting, alias limiting, and pagination clamping against resource-exhaustion attacks.

## Quick start

```bash
docker compose up -d --build graphql-api
curl http://localhost:8002/healthz   # → {"status":"ok","service":"graphql-api"}
```

The container listens on port 8000 internally and is published on host port **8002** (`8002:8000`).

Interactive query editor (GraphiQL): `http://localhost:8002/graphql` in the browser.

To run without Docker:

```bash
cd GRAPHQL
poetry install
DATABASE_PATH=../data/catalog.db poetry run uvicorn app.main:app --reload
```

## Service surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/graphql` | GraphiQL UI (visual query editor) |
| POST | `/graphql` | Execute queries and mutations (JSON in, JSON out) |
| GET | `/health` | `{"status":"ok","service":"graphql-api"}` |
| GET | `/healthz` | Same payload — Docker's default health route |

There is no authentication layer on this service; every operation is public.

## Schema

The full SDL is committed at `schema.graphql` and regenerated with `poetry run python export_schema.py` whenever the schema changes.

**Queries**

| Field | Arguments | Returns |
|---|---|---|
| `movie` | `id: ID!` | `Movie` (or `null` if not found) |
| `movies` | `genre: String`, `year: Int`, `limit: Int = 20`, `offset: Int = 0` | `[Movie!]!` |

**Mutations**

| Field | Arguments | Returns |
|---|---|---|
| `addMovie` | `title!`, `releaseYear!`, `runtimeMinutes`, `director`, `synopsis`, `genreIds` | `Movie!` |
| `updateMovie` | `id!` + any field to change (partial update) | `Movie!` |
| `deleteMovie` | `id: ID!` | `Boolean!` |

`updateMovie` is a partial update: any argument left out keeps its existing value. Passing `genreIds` replaces the movie's genre links; an empty list clears them; omitting it leaves them untouched.

**Types**

`Movie` and `Genre` traverse each other (`movie → genres → movies → …`). Nested fields resolve lazily, so a client asking only for `movie { title }` never triggers genre queries.

## Security

- **SQL injection** — every query uses `?` placeholders; no string-concatenated values. Dynamic `WHERE`/`SET` clauses are built from a fixed set of column names, never from user input.
- **Query depth** — `QueryDepthLimiter` rejects documents nested deeper than `MAX_QUERY_DEPTH` (5). Mitigates recursive abuse like `movie { genres { movies { genres { … } } } }`. The deepest legitimate path is depth 4.
- **Alias abuse** — `MaxAliasesLimiter` rejects documents requesting the same expensive field more than `MAX_ALIASES` (15) times under different names to amplify load.
- **Pagination** — the `movies` resolver clamps `limit` to 1–`MAX_PAGE_SIZE` (100) and `offset` to ≥0, so a client can't request an unbounded page. `DEFAULT_PAGE_SIZE` is 20.
- **Extensions per request** — security extensions are registered as factories, not shared instances, so execution state can't leak between concurrent requests.
- **CORS** — allow-list (`http://localhost:3000`), `allow_credentials=False` (no cookies), methods restricted to `GET`/`POST`.
- **Single source of truth** — all limits live in `config.py`; resolvers and extensions import from there rather than redefining constants.

## Architecture

```
FastAPI app (app/main.py) — builds schema, mounts GraphQLRouter on /graphql
  → Query / Mutation resolvers (app/schema/queries.py, mutations.py)
  → GraphQL types + row→type mappers (app/schema/types.py)
  → Services: SQL layer (app/services/movies_service.py, genre_service.py)
  → DB connection management (app/utils/db.py)
  → Security extensions (app/utils/security.py)
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_PATH` | `data/catalog.db` (repo root) | SQLite file path. Falls back to `data/catalog.db` or `catalog.db` at the repo root; service raises `FileNotFoundError` at startup if no file is found. |