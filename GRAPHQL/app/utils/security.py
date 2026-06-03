"""
GraphQL-specific security extensions.

This module assembles defenses against attacks that are unique to
GraphQL — particularly resource-exhaustion attacks via deeply nested
queries, alias abuse, or oversized documents.

Unlike REST, where each request hits one endpoint, a GraphQL query
can traverse arbitrarily deep relationships in a single request. A
malicious client could send:

    movie { genres { movies { genres { movies { ... } } } } }

Each level triggers more database calls. Without limits, an attacker
could exhaust server resources. The three extensions below mitigate
the main GraphQL-specific abuse patterns:

  - QueryDepthLimiter rejects documents nested deeper than MAX_QUERY_DEPTH.
  - MaxAliasesLimiter rejects documents that request the same field many
    times under different names to amplify load.
  - MaxTokensLimiter rejects documents with more than MAX_TOKENS tokens,
    catching oversized payloads that are shallow and alias-free but
    enormous, and so slip past the other two limits.

Limits live in config.py; this module only wires up the extensions.

Extensions are registered as factories (callables that build a fresh
extension) rather than instances, so a new extension is constructed per
request. This is what Strawberry recommends: a shared instance would be
reused across requests and could leak execution state between concurrent
requests.
"""

from strawberry.extensions import (
    MaxAliasesLimiter,
    MaxTokensLimiter,
    QueryDepthLimiter,
)

from app.config import MAX_ALIASES, MAX_QUERY_DEPTH, MAX_TOKENS


def get_security_extensions() -> list:
    """
    Return the list of Strawberry extension factories to attach to the schema.

    Centralising the extension list here means future additions
    (rate limiting, error masking, etc.) have a single place to live
    and main.py doesn't grow with security concerns.
    """
    return [
        QueryDepthLimiter(max_depth=MAX_QUERY_DEPTH),
        MaxAliasesLimiter(max_alias_count=MAX_ALIASES),
        MaxTokensLimiter(max_token_count=MAX_TOKENS),
    ]