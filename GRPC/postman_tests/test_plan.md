# Postman Test Plan — gRPC Catalog Service

Postman does not currently export gRPC collections, so each test below is documented
with the request/response details and accompanied by a screenshot in this folder.

## Setup

1. New → gRPC Request
2. Server URL: `localhost:9000` (uncheck TLS)
3. Service definition → Import a .proto file → select `proto/catalog.proto`
4. Pick the method from the dropdown next to the URL.

---

## Test 1 — GetMovie (positive)

**Method:** `CatalogService / GetMovie`
**Request:**
```json
{ "movie_id": 1 }
```
**Expected:** Inception is returned with all fields populated and 2 genres
(`Action`, `Sci-Fi`). Status code `OK`.

📸 Screenshot: `01_get_movie_success.png`

---

## Test 2 — GetMovie (negative — not found)

**Method:** `CatalogService / GetMovie`
**Request:**
```json
{ "movie_id": 9999 }
```
**Expected:** Status code `NOT_FOUND`, message `"No movie with id 9999"`.

📸 Screenshot: `02_get_movie_not_found.png`

---

## Test 3 — GetMovie (negative — invalid argument)

**Method:** `CatalogService / GetMovie`
**Request:**
```json
{ "movie_id": -1 }
```
**Expected:** Status code `INVALID_ARGUMENT`, message about positive integer.

📸 Screenshot: `03_get_movie_invalid.png`

---

## Test 4 — LiveReviewFeed (positive — receives new review)

**Method:** `CatalogService / LiveReviewFeed`
**Action:**
1. Click **Invoke**.
2. Send message: `{ "movie_id": 1 }`
3. In a terminal: `python add_test_review.py 1 8 "Great film"`
4. Observe the streamed `ReviewUpdate` in Postman.

**Expected:** A `ReviewUpdate` arrives with `movie_title: "Inception"`,
`rating: 8`, `comment: "Great film"`.

📸 Screenshot: `04_review_feed_success.png`

---

## Test 5 — LiveReviewFeed (negative — invalid movie_id)

**Method:** `CatalogService / LiveReviewFeed`
**Action:**
1. Click **Invoke**.
2. Send message: `{ "movie_id": 0 }`
3. Observe the server log warning; no review is streamed for that ID.

**Expected:** Server logs `Invalid subscribe request`. The stream stays open
but the bad ID is ignored.

📸 Screenshot: `05_review_feed_invalid.png`

---

## Test 6 — XSS sanitization (security)

**Setup:** Insert a malicious-looking review:
```powershell
python add_test_review.py 1 5 "<script>alert('xss')</script>"
```

**Method:** `CatalogService / LiveReviewFeed`
**Action:** Subscribe to movie_id 1, observe the streamed update.

**Expected:** The `comment` field arrives as
`&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;` — the script tags are
HTML-escaped and harmless.

📸 Screenshot: `06_xss_sanitized.png`