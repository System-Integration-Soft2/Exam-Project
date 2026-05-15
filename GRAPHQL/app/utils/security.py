"""
GraphQL-specific security extensions.

This module implements defenses against attacks that are unique to
GraphQL — particularly resource-exhaustion attacks via deeply nested
or recursive queries.

Unlike REST, where each request hits one endpoint, a GraphQL query
can traverse arbitrarily deep relationships in a single request. A
malicious client could send a query like:

    movie { genres { movies { genres { movies { ... } } } } }

Each level triggers more database calls. Without a depth limit, an
attacker could send a 50-level-deep query and exhaust server
resources — a denial-of-service attack specific to GraphQL.

We mitigate this with Strawberry's built-in QueryDepthLimiter
extension, which rejects any query that exceeds a configured depth.
"""

from strawberry.extensions import QueryDepthLimiter


# Maximum allowed nesting depth in any single query.
#
# Our schema's deepest legitimate path is roughly:
#   movie -> reviews -> user -> (stops)         = depth 3
#   movie -> genres -> movies -> genres         = depth 4
#
# A limit of 5 accommodates all legitimate use cases and stops
# recursive abuse patterns. Raise this only if real queries need it.
MAX_QUERY_DEPTH = 5


def get_security_extensions() -> list:
    """
    Return the list of Strawberry extensions to attach to the schema.

    Centralising the extension list here means future additions
    (rate limiting, query complexity analysis, etc.) have a single
    place to live, and main.py doesn't grow with security concerns.
    """
    return [
        QueryDepthLimiter(max_depth=MAX_QUERY_DEPTH),
    ]