"""
Application-wide configuration values.

All security-relevant limits and defaults live here in one place.
Other modules import from this file rather than defining their own
constants, so there is a single source of truth for every limit.

GraphQL has no built-in guards against resource-exhaustion attacks
(large pages, deep recursive queries, alias abuse, oversized
documents), so these limits are enforced explicitly:

  - Resolver level: pagination clamping (see queries.py).
  - Schema level: QueryDepthLimiter, MaxAliasesLimiter, MaxTokensLimiter
    (see utils/security.py).
"""

# --- Pagination ------------------------------------------------------------
# Used by the movies() query. The default applies when the client does
# not specify a limit; the max is a hard cap that the client cannot
# exceed regardless of what they send.
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# --- Query complexity ------------------------------------------------------
# Maximum nesting depth of a GraphQL document. Mitigates recursive
# queries like `movie { genres { movies { genres { ... } } } }`.
#
# Our schema's deepest legitimate paths are:
#   movie -> genres -> movies            = depth 3
#   movie -> genres -> movies -> genres  = depth 4
# A limit of 5 accommodates all real queries and stops abuse.
MAX_QUERY_DEPTH = 5

# Maximum number of field aliases in a single document. Mitigates
# alias abuse where a client requests the same expensive field many
# times under different names to amplify load.
MAX_ALIASES = 15

# Maximum number of tokens in a single GraphQL document. Catches
# shallow-but-enormous payloads that slip past the depth and alias
# limits (e.g. a single field repeated thousands of times inline).
MAX_TOKENS = 1000
