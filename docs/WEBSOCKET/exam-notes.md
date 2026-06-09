# WebSocket — Exam Notes
> Java Spring Boot · JSON over persistent connection · pub/sub streaming

---

## Files — Overview

| File | What it does | Exam relevance |
|------|-------------|----------------|
| `UnaryHandler.java` | Request/response pattern — receives movie id, returns movie details | Must know |
| `StreamingHandler.java` | Bidirectional streaming — pub/sub with polling every 2 sec. | Must know |
| `WebSocketConfig.java` | Registers handlers on /ws/movies/detail and /ws/movies/stream | Must know |
| `dto/` (folder) | DTOs — the contract: MovieIdRequest, MovieDetailResponse, ReviewResponse, ErrorResponse | Must know |
| `Movie.java`, `Review.java`, `Genre.java` | JPA entities — database models | Good to know |
| `MovieRepository.java` | Database lookups for movies | Good to know |
| `ReviewRepository.java` | Database lookups for reviews incl. polling query | Good to know |
| `WebsocketApplication.java` | Spring Boot entry point | Not needed |

---

## Quick Answers — One Line

**What are WebSockets?**
A protocol that upgrades an HTTP connection to a persistent, full-duplex connection — both sides can send messages at any time without opening new connections.

**What is a DTO?**
Data Transfer Object — a simple class that defines the format of messages sent back and forth. In WebSockets, DTOs act as the contract instead of a `.proto` file or WSDL.

**What is the pub/sub pattern?**
Publish/Subscribe — the client subscribes to a topic (here: a movie id), and the server pushes new messages to the subscriber as they arrive.

**Why are WebSockets more browser-friendly than gRPC?**
WebSockets are supported natively in all modern browsers. gRPC typically requires a gRPC-Web proxy to work from a browser.

**How do we handle errors in WebSockets?**
We send structured JSON error envelopes: `{"error": "movie_not_found", "message": "..."}` — the connection is never closed on error.

**What is `synchronized(session)` for?**
WebSocketSession is not thread-safe — since polling runs on a background thread, all writes to the same session must be synchronized to avoid race conditions.

**What is the difference between UnaryHandler and StreamingHandler?**
UnaryHandler uses a request-response pattern (one movie id in, one response out). StreamingHandler uses pub/sub — the client subscribes, the server continuously pushes new reviews.

---

## Constant Polling vs. Long Polling vs. WebSockets

**Constant polling**
The client sends HTTP requests at fixed intervals regardless of whether there is new data. The server responds immediately — with or without data. Simple but wasteful: many empty requests.

**Long polling**
The client sends one request, the server holds the connection open until there is new data or a timeout is reached. When the response arrives, the client immediately sends a new request. More efficient, but still overhead per message.

**WebSockets**
One persistent connection established via HTTP upgrade. Both sides send freely and independently — no new connection per message. Lowest latency, full duplex, but not stateless.

---

## What Do WebSockets Consist Of — Use Cases, Advantages and Disadvantages

### Consist of

**1. Handshake**
Starts as a normal HTTP request with the header `Upgrade: websocket`. The server accepts with HTTP 101 Switching Protocols, and the connection is converted to a persistent WebSocket connection over TCP.

**2. Frames**
Data is sent as frames (text or binary). Both sides can send frames at any time — no request-response cycle required.

### Use Cases
Multiplayer games, chat and messaging, collaborative editing (Google Docs-like), real-time notifications (social media), live dashboards and financial feeds.

### Advantages
- Low latency — no new connection per message
- Full duplex — server can push data without the client asking
- Works over standard ports (80/443)
- Supports both text and binary data (images, video)
- Native browser support — no proxy needed

### Disadvantages
- Not stateless — harder to scale horizontally
- No built-in reconnect — must be handled manually
- Per-session state requires thread safety (`synchronized`)
- No formal contract like `.proto` or WSDL — JSON parsing is manual

---

## Question — Explain the WebSockets Implementation of the gRPC API's Unary RPC (show in code). Compare Both Implementations.

### Unary

Unary is the simple request-response message pattern, where the client sends one specific request and the server returns one specific response.

In gRPC there is a formal contract in the form of a `.proto` file, where all types are defined. This contract is used to automatically generate strongly typed code for both client and server.

In WebSockets there is no such formal contract. Instead we use DTOs (`MovieIdRequest` as the incoming message and `MovieDetailResponse` as the response) as the contract and send data as JSON between client and server.

### Code — `UnaryHandler.java`
Endpoint: `ws://localhost:8080/ws/movies/detail`

```java
// Client sends one movie id as JSON
MovieIdRequest request = objectMapper.readValue(payload, MovieIdRequest.class);
// ^ throws JacksonException on invalid JSON → returns invalid_request error

Integer movieId = request.getMovieId();

// Server looks up the movie in the database
Optional<Movie> movieOpt = movieRepository.findById(movieId);

if (movieOpt.isEmpty()) {
    sendError(session, "movie_not_found", "No movie found with id " + movieId);
    return;
    // Connection is NOT closed — client can send another request
}

// Server builds MovieDetailResponse with HTML-escaped fields (XSS prevention)
MovieDetailResponse response = new MovieDetailResponse(movieOpt.get());
// ^ escapes title, director, synopsis and genres via HtmlUtils.htmlEscape

// Server sends one response back
session.sendMessage(new TextMessage(objectMapper.writeValueAsString(response)));
```

### Comparison — WebSocket Unary vs. gRPC Unary

| Aspect | WebSocket | gRPC |
|--------|-----------|------|
| **Contract** | DTOs (`MovieIdRequest`, `MovieDetailResponse`) — no formal contract file | `.proto` file defines all types and operations |
| **Data format** | JSON (text format) | Protobuf (binary format) — more compact |
| **Type safety** | Manual JSON parsing via `ObjectMapper` — parsing errors handled manually | Strongly typed — code auto-generated from `.proto` |
| **Error handling** | Structured JSON error envelope: `{"error":"movie_not_found","message":"..."}` | gRPC status codes: `NOT_FOUND`, `INVALID_ARGUMENT` via `context.abort()` |
| **Connection** | Persistent WebSocket — stays open after the response | New HTTP/2 stream per call |
| **Browser support** | Native in all modern browsers | Typically requires gRPC-Web proxy |

---

## Question — Explain the WebSockets Implementation of the gRPC API's Bidirectional Streaming RPC (show in code). Compare Both Implementations.

### Bidirectional Streaming

Both WebSocket endpoints keep the connection open — that is the nature of the WebSocket protocol itself. The difference between unary and bidirectional streaming is the message pattern:

- `UnaryHandler` (`/ws/movies/detail`): request-response — the client sends one message, the server replies with one message. This can be repeated as many times as needed on the same connection.
- `StreamingHandler` (`/ws/movies/stream`): both sides can send messages independently at any time. The client sends subscriptions, the server pushes new reviews — neither side waits for the other.

In gRPC this is implemented using the `stream` keyword in the `.proto` file, which allows messages to be streamed in both directions over the same connection. The client streams movie ids, and the server streams reviews back.

In WebSockets the connection is persistent by default. Here we implement a pub/sub pattern: the client subscribes to a movie by sending `{"movieId": N}`, and the server maintains per-session subscription state and polls the database every 2 seconds for new reviews, which are then pushed to the client. The connection is never closed by the server.

### Code — `StreamingHandler.java`
Endpoint: `ws://localhost:8080/ws/movies/stream`

```java
// Per-session state: which movies are subscribed to, and what is the last seen review id
private final ConcurrentHashMap<String, SessionState> sessions = new ConcurrentHashMap<>();

// When the connection opens: start a polling scheduler
state.scheduler = Executors.newSingleThreadScheduledExecutor();
state.scheduler.scheduleAtFixedRate(
    () -> pollAndPush(session, state),
    POLL_INTERVAL_MS, POLL_INTERVAL_MS, TimeUnit.MILLISECONDS
);

// Client sends a subscription
MovieIdRequest request = objectMapper.readValue(payload, MovieIdRequest.class);
state.subscribedMovieIds.add(movieId);
state.lastSeenByMovie.putIfAbsent(movieId, 0);

// Catch-up: immediately send all existing reviews for this movie
List<Review> catchUp = reviewRepository
    .findByMovieIdInAndIdGreaterThanOrderByIdAsc(List.of(movieId), 0);
for (Review review : catchUp) {
    synchronized (session) {   // thread-safe write
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(toResponse(review))));
    }
    state.lastSeenByMovie.merge(review.getMovieId(), review.getId(), Math::max);
}

// Polling task: push new reviews every 2 seconds
private void pollAndPush(WebSocketSession session, SessionState state) {
    for (Integer movieId : state.subscribedMovieIds) {
        int sinceId = state.lastSeenByMovie.getOrDefault(movieId, 0);
        List<Review> newReviews = reviewRepository
            .findByMovieIdInAndIdGreaterThanOrderByIdAsc(List.of(movieId), sinceId);
        for (Review review : newReviews) {
            synchronized (session) {
                session.sendMessage(new TextMessage(objectMapper.writeValueAsString(toResponse(review))));
            }
            state.lastSeenByMovie.merge(review.getMovieId(), review.getId(), Math::max);
        }
    }
}
```

### Comparison — WebSocket Streaming vs. gRPC Bidirectional Streaming

| Aspect | WebSocket | gRPC |
|--------|-----------|------|
| **Contract** | DTOs (`MovieIdRequest`, `ReviewResponse`) act as the contract | `stream` keyword in `.proto` file explicitly defines bidirectional streaming |
| **Data format** | JSON (text format) | Protobuf (binary format) |
| **Mechanism** | pub/sub + `ScheduledExecutorService` polls DB every 2 sec. | Background thread + `yield` sends frames to the client's iterator |
| **Type safety** | Manual JSON parsing and structuring via `ObjectMapper` | Auto-generated code from `.proto` |
| **Error on message** | JSON error envelope — stream stays open, client can send new subscriptions | gRPC status code can terminate the stream |
| **Browser support** | Native in all modern browsers | Typically requires gRPC-Web proxy |
| **Multi-subscription** | Multiple movie ids can be added on the same connection at any time | New `LiveReviewFeed` call per set of subscriptions |

---

## Run Tests and Explain Messages/Responses

### Positive Testing — Unary

| # | Handler | Input | Expected |
|---|---------|-------|----------|
| 1 | `UnaryHandler` | `{"movieId": 1}` | MovieDetailResponse — "Inception", releaseYear, director, synopsis, `genres: ["Action","Sci-Fi"]` |

### Negative Testing — Unary

| # | Handler | Input | Expected |
|---|---------|-------|----------|
| 2 | `UnaryHandler` | `abc` | `{"error":"invalid_request","message":"Malformed JSON: expected {\"movieId\": <integer>}"}` — connection stays open |
| 3 | `UnaryHandler` | `{"movieId": 9999}` | `{"error":"movie_not_found","message":"No movie found with id 9999"}` — connection stays open |

### Positive Testing — Bidirectional Streaming

| # | Handler | Input | Expected |
|---|---------|-------|----------|
| 4 | `StreamingHandler` | `{"movieId": 1}` | 4 ReviewResponse frames immediately (ids 101–103, 111 for Inception). Polling continues every ~2 sec. |
| 5 | `StreamingHandler` | `{"movieId": 2}` (same connection) | 3 frames for The Dark Knight (ids 104–106). Both movies now stream on one connection. |
| 6 | `StreamingHandler` | New review inserted in DB while stream is open | ReviewResponse arrives within ~2 sec. — without the client sending anything. |

### Negative Testing — Bidirectional Streaming

| # | Handler | Input | Expected |
|---|---------|-------|----------|
| 7 | `StreamingHandler` | `abc` | `{"error":"invalid_request","message":"Malformed JSON: expected {\"movieId\": <integer>}"}` — connection stays open |
| 8 | `StreamingHandler` | `{"movieId": 9999}` | `{"error":"movie_not_found","message":"No movie found with id 9999"}` — connection stays open |

> Messages are sent as JSON over a persistent WebSocket connection. Errors are returned as structured JSON objects and never close the connection. WebSockets do not use HTTP status codes — everything is communicated in the message format.