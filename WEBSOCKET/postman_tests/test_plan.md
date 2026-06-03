# Postman Test Plan — WebSocket Movie Service

## Setup

1. New → WebSocket Request
2. WebSocket URL:

   * Unary endpoint: `ws://localhost:8080/ws/movies/detail`
   * Streaming endpoint: `ws://localhost:8080/ws/movies/reviews/stream`
3. Click **Connect**
4. Send the request payload as JSON in the message field.

---

# Unary Operations

## Test 1 — FindMovie (positive)

**Endpoint:** `/ws/movies/detail`

**Request:**

```json
{"movieId": 1}
```

**Expected:**
The server returns a `MovieDetailResponse` JSON object for *Inception* containing all movie fields and a `genres` array.

Example response shape:

```json
{
  "id": 1,
  "title": "Inception",
  "releaseYear": 2010,
  "runtimeMinutes": 148,
  "director": "Christopher Nolan",
  "synopsis": "...",
  "genres": ["Action", "Sci-Fi"]
}
```

This demonstrates that the unary operation correctly fetches data from the SQLite database and returns the full movie detail — including the `genres` array — through the WebSocket connection.

---

## Test 2 — FindMovie (negative — malformed JSON)

**Endpoint:** `/ws/movies/detail`

**Request:**

```text
abc
```

**Expected:**
The server responds with a structured JSON error envelope:

```json
{"error": "invalid_request", "message": "Malformed JSON: expected {\"movieId\": <integer>}"}
```

This demonstrates that the WebSocket service validates the input before processing the request and returns a structured error response when the payload cannot be parsed as a `MovieIdRequest`.

---

## Test 3 — FindMovie (negative — not found)

**Endpoint:** `/ws/movies/detail`

**Request:**

```json
{"movieId": 9999}
```

**Expected:**
The server responds with a structured JSON error envelope:

```json
{"error": "movie_not_found", "message": "No movie found with id 9999"}
```

This demonstrates that the WebSocket service correctly handles requests for non-existing resources and returns an appropriate structured error response.

---

# Bidirectional Streaming Operations

## Test 4 — StreamMovie (positive)

**Endpoint:** `/ws/movies/reviews/stream`

**Request:**

```json
{"movieId": 1}
```

**Expected:**
The server immediately sends all existing reviews for movie 1 as a sequence of `ReviewResponse` frames, then continues to push any new reviews as they are added (polled every 2 seconds). The connection stays open.

Example frame shape:

```json
{
  "reviewId": 101,
  "movieId": 1,
  "movieTitle": "Inception",
  "rating": 5,
  "comment": "Masterpiece.",
  "createdAt": "2024-01-01T12:00:00"
}
```

The client can subscribe to additional movies on the same open connection by sending further `{"movieId": N}` messages. Each new subscription triggers an immediate catch-up of existing reviews for that movie, followed by live polling.

This demonstrates that the bidirectional streaming operation keeps the connection open, maintains per-session subscription state, and pushes new `ReviewResponse` frames to the client as they become available.

---

## Test 5 — StreamMovie (negative — malformed JSON)

**Endpoint:** `/ws/movies/reviews/stream`

**Request:**

```text
abc
```

**Expected:**
The server responds with a structured JSON error envelope:

```json
{"error": "invalid_request", "message": "Malformed JSON: expected {\"movieId\": <integer>}"}
```

The connection remains open after the error. The client can send a valid `{"movieId": N}` message on the same connection and the subscription will proceed normally.

This demonstrates that the streaming endpoint validates each incoming message independently and does not close the connection on a bad request.

---

## Test 6 — StreamMovie (negative — not found)

**Endpoint:** `/ws/movies/reviews/stream`

**Request:**

```json
{"movieId": 9999}
```

**Expected:**
The server responds with a structured JSON error envelope:

```json
{"error": "movie_not_found", "message": "No movie found with id 9999"}
```

The connection remains open after the error. The client can send a valid `{"movieId": N}` message on the same connection and the subscription will proceed normally.

This demonstrates that the streaming endpoint correctly handles requests for non-existing resources without terminating the session.
