# REST API — Exam Notes

## Files — overview

| File | What it does | Exam relevance |
|------|-------------|----------------|
| `app/routers/auth.py` | Login, refresh, logout endpoints — OAuth2 password flow | Must know |
| `app/routers/movies.py` | CRUD for movies + HATEOAS links — admin-protected writes | Must know |
| `app/routers/reviews.py` | Read reviews with pagination and search | Must know |
| `app/routers/genres.py` | Read genres with pagination and search | Must know |
| `app/utils/security.py` | JWT creation, decode, bcrypt hashing, auth dependencies | Must know |
| `app/utils/db.py` | DB connection, `init_db()`, `escape_like()` — shows SQL-injection prevention | Must know |
| `app/utils/redis_client.py` | Redis denylist for token revocation (`SET NX` for atomic claim) | Good to know |
| `app/utils/exceptions.py` | Structured error envelope (`AppError`) for all HTTP error responses | Good to know |
| `app/utils/middleware.py` | Security headers — `X-Content-Type-Options: nosniff` + strict CSP | Good to know |
| `app/config.py` | Strict config via `pydantic-settings` — no default for `JWT_SECRET` | Good to know |
| `app/services/` | Business logic (auth, movies, reviews, genres) called by routers | Good to know |
| `app/models/` | Pydantic v2 request/response models | Good to know |
| `app/main.py` | FastAPI app + lifespan, CORS setup, Redis error handler | Good to know |

---

## Quick answers

**What makes an API RESTful? What transport media and formats?**  
Resources identified by URLs, manipulated via standard HTTP methods (GET, POST, PUT, DELETE). Transport: HTTP/HTTPS. Format: typically JSON, but REST doesn't mandate one — XML, plain text, etc. are also valid.

**What is a JWT? What does it consist of? What is a claim?**  
*JSON Web Token* — three base64url-encoded parts: **header** (algorithm + type), **payload** (claims), **signature** (HMAC or RSA over header+payload). A claim is a key-value pair in the payload — e.g. `sub` (subject), `exp` (expiry), `role`.

**How can a JWT be revoked?**  
JWTs are stateless so they can't be invalidated directly. This API uses a **Redis denylist** — on logout/refresh, the token's `jti` is added to Redis with a TTL matching the remaining token lifetime. Every protected request checks the denylist before proceeding.

**What is a bearer token? How can it be stored? How can it be hardened?**  
A bearer token grants access to whoever holds it — no proof of identity needed beyond the token itself. Storage: memory (safest for SPAs), `httpOnly` secure cookies, or `localStorage` (vulnerable to XSS). Hardening: short TTL, refresh rotation, denylist revocation, HS256 with a strong secret (≥32 chars), explicit algorithm allow-list to prevent `alg:none` attacks.

**Explain OAuth2 roles (resource owner, resource server, authorization server, client).**  
**Resource owner:** the user. **Client:** the app requesting access. **Authorization server:** issues tokens after verifying credentials (in this project: REST's `/api/v1/auth/login`). **Resource server:** the API that checks the token on each request (in this project: also REST — same service). In larger systems these are separate services.

**Explain SOP, CORS, and preflight requests.**  
**SOP** (Same-Origin Policy): browsers block requests from one origin to another by default. **CORS** (Cross-Origin Resource Sharing): the server sends headers (`Access-Control-Allow-Origin`, etc.) that tell the browser which origins are allowed. **Preflight:** for non-simple requests (e.g. PUT with JSON), the browser sends an `OPTIONS` request first — the server must respond with the correct CORS headers or the actual request is blocked.

**Name 3 security attacks and how this API prevents them.**  
1. **SQL-injection** — parameterised queries (`?` placeholders), `escape_like()` for LIKE clauses.  
2. **XSS** — JSON-only responses (no HTML rendering), `X-Content-Type-Options: nosniff`, strict `Content-Security-Policy`.  
3. **CSRF** — bearer token in `Authorization` header (not cookies), CORS allow-list (no `*`), origin validation on every credentialed request.

---

## Explain URL naming (show code)

**File:** `app/routers/movies.py`, `auth.py`, `reviews.py`, `genres.py`

All routes use a consistent pattern: `/api/v1/{resource}` for collections, `/api/v1/{resource}/{id}` for single items.

```
/api/v1/auth/login       POST   — authenticate
/api/v1/auth/refresh     POST   — rotate tokens
/api/v1/auth/logout      POST   — revoke tokens

/api/v1/movies           GET    — list (public)
/api/v1/movies/{id}      GET    — single (public)
/api/v1/movies           POST   — create (admin)
/api/v1/movies/{id}      PUT    — update (admin)
/api/v1/movies/{id}      DELETE — delete (admin)

/api/v1/reviews          GET    — list (public, filterable by movie_id)
/api/v1/reviews/{id}     GET    — single (public)

/api/v1/genres           GET    — list (public)
/api/v1/genres/{id}      GET    — single (public)
```

Resource names are **plural nouns** (`movies`, not `movie`). HTTP methods express the action — the URL never contains verbs. Each router declares its prefix:

```python
router = APIRouter(prefix="/api/v1/movies", tags=["movies"])
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
```

---

## Explain versioning (show code)

**File:** `app/routers/movies.py` line 16, `auth.py` line 9, etc.

Versioning is **URI-path based** — all routes are prefixed with `/api/v1/`:

```python
router = APIRouter(prefix="/api/v1/movies", tags=["movies"])
```

If a breaking change is needed, a new `/api/v2/` prefix can be added with separate routers while keeping `/api/v1/` intact. This is the simplest versioning strategy and the most common for REST APIs.

---

## Explain HATEOAS (show code)

**Files:** `app/routers/movies.py` lines 29–69, `app/utils/links.py`, `app/models/movies.py`

Every response includes `_links` with URLs to related actions:

```python
# routers/movies.py — build link set for a single movie
def _movie_links(movie_id: int) -> LinksMap:
    base = f"/api/v1/movies/{movie_id}"
    return {
        "self": Link(href=base, method="GET"),
        "update": Link(href=base, method="PUT"),
        "delete": Link(href=base, method="DELETE"),
        "reviews": Link(href=f"/api/v1/reviews?movie_id={movie_id}", method="GET"),
    }
```

List responses include **pagination links** (self, first, last, next, prev):

```python
# utils/links.py — pagination links with filters preserved
def page_links(base_path, page, size, total, **filters):
    links = {"self": Link(href=_href(page), method="GET")}
    if total > 0:
        links["first"] = Link(href=_href(1), method="GET")
        links["last"]  = Link(href=_href(last_page), method="GET")
        if page > 1:    links["prev"] = Link(href=_href(page - 1), method="GET")
        if page < last_page: links["next"] = Link(href=_href(page + 1), method="GET")
```

The `_links` field is serialized via Pydantic alias:

```python
# models/movies.py
class MovieResponse(BaseModel):
    links: LinksMap = Field(serialization_alias="_links")
```

This means the client can navigate the entire API by following links — it never needs to hardcode URLs.

---

## Explain pagination and filtering (show code)

**Files:** `app/routers/movies.py` lines 72–91, `app/services/movie_service.py` lines 26–82, `app/utils/db.py` line 102

Query parameters: `?page=1&size=20&q=inception`

```python
# routers/movies.py — query params with validation
@router.get("/")
async def list_movies_endpoint(
    q: str | None = Query(default=None),       # title search
    page: int = Query(default=1, ge=1),         # page number (1-indexed)
    size: int = Query(default=20, ge=1),        # items per page (clamped to 100)
    db=Depends(get_db),
):
```

```python
# services/movie_service.py — filtering with safe LIKE
size = min(size, 100)                           # hard cap
offset = (page - 1) * size

if q and q.strip():
    pattern = escape_like(q.strip())            # escape %, _, \ for safe LIKE
    cursor = await db.execute(
        "SELECT ... FROM movies WHERE title LIKE ? ESCAPE '\\' ORDER BY id LIMIT ? OFFSET ?",
        (pattern, size, offset),
    )
```

```python
# utils/db.py — escape_like prevents wildcard injection
def escape_like(term: str) -> str:
    term = term.replace("\\", "\\\\")   # escape backslash first
    term = term.replace("%", "\\%")     # then percent
    term = term.replace("_", "\\_")     # then underscore
    return f"%{term}%"                  # wrap with wildcards
```

The response envelope includes `page`, `size`, `total`, and navigation `_links`.

---

## Explain how OAuth2 authentication was implemented (show code)

**Files:** `app/routers/auth.py`, `app/services/auth_service.py`, `app/utils/security.py`

### Login — OAuth2 password flow

```python
# routers/auth.py — accepts form-encoded username+password (OAuth2 spec)
@router.post("/api/v1/auth/login")
async def login_endpoint(form: OAuth2PasswordRequestForm = Depends()):
    return await login(form.username, form.password, db, settings)
```

```python
# services/auth_service.py — verify credentials, issue token pair
async def login(username, password, db, settings):
    row = await db.execute("SELECT ... FROM users WHERE username = ?", (username,))
    if row is None:
        bcrypt.checkpw(b"x", DUMMY_HASH)    # constant-time: prevents user enumeration
        raise AppError("unauthorized", "Invalid credentials", 401)
    if not verify_password(password, row["password_hash"]):
        raise AppError("unauthorized", "Invalid credentials", 401)
    return TokenPair(access_token=..., refresh_token=..., expires_in=900)
```

### Refresh — token rotation

```python
# services/auth_service.py — atomic claim via SET NX; concurrent calls lose the race
claimed = await denylist_set(redis_client, old_jti, remaining_ttl)
if not claimed:
    raise AppError("token_revoked", "Token has been revoked", 401)
# issue new pair, return it
```

### Logout — revoke both tokens

```python
# services/auth_service.py — denylist both jtis in Redis with remaining TTL
await denylist_set(redis_client, access_payload["jti"], access_ttl)
await denylist_set(redis_client, refresh_payload["jti"], refresh_ttl)
```

---

## Explain how JWTs are handled (show code)

**File:** `app/utils/security.py`

### Token creation

```python
# security.py — standard claim set
payload = {
    "sub": str(user_id),        # user ID as string (JWT spec)
    "username": username,
    "role": role,               # "admin" or "user"
    "jti": str(uuid.uuid4()),   # unique token ID (for revocation)
    "iat": now,
    "exp": now + ttl_seconds,   # 15 min (access) or 7 days (refresh)
    "type": token_type,         # "access" or "refresh"
}
return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
```

### Token verification

```python
# security.py — decode with explicit algorithm allow-list (prevents alg:none attack)
def decode_token(token, settings):
    return jwt.decode(
        token, settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],   # only HS256 accepted
    )
```

### Auth dependency (used on every protected route)

```python
# security.py — full chain: decode → type check → denylist check → DB lookup
async def get_current_user(token, db, redis_client, settings):
    payload = decode_token(token, settings)
    if payload.get("type") != "access":
        raise AppError("unauthorized", "Invalid token type", 401)
    if await denylist_exists(redis_client, jti):        # Redis check
        raise AppError("token_revoked", "Token has been revoked", 401)
    row = await db.execute("SELECT ... FROM users WHERE id = ?", (user_id,))
    return UserInternal(id=..., username=..., role=...)

# security.py — admin gate
def require_admin(user):
    if user.role != "admin":
        raise AppError("forbidden", "Admin access required", 403)
```

---

## How the REST API prevents SQL-injection, XSS, and CSRF

### SQL-injection

**File:** `app/utils/db.py`, `app/services/movie_service.py`

Every query uses parameterised statements — never string concatenation:

```python
await db.execute("SELECT ... FROM users WHERE username = ?", (username,))
await db.execute("SELECT ... FROM movies WHERE title LIKE ? ESCAPE '\\'", (pattern,))
```

LIKE searches use `escape_like()` to escape `%`, `_`, `\` before binding.

### XSS

**File:** `app/utils/middleware.py`

The API only serves JSON (`Content-Type: application/json`), never HTML — browsers won't execute scripts from JSON responses. Additionally:

```python
# middleware.py — every response gets these headers
response.headers["X-Content-Type-Options"] = "nosniff"        # prevent MIME sniffing
response.headers["Content-Security-Policy"] = "default-src 'none'"  # block all resource loading
```

### CSRF

**Files:** `app/main.py` lines 63–69, `app/utils/security.py`

Three layers of protection:

1. **Bearer token in header** — tokens are sent via `Authorization: Bearer <token>`, not cookies. A malicious site cannot set custom headers via `<form>` or `<img>`.
2. **CORS allow-list** — only explicitly named origins can make credentialed requests:
   ```python
   # main.py
   app.add_middleware(CORSMiddleware,
       allow_origins=[o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",")],
       allow_credentials=True)
   ```
3. **No wildcard** — config validation rejects `*` as an origin:
   ```python
   # config.py
   if origin.strip() == "*":
       raise ValueError("CORS_ALLOWED_ORIGINS must not contain '*'")
   ```

---

All data is **JSON over HTTP/1.1**. Every error response follows the same envelope: `{"detail":"...","code":"...","_links":{...}}`.
