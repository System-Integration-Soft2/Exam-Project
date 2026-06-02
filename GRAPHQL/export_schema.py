"""
Export the GraphQL schema to a .graphql file.

Run this script manually whenever the schema changes:

    poetry run python export_schema.py

The generated schema.graphql file is committed to the repository as
documentation of the API contract. Clients can import it into tools
like Postman or use it for static analysis.
"""

from pathlib import Path

from app.main import schema


# The output file lives next to this script, in GRAPHQL/.
OUTPUT_PATH = Path(__file__).parent / "schema.graphql"


def export_schema() -> None:
    """Write the schema's SDL representation to schema.graphql."""
    sdl = schema.as_str()
    OUTPUT_PATH.write_text(sdl, encoding="utf-8")
    print(f"Schema exported to: {OUTPUT_PATH}")
    print(f"Size: {len(sdl)} characters")


if __name__ == "__main__":
    export_schema()