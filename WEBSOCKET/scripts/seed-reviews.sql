-- Seed reviews for WebSocket streaming tests.
-- Idempotent: INSERT OR IGNORE with explicit primary keys starting at 101
-- to avoid collisions with reviews created by other services (gRPC, REST).
-- Uses user_id=1 (test_user, created by GRPC/add_test_review.py).
-- Run: sqlite3 data/catalog.db < WEBSOCKET/scripts/seed-reviews.sql

PRAGMA foreign_keys = ON;

-- Movie 1 (Inception) — 3 reviews
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (101, 1, 1, 9, 'A masterpiece of layered storytelling.');
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (102, 1, 1, 7, 'Ambitious but the ending is too ambiguous.');
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (103, 1, 1, 10, 'Rewatchable every single year.');

-- Movie 2 (The Dark Knight) — 3 reviews
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (104, 2, 1, 10, 'Best superhero movie ever made.');
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (105, 2, 1, 9, 'A crime thriller that happens to feature Batman.');
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (106, 2, 1, 8, 'Excellent, though the third act drags slightly.');

-- Movie 3 (Interstellar) — 2 reviews
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (107, 3, 1, 8, 'Visually stunning. The emotion is real.');
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (108, 3, 1, 6, 'Too long but worth watching once.');

-- Movie 4 (Pulp Fiction) — 2 reviews
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (109, 4, 1, 10, 'Non-linear storytelling at its finest.');
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (110, 4, 1, 9, 'Sharp dialogue, unforgettable performances.');

-- XSS test: demonstrates that HtmlUtils.htmlEscape() sanitizes malicious content
INSERT OR IGNORE INTO reviews (id, movie_id, user_id, rating, comment) VALUES (111, 1, 1, 3, '<script>alert(''xss'')</script>');
