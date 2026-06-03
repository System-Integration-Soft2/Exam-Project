# ---- Stage 1: build dependencies with Poetry ----
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files (build cache invalidates only when these change)
COPY GRAPHQL/pyproject.toml GRAPHQL/poetry.lock* ./

# Install dependencies into the system site-packages (no project venv)
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# ---- Stage 2: slim runtime image ----
FROM python:3.12-slim-bookworm
WORKDIR /app

# Install curl for the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (no seed.sql: GraphQL only reads the mounted catalog.db)
COPY GRAPHQL/app ./app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]