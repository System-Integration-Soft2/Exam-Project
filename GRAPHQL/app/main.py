"""
FastAPI application entry point.

This module wires everything together:
  - Builds the GraphQL schema from Query and Mutation classes.
  - Creates a FastAPI application instance.
  - Mounts Strawberry's GraphQLRouter on the /graphql path.
  - Configures CORS to restrict which origins may call the API.

To run the server locally:
    poetry run uvicorn app.main:app --reload

The server listens on http://localhost:8000 by default.
GraphiQL (visual playground) is available at http://localhost:8000/graphql
"""

from app.utils.security import get_security_extensions
import strawberry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.schema.queries import Query
from app.schema.mutations import Mutation


# ---------------------------------------------------------------------
# Build the GraphQL schema.
#
# This is the central place where Query and Mutation are joined into
# a single schema object. Strawberry inspects the classes, generates
# the SDL, and prepares resolvers for execution.
# ---------------------------------------------------------------------
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=get_security_extensions(),
)


# ---------------------------------------------------------------------
# Create the GraphQL router.
#
# FastAPI-compatible router that handles GraphQL
# requests: it parses incoming POSTs, runs them against the schema,
# and returns JSON responses.
# ---------------------------------------------------------------------
graphql_app = GraphQLRouter(schema)


# ---------------------------------------------------------------------
# Create the FastAPI application.
# ---------------------------------------------------------------------
app = FastAPI(
    title="Movie Catalog GraphQL API",
    description="GraphQL API for the System Integration exam project.",
    version="1.0.0",
)


# ---------------------------------------------------------------------
# CORS configuration.
# ---------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Hypothetical frontend dev server
    ],
    allow_credentials=False,      # We do not use cookies; explicit denial.
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------
# Mount the GraphQL router on /graphql.
#
# After this line, two things happen at http://localhost:8000/graphql:
#   - GET  → GraphiQL UI (visual query editor in the browser)
#   - POST → GraphQL query/mutation execution (JSON in, JSON out)
# ---------------------------------------------------------------------
app.include_router(graphql_app, prefix="/graphql")


# ---------------------------------------------------------------------
# Health check endpoint.
# ---------------------------------------------------------------------
@app.get("/health")
def health_check() -> dict:
    """Return a simple status payload to confirm the server is up."""
    return {"status": "ok", "service": "graphql-api"}

# Additional health check endpoint - Docker's default.
@app.get("/healthz")
def health_check() -> dict:
    return {"status": "ok", "service": "graphql-api"}