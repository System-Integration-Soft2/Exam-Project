# REST API

FastAPI service for a movie catalog. OAuth2 password flow with HS256 JWT bearer auth (access + refresh, refresh rotation), per-jti Redis denylist for revocation.

## Quick start

```bash
docker compose up -d --build
curl http://localhost:8000/healthz   # → {"db":"ok","redis":"ok"}
```

The stack brings up `rest-api` (port 8000) and `redis` (port 6379). Both must be healthy before the first request.

**Default users**, auto-seeded by `init_db()` on first run:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | `admin` |
| `tester` | `tester123` | `user` |


## Endpoints

| Method | Path | Auth |
|---|---|---|
| GET | `/healthz` | none |
| POST | `/api/v1/auth/login` | form-encoded credentials |
| POST | `/api/v1/auth/refresh` | refresh JWT in body |
| POST | `/api/v1/auth/logout` | bearer |
| GET | `/api/v1/movies` | none |
| GET | `/api/v1/movies/{id}` | none |
| POST | `/api/v1/movies` | admin |
| PUT | `/api/v1/movies/{id}` | admin |
| DELETE | `/api/v1/movies/{id}` | admin |
| GET | `/api/v1/genres` | none |
| GET | `/api/v1/genres/{id}` | none |
| GET | `/api/v1/reviews` | none |
| GET | `/api/v1/reviews/{id}` | none |

Pagination on every list endpoint: `?page=N&size=N` (size 1–100). Search on movies and genres: `?q=...`. Filter on reviews: `?movie_id=N`. All list responses are HATEOAS-shaped with `_links` (`self`, `first`, `last`, `prev?`, `next?`).

Interactive API exploration: `http://localhost:8000/docs` (Swagger UI) or `/redoc`.


## Security

- **SQL injection** — every query uses `?` placeholders; `LIKE` inputs are escaped with `ESCAPE '\\'`.
- **XSS** — JSON-only responses; every response carries `X-Content-Type-Options: nosniff` and a strict `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`. Doc routes (`/docs`, `/redoc`, `/openapi.json`) get a relaxed CSP that permits the Swagger/ReDoc CDN.
- **CSRF** — bearer tokens in `Authorization` header, never cookies. Browsers don't auto-attach `Authorization` to cross-site requests, so the API is structurally not susceptible to CSRF.
- **CORS** — allow-list driven by `CORS_ALLOWED_ORIGINS`. Wildcard `*` rejected at config time. `allow_credentials=True` is safe because origins are a specific list.
- **JWT** — HS256 with explicit `algorithms=` allow-list (defense against alg-confusion attacks). Standard claims: `iss`, `aud`, `sub`, `jti`, `iat`, `exp`, `type`. Per-jti Redis denylist with TTL matching the token's remaining expiry — entries auto-evict.
- **Token revocation** — logout denylists both jtis (access + refresh). Refresh rotation uses `SET … EX … NX` for an atomic claim so concurrent refresh calls can't both succeed.
- **Login timing** — unknown username runs a dummy bcrypt verify to equalise response time with the known-username-wrong-password path.
- **Startup config** — `JWT_SECRET` is required, ≥32 chars, no default. The service exits non-zero at module load if it's missing or too short.

## Configuration

See `.env.example` for the full variable set with safe defaults. Required: `JWT_SECRET`. Everything else has a default suitable for local development.
