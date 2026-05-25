"""
GraphQL-specific security extensions.

This module assembles defenses against attacks that are unique to
GraphQL — particularly resource-exhaustion attacks via deeply nested
queries or alias abuse.

Unlike REST, where each request hits one endpoint, a GraphQL query
can traverse arbitrarily deep relationships in a single request. A
malicious client could send:

    movie { genres { movies { genres { movies { ... } } } } }

Each level triggers more database calls. Without limits, an attacker
could exhaust server resources. The two extensions below mitigate
the two main GraphQL-specific abuse patterns:

  - QueryDepthLimiter rejects documents nested deeper than MAX_QUERY_DEPTH.
  - MaxAliasesLimiter rejects documents that request the same field many
    times under different names to amplify load.

Limits live in config.py; this module only wires up the extensions.

Extensions are returned as lambda factories (not instances) so a fresh
extension is constructed per request, which is what Strawberry recommends.
"""

from strawberry.extensions import MaxAliasesLimiter, QueryDepthLimiter

from app.config import MAX_ALIASES, MAX_QUERY_DEPTH


def get_security_extensions() -> list:
    """
    Return the list of Strawberry extensions to attach to the schema.

    Centralising the extension list here means future additions
    (rate limiting, error masking, etc.) have a single place to live
    and main.py doesn't grow with security concerns.
    """
    return [
    QueryDepthLimiter(max_depth=MAX_QUERY_DEPTH),
    MaxAliasesLimiter(max_alias_count=MAX_ALIASES),
]