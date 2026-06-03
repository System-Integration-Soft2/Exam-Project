# SOAP Movies Service

A C# .NET + CoreWCF SOAP service exposing `ListMovies`, `GetMovieById`,
`CreateMovie`, `UpdateMovie`, and `DeleteMovie` against the shared `data/catalog.db` SQLite db file.
Runs on port 8001

## Service surface

- **WSDL:** `GET http://localhost:8001/movies.svc?wsdl`
- **SOAP endpoint:** `POST http://localhost:8001/movies.svc` (SOAP 1.1, `basicHttpBinding`)
- **Health check:** `GET http://localhost:8001/healthz` → `{"db":"ok"}` (200) or `{"db":"error"}` (503)

Every response carries `X-Content-Type-Options: nosniff`.

## Running the API

```bash
docker compose up -d soap-api
```


To run without Docker:

```bash
cd SOAP
DATABASE_PATH=../data/catalog.db dotnet run --project src -c Release
```

## Architecture

Three-layererd

```
CoreWCF transport (Program.cs)
  → IMovieService contract (Contracts/IMovieService.cs)
  → MovieService implementation (Services/MovieService.cs)
  → MovieRepository SQL layer (Repositories/MovieRepository.cs)
```

## Environment variables

| Variable        | Default      | Purpose                                                                 |
|-----------------|--------------|-------------------------------------------------------------------------|
| `DATABASE_PATH` | *(required)* | SQLite file path (bind-mounted); service exits non-zero at boot if unset |