# WebSocket Movie API

Spring Boot WebSocket service exposing two endpoints over a shared SQLite catalog.

## Endpoints

| Path | Type | Description |
|------|------|-------------|
| `ws://localhost:8080/ws/movies/detail` | Unary | Send `{"movieId": N}`, receive one `MovieDetailResponse` JSON frame. Connection stays open; send more requests on the same socket. |
| `ws://localhost:8080/ws/movies/stream` | Bidirectional | Send `{"movieId": N}` to subscribe to reviews for that movie. Server pushes `ReviewResponse` frames for that movie every ~2 s as new reviews appear. |

### Request format (both endpoints)

```json
{"movieId": 1}
```

### Response shapes

**MovieDetailResponse** (detail endpoint):
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

**ReviewResponse** (stream endpoint):
```json
{
  "reviewId": 1,
  "movieId": 1,
  "movieTitle": "Inception",
  "rating": 9,
  "comment": "A genre-defining masterpiece.",
  "createdAt": "2026-01-01T00:00:00"
}
```

## How to run

```bash
# Requires data/catalog.db to exist and REST to have booted at least once
# (REST's init_db() seeds the schema and the admin user on first boot).
docker compose up -d websocket-api
```

## Seed reviews

To populate the database with some reviews for trying out the streaming endpoint, run:

```bash
./WEBSOCKET/scripts/seed-reviews.sh
```

## Create single review

To create a single review while the stream is running, run:

```bash
./WEBSOCKET/scripts/create-review.sh <movie_id> <rating> "<comment>"
```