# SOAP Movies Service

A C# .NET 8 + CoreWCF SOAP service exposing `ListMovies`, `GetMovieById`,
`CreateMovie`, and `UpdateMovie` against the shared `catalog.db` SQLite file.
Runs on port 8001 alongside the REST service.

## Service surface

- **WSDL:** `GET http://localhost:8001/movies.svc?wsdl`
- **SOAP endpoint:** `POST http://localhost:8001/movies.svc` (SOAP 1.1, `basicHttpBinding`)
- **Health check:** `GET http://localhost:8001/healthz` → `{"db":"ok"}` (200) or `{"db":"error"}` (503)

## Running the API

```bash
docker compose up -d soap-api
```

## Architecture

Three-layer mirror of the REST service:

```
CoreWCF transport (Program.cs)
  → IMovieService contract (Contracts/IMovieService.cs)
  → MovieService implementation (Services/MovieService.cs)
  → MovieRepository SQL layer (Repositories/MovieRepository.cs)
```

## Environment variables

| Variable        | Default              | Purpose                        |
|-----------------|----------------------|--------------------------------|
| `DATABASE_PATH` | *(required)*         | SQLite file path (bind-mounted); service exits non-zero at boot if unset |
| `LOG_LEVEL`     | `Information`        | Minimum log level (e.g. `Debug`, `Warning`, `Error`) |