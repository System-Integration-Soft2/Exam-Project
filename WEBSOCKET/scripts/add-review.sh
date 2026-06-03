#!/usr/bin/env bash
# add-review.sh — insert a review into catalog.db via parameterised Python write.
# Usage: ./WEBSOCKET/scripts/add-review.sh <movie_id> <rating> "<comment>"
# Example: ./WEBSOCKET/scripts/add-review.sh 1 8 "Added while streaming"
# user_id=2 is the admin user (sub=2 from JWT).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <movie_id> <rating> \"<comment>\""
    exit 1
fi

python3 - "$REPO_ROOT/data/catalog.db" "$1" "$2" "$3" <<'PY'
import sqlite3, sys
db, movie_id, rating, comment = sys.argv[1:5]
conn = sqlite3.connect(db)
conn.execute(
    "INSERT INTO reviews (movie_id, user_id, rating, comment) VALUES (?, 2, ?, ?)",
    (int(movie_id), int(rating), comment),
)
conn.commit()
conn.close()
PY
echo "Review added: movie_id=$1 rating=$2 comment=\"$3\""
