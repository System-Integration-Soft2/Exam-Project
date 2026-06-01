# Postman Test Plan — WebSocket Movie Service

## Setup

1. New → WebSocket Request
2. WebSocket URL:

   * Unary endpoint: `ws://localhost:8080/ws/movie/detail`
   * Streaming endpoint: `ws://localhost:8080/ws/movie/stream`
3. Click **Connect**
4. Send the request payload in the message field.

---

# Unary Operations

## Test 1 — FindMovie (positive)

**Endpoint:** `/ws/movie/detail`

**Request:**

```text
1
```

**Expected:**
The server successfully establishes the WebSocket connection and returns the full movie details for *Inception* as JSON.

This demonstrates that the Unary operation correctly fetches data from the SQLite database and returns the result through the WebSocket connection.

📸 Screenshot: `01_find_movie_success.png`

---

## Test 2 — FindMovie (negative — invalid characters)

**Endpoint:** `/ws/movie/detail`

**Request:**

```text
abc
```

**Expected:**
The server responds with the custom error message:

```text
Fejl i Film ID format. Vær sikker på at du sender et gyldigt heltal.
```

This demonstrates that the WebSocket service correctly validates the input before processing the request and gracefully handles invalid data by returning an appropriate error message to the client.

📸 Screenshot: `02_find_movie_invalid_characters.png`

---

## Test 3 — FindMovie (negative — not found)

**Endpoint:** `/ws/movie/detail`

**Request:**

```text
99
```

**Expected:**
The server responds with a custom error message indicating that the requested movie could not be found.

This demonstrates that the WebSocket service correctly handles requests for non-existing resources and gracefully returns an appropriate error response to the client.

📸 Screenshot: `03_find_movie_not_found.png`

---

# Bidirectional Streaming Operations

## Test 4 — StreamMovie (positive)

**Endpoint:** `/ws/movie/stream`

**Request:**

```text
1
```

**Expected:**
The server successfully establishes the WebSocket connection and continuously streams movie data back to the client every 2 seconds.

The response contains multiple movie objects from the SQLite database returned as JSON through the WebSocket connection.

This demonstrates that the Bidirectional Streaming operation correctly keeps the connection open and continuously streams data between the server and client in real time.

📸 Screenshot: `04_stream_movie_success.png`

---

## Test 5 — StreamMovie (negative — invalid characters)

**Endpoint:** `/ws/movie/stream`

**Request:**

```text
abc
```

**Expected:**
The server responds with a custom error message indicating that the request format is invalid.

This demonstrates that the WebSocket service correctly validates the input before processing the streaming request and gracefully handles invalid data by returning an appropriate error message to the client.

📸 Screenshot: `05_stream_movie_invalid_characters.png`

---

## Test 6 — StreamMovie (negative — not found)

**Endpoint:** `/ws/movie/stream`

**Request:**

```text
99
```

**Expected:**
The server responds with a custom error message indicating that the requested movie could not be found.

This demonstrates that the WebSocket service correctly handles requests for non-existing resources during streaming operations and gracefully returns an appropriate error response to the client.

📸 Screenshot: `06_stream_movie_not_found.png`
