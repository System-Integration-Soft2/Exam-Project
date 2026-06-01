#!/usr/bin/env bash

set -euo pipefail

if ! command -v sqlite3 &>/dev/null; then
    echo "Error: sqlite3 is not installed. Install it with: apt-get install sqlite3" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

sqlite3 "$REPO_ROOT/catalog.db" < "$REPO_ROOT/WEBSOCKET/scripts/seed-reviews.sql"

echo "Seeded 10 reviews (ids 101-110) across movies 1-4."
