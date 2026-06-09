# Exam-Project

Five-protocol API project (REST, SOAP, GraphQL, gRPC, WebSocket) sharing a single SQLite database and one Redis instance.

## Quick start

```bash
# 1. Create your .env file
cp .env.example .env

# 2. Build and start all services
docker compose up -d --build
```

## Services and ports

| Service   | Port |
|-----------|------|
| REST      | 8000 |
| SOAP      | 8001 |
| GraphQL   | 8002 |
| gRPC      | 9000 |
| WebSocket | 8080 |
| Redis     | 6379 |

## Stopping

```bash
docker compose down
```

To also remove persisted Redis data:

```bash
docker compose down -v
```
