# gRPC Catalog Service

A gRPC API for a movie catalog with a unary RPC and a bidirectional streaming RPC,
backed by a shared SQLite database (`../data/catalog.db`).

## Why Python?

gRPC is designed to be language-agnostic — the `.proto` contract is the source of truth,
and any supported language can implement it. Python was chosen because:

- It is one of gRPC's primary reference languages, with mature tooling (`grpcio`, `grpcio-tools`).
- `sqlite3` is part of the Python standard library, giving direct and transparent control
  over parameterized queries — which makes SQL-injection prevention explicit and verifiable.
- The rest of our group works in Python, so the gRPC service is consistent with the
  REST, SOAP, GraphQL, and WebSocket services in the same project.

## Service Definition

See [`proto/catalog.proto`](proto/catalog.proto).

| RPC               | Type                    | Purpose                                           |
|-------------------|-------------------------|---------------------------------------------------|
| `GetMovie`        | Unary                   | Fetch a single movie with its genres              |
| `LiveReviewFeed`  | Bidirectional streaming | Subscribe to movies and receive new reviews live  |

## Project Structure

```
GRPC/
├── proto/
│   └── catalog.proto         # Service contract (Protobuf)
├── generated/                # Auto-generated from .proto
│   ├── catalog_pb2.py
│   └── catalog_pb2_grpc.py
├── db.py                     # SQLite helper with parameterized queries
├── security.py               # Input validation and XSS sanitization
├── server.py                 # gRPC server implementation
├── client.py                 # Test client (unary + streaming)
├── add_test_review.py        # Helper to insert reviews for streaming tests
├── requirements.txt          # Python dependencies
└── README.md
```

## Setup

Requires **Python 3.10+** (developed on 3.13).

```powershell
# From the GRPC/ directory
python -m venv .venv
.\.venv\Scripts\activate           # Windows
# source .venv/bin/activate        # macOS/Linux
pip install -r requirements.txt
```

### Regenerate Python code from `.proto`

Only needed if `catalog.proto` changes:

```powershell
python -m grpc_tools.protoc -I=proto --python_out=generated --grpc_python_out=generated proto/catalog.proto
```

## Running

Open three terminals (all with the venv activated).

**Terminal 1 — start the server:**
```powershell
python server.py
```

**Terminal 2 — call the unary RPC:**
```powershell
python client.py get 1
```

**Terminal 3 — open a streaming subscription:**
```powershell
python client.py feed 1 2 3
```

**Terminal 4 (or reuse 3 after Ctrl-C) — insert a review to trigger the stream:**
```powershell
python add_test_review.py 1 9 "Absolutely brilliant!"
```

The streaming client will print the new review within a couple of seconds.

## Security

### SQL-Injection — Prevented

Every database query uses **parameterized statements** with `?` placeholders.
User input is passed as a separate argument tuple, never concatenated into the SQL string.

```python
# db.py — see fetch_movie
conn.execute("SELECT id, title FROM movies WHERE id = ?", (movie_id,))
```

The `IN (...)` clause in `fetch_new_reviews_for_movies` builds its placeholders
dynamically (`?,?,?`) but every value is still passed as a parameter — the SQL
itself is fixed and contains no user-controlled string.

### XSS — Prevented

Every outgoing string field is escaped with `html.escape()` in `security.py`.
A malicious comment like `<script>alert(1)</script>` becomes
`&lt;script&gt;alert(1)&lt;/script&gt;` before it leaves the server, so any
downstream consumer that renders the value as HTML will display it as text.

Inputs are also length-validated and stripped of ASCII control characters
(`security.validate_comment`) before being accepted.

### CSRF — Not Applicable to gRPC

CSRF attacks rely on a victim's browser sending a forged request to a site where
the victim has an active session, with credentials (typically a session cookie)
attached automatically. **gRPC over HTTP/2 is not vulnerable to CSRF because:**

1. **No cookie-based authentication.** This service has no cookies; it uses no
   browser session at all.
2. **Browsers cannot send native gRPC requests.** gRPC requires the
   `application/grpc` content type and HTTP/2 framing, which the browser
   `<form>` and image-tag attack surfaces cannot produce. Any browser-based
   gRPC call goes through gRPC-Web with an explicit JS library, which is
   subject to CORS and cannot be invoked silently from another origin.
3. **No ambient credentials.** A real client (gRPC stub) must explicitly send
   credentials in each call (e.g., metadata headers); a malicious page cannot
   trigger that on the user's behalf.

For these reasons, no CSRF token is needed in this service. If gRPC-Web is
later introduced, standard CORS configuration on the proxy is sufficient.

## Testing with Postman

Postman supports gRPC natively:

1. New → gRPC Request
2. Server URL: `localhost:9000`
3. Import the proto file: `proto/catalog.proto`
4. Pick a method (`GetMovie` or `LiveReviewFeed`) and send.

A test collection with positive and negative cases is included as screenshots
(see `postman_tests/`) since Postman does not export gRPC collections at the
time of writing.