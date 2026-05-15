"""Test that mutations work end-to-end. Delete after verifying."""
import strawberry
from app.schema.queries import Query
from app.schema.mutations import Mutation

schema = strawberry.Schema(query=Query, mutation=Mutation)

print("=" * 60)
print("Updated SDL (now with Mutation):")
print("=" * 60)
print(schema)

# ---------------------------------------------------------------------
# Test 1: addReview happy path
# ---------------------------------------------------------------------
print("=" * 60)
print("Test 1: add a review for Inception (movie id 1)")
print("=" * 60)
result = schema.execute_sync(
    """
    mutation {
      addReview(input: {
        movieId: "1",
        userId: "1",
        rating: 9,
        comment: "Mind-bending masterpiece!"
      }) {
        id
        rating
        comment
        createdAt
        movie { title }
        user { username }
      }
    }
    """
)
if result.errors:
    print("Errors:", result.errors)
else:
    import json
    print(json.dumps(result.data, indent=2))

# ---------------------------------------------------------------------
# Test 2: addReview with invalid rating — should fail
# ---------------------------------------------------------------------
print("=" * 60)
print("Test 2: try to add a review with rating 15 (should fail)")
print("=" * 60)
result = schema.execute_sync(
    """
    mutation {
      addReview(input: {
        movieId: "1",
        userId: "1",
        rating: 15,
        comment: "Out of range"
      }) {
        id
      }
    }
    """
)
print("Errors:", [str(e) for e in (result.errors or [])])
print("Data:", result.data)

# ---------------------------------------------------------------------
# Test 3: addReview with XSS payload — should be escaped
# ---------------------------------------------------------------------
print("=" * 60)
print("Test 3: add a review with XSS payload — check sanitisation")
print("=" * 60)
result = schema.execute_sync(
    """
    mutation {
      addReview(input: {
        movieId: "1",
        userId: "1",
        rating: 5,
        comment: "<script>alert('hacked')</script>"
      }) {
        comment
      }
    }
    """
)
if result.errors:
    print("Errors:", result.errors)
else:
    import json
    print(json.dumps(result.data, indent=2))

# ---------------------------------------------------------------------
# Test 4: addMovie happy path
# ---------------------------------------------------------------------
print("=" * 60)
print("Test 4: add a new movie 'Fight Club' linked to genres 2 (Drama) and 5 (Thriller)")
print("=" * 60)
result = schema.execute_sync(
    """
    mutation {
      addMovie(input: {
        title: "Fight Club",
        releaseYear: 1999,
        runtimeMinutes: 139,
        director: "David Fincher",
        synopsis: "An insomniac office worker forms an underground fight club.",
        genreIds: ["2", "5"]
      }) {
        id
        title
        releaseYear
        director
        genres { name }
      }
    }
    """
)
if result.errors:
    print("Errors:", result.errors)
else:
    import json
    print(json.dumps(result.data, indent=2))