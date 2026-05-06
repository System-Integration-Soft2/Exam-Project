PRAGMA foreign_keys = ON;

-- Users table: stores credentials and role for authentication.
-- password_hash is a bcrypt hash;
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    NOT NULL UNIQUE,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'user'
                            CHECK (role IN ('user', 'admin')),
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- Genres table: lookup table for movie genre classification.
CREATE TABLE IF NOT EXISTS genres (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL UNIQUE
);

-- Movies table: the primary catalog resource.
-- release_year is constrained to the range of plausible film history.
-- runtime_minutes is optional; NULL means unknown.
CREATE TABLE IF NOT EXISTS movies (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    release_year     INTEGER NOT NULL
                             CHECK (release_year BETWEEN 1888 AND 2100),
    runtime_minutes  INTEGER          CHECK (runtime_minutes IS NULL OR runtime_minutes > 0),
    director         TEXT,
    synopsis         TEXT,
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    updated_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- movie_genres: many-to-many join between movies and genres.
-- Cascades on delete so removing a movie or genre cleans up links automatically.
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id    INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id    INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- Reviews table: user ratings and comments on movies.
-- rating is 1–10 inclusive; comment is optional and capped at 2000 chars.
-- No updated_at column: reviews are immutable once submitted.
CREATE TABLE IF NOT EXISTS reviews (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id   INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    rating     INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 10),
    comment    TEXT             CHECK (comment IS NULL OR length(comment) <= 2000),
    created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- Indexes for common query patterns.
CREATE INDEX IF NOT EXISTS idx_users_username      ON users(username);
CREATE INDEX IF NOT EXISTS idx_movies_title        ON movies(title);
CREATE INDEX IF NOT EXISTS idx_movies_release_year ON movies(release_year);
CREATE INDEX IF NOT EXISTS idx_movie_genres_genre  ON movie_genres(genre_id);
CREATE INDEX IF NOT EXISTS idx_reviews_movie       ON reviews(movie_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user        ON reviews(user_id);

-- Seed genres (idempotent: INSERT OR IGNORE on the UNIQUE name column).
INSERT OR IGNORE INTO genres (name) VALUES ('Action');
INSERT OR IGNORE INTO genres (name) VALUES ('Drama');
INSERT OR IGNORE INTO genres (name) VALUES ('Sci-Fi');
INSERT OR IGNORE INTO genres (name) VALUES ('Comedy');
INSERT OR IGNORE INTO genres (name) VALUES ('Thriller');

-- Seed movies (idempotent: INSERT OR IGNORE; title is not UNIQUE so we use
-- a WHERE NOT EXISTS guard to avoid duplicates on re-runs).
INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 1, 'Inception', 2010, 148, 'Christopher Nolan',
           'A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 1);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 2, 'The Dark Knight', 2008, 152, 'Christopher Nolan',
           'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 2);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 3, 'Interstellar', 2014, 169, 'Christopher Nolan',
           'A team of explorers travel through a wormhole in space in an attempt to ensure humanity''s survival.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 3);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 4, 'Pulp Fiction', 1994, 154, 'Quentin Tarantino',
           'The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 4);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 5, 'The Matrix', 1999, 136, 'Lana Wachowski, Lilly Wachowski',
           'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 5);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 6, 'Parasite', 2019, 132, 'Bong Joon-ho',
           'Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 6);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 7, 'Forrest Gump', 1994, 142, 'Robert Zemeckis',
           'The presidencies of Kennedy and Johnson, the Vietnam War, the Watergate scandal and other historical events unfold from the perspective of an Alabama man with an IQ of 75.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 7);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 8, 'Alien', 1979, 117, 'Ridley Scott',
           'After a space merchant vessel receives an unknown transmission as a distress call, one of the crew is attacked by a mysterious life form and they soon realize that its life cycle has merely begun.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 8);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 9, 'The Godfather', 1972, 175, 'Francis Ford Coppola',
           'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 9);

INSERT OR IGNORE INTO movies (id, title, release_year, runtime_minutes, director, synopsis)
    SELECT 10, 'Blade Runner 2049', 2017, 164, 'Denis Villeneuve',
           'A young blade runner''s discovery of a long-buried secret leads him to track down former blade runner Rick Deckard, who''s been missing for thirty years.'
    WHERE NOT EXISTS (SELECT 1 FROM movies WHERE id = 10);

-- Seed movie_genres links (idempotent: PRIMARY KEY (movie_id, genre_id) + INSERT OR IGNORE).
-- Inception: Action, Sci-Fi
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 1, id FROM genres WHERE name = 'Action';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 1, id FROM genres WHERE name = 'Sci-Fi';

-- The Dark Knight: Action, Thriller
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 2, id FROM genres WHERE name = 'Action';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 2, id FROM genres WHERE name = 'Thriller';

-- Interstellar: Sci-Fi, Drama
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 3, id FROM genres WHERE name = 'Sci-Fi';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 3, id FROM genres WHERE name = 'Drama';

-- Pulp Fiction: Thriller, Drama
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 4, id FROM genres WHERE name = 'Thriller';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 4, id FROM genres WHERE name = 'Drama';

-- The Matrix: Action, Sci-Fi
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 5, id FROM genres WHERE name = 'Action';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 5, id FROM genres WHERE name = 'Sci-Fi';

-- Parasite: Thriller, Drama
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 6, id FROM genres WHERE name = 'Thriller';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 6, id FROM genres WHERE name = 'Drama';

-- Forrest Gump: Drama, Comedy
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 7, id FROM genres WHERE name = 'Drama';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 7, id FROM genres WHERE name = 'Comedy';

-- Alien: Sci-Fi, Thriller
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 8, id FROM genres WHERE name = 'Sci-Fi';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 8, id FROM genres WHERE name = 'Thriller';

-- The Godfather: Drama, Thriller
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 9, id FROM genres WHERE name = 'Drama';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 9, id FROM genres WHERE name = 'Thriller';

-- Blade Runner 2049: Sci-Fi, Thriller
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 10, id FROM genres WHERE name = 'Sci-Fi';
INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
    SELECT 10, id FROM genres WHERE name = 'Thriller';
