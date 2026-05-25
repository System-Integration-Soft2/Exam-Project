"""
Application-wide configuration values.

All security-relevant limits and defaults live here so they are
visible in one place. GraphQL has no built-in guards against
resource-exhaustion attacks (large pages, deep recursive queries,
alias abuse), so these limits are enforced explicitly:

  - Resolver level: pagination clamping (see queries.py).
  - Schema level: QueryDepthLimiter, MaxAliasesLimiter (see schema.py).
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
# Picked to comfortably allow our deepest legitimate query
# (movie -> reviews -> user) while rejecting pathological nesting.
MAX_QUERY_DEPTH = 10

# Maximum number of field aliases in a single document. Mitigates
# alias abuse where a client requests the same expensive field many
# times under different names to amplify load.
MAX_ALIASES = 15