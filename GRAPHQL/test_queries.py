"""Quick sanity check that the Query type works. Delete after verifying."""
import strawberry
from app.schema.queries import Query

# Build a temporary schema with only the Query type
schema = strawberry.Schema(query=Query)

# Print the generated SDL so we can see what Strawberry produced
print("=" * 60)
print("Generated SDL:")
print("=" * 60)
print(schema)

# Now execute a real query against it
print("=" * 60)
print("Test query: fetch movie with id=1, including genres and reviews")
print("=" * 60)
result = schema.execute_sync(
    """
    query {
      movie(id: "1") {
        id
        title
        releaseYear
        director
        averageRating
        genres {
          name
        }
        reviews {
          rating
          comment
          user {
            username
          }
        }
      }
    }
    """
)

if result.errors:
    print("Errors:", result.errors)
else:
    import json
    print(json.dumps(result.data, indent=2))