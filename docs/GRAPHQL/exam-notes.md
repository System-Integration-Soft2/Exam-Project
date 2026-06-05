# GraphQL API — Eksamensnoter

Vores GraphQL-API er et **film-katalog** i **Python** med **Strawberry** (oven på **FastAPI**). Data ligger i **SQLite** (`catalog.db`): `movies`, `genres` og en many-to-many-relation imellem dem. Hele API'et nås på **ét endpoint**: `/graphql`. SDL'en genereres fra koden med `export_schema.py` og holdes i sync med `schema.graphql`.

---

## Filer — overblik

Filerne ligger under `GRAPHQL/`. "Eksamensrelevans" = hvad man bør kunne forklare.

| Fil | Hvad den gør | Eksamensrelevans |
|-----|-------------|------------------|
| `app/main.py` | Bygger schema'et, monterer GraphQL på `/graphql`, sætter CORS op. Alt samles her. | Skal vide |
| `app/schema/queries.py` | `Query`: read-operationerne `movie(id)` og `movies(...)`. | Skal vide |
| `app/schema/mutations.py` | `Mutation`: write-operationerne `addMovie`, `updateMovie`, `deleteMovie`. | Skal vide |
| `app/schema/types.py` | Typerne `Movie` og `Genre` + de nested field-resolvers (`Movie.genres`, `Genre.movies`). | Skal vide |
| `schema.graphql` | API-kontrakten i **SDL**. Genereres fra koden. | Skal vide |
| `app/utils/security.py` | GraphQL-forsvar: depth limiter + alias limiter (mod DoS). | Skal vide |
| `app/services/movies_service.py` | Al SQL om film. Parameterized queries → ingen SQL-injection. | Skal vide |
| `postman/graphql_collection.json` | Postman-tests (positive + negative requests). | Skal vide |
| `app/services/genre_service.py` | Al SQL om genrer. | Godt at vide |
| `app/config.py` | Alle limits ét sted: `MAX_PAGE_SIZE`, `MAX_QUERY_DEPTH`, `MAX_ALIASES`. | Godt at vide |
| `app/utils/db.py` | Åbner SQLite-connections, commit/rollback. | Godt at vide |
| `export_schema.py` | Skriver schema'et ud til `schema.graphql`. | Godt at vide |
| `pyproject.toml` | Dependencies (Poetry): `strawberry-graphql`, `fastapi`, `uvicorn`. | Godt at vide |
| `Dockerfile` / `README.md` | Container-setup / næsten tom. | Ikke nødvendigt |

---

## Hurtige svar

**Hvad er GraphQL?** Et query language til API'er (Facebook, 2015). Klienten beskriver præcis hvilke fields den vil have, og serveren svarer i samme form. Transport: **HTTP POST**. Format: **JSON**. Ét endpoint: `/graphql`.

**REST vs. GraphQL?** REST: mange URL'er, fast response-form. GraphQL: ét endpoint, og klienten vælger selv fields og nested data i ét kald → ingen over-/underfetching.

**Schema / SDL?** Schema'et er API'ets kontrakt — alle types og operationer, skrevet i **SDL** (Schema Definition Language). Hos os: `schema.graphql`.

**Resolver?** En funktion der henter data for ét field. I Strawberry **er** metoderne i `Query`/`Mutation` og fields med `@strawberry.field` selv resolvers — ingen separat resolver-fil.

**Query / mutation / subscription?** **Query** = read (som `GET`). **Mutation** = write-then-read (som `POST`/`PUT`/`DELETE`). **Subscription** = realtid over WebSockets. *Vi bruger query + mutation.*

**Field, scalar, type-modifier?** Field = navngiven værdi (fx `title`). Scalars: `Int`, `String`, `Float`, `Boolean`, `ID`. Modifiers: `!` = non-null, `[ ]` = liste. `[Genre!]!` = non-null liste af non-null `Genre`.

**Strawberry / code-first?** Vi skriver Python-klasser, og Strawberry genererer SDL'en (code-first). Strawberry oversætter `snake_case` → `camelCase`: `release_year` → `releaseYear`, `add_movie` → `addMovie`.

**Error handling?** GraphQL svarer typisk med HTTP **200**. Fejl lægges i en `errors`-liste i JSON, og `data` bliver `null`. Modsat REST, der bruger forskellige status codes.

**GraphQL-specifik sikkerhed?** Ét kald kan grave dybt i grafen → **resource-exhaustion (DoS)**: dybe queries og alias-misbrug. Vi forsvarer os med en depth limiter + alias limiter.

---

## Konceptuelle spørgsmål (21–23)

### 21 — Overfetching og underfetching

**Overfetching** = for meget data (REST har fast response-form → man får alle fields, også dem man ikke skal bruge). **Underfetching** = for lidt → man må lave flere kald for at samle alt.

**GraphQL løser begge:** klienten vælger fields, og nested data hentes i ét kald.

```graphql
{ movie(id: 1) { title genres { name } } }
```
```json
{ "data": { "movie": { "title": "Inception",
  "genres": [{ "name": "Action" }, { "name": "Sci-Fi" }] } } }
```
- Ingen overfetching: kun `title` + genrernes `name` returneres.
- Ingen underfetching: film + genrer i ét kald (i REST: `/movies/1` **og** `/movies/1/genres`).

### 22 — Hvordan virker GraphQL (operationer, fordele/ulemper)

Ét endpoint, HTTP POST, JSON. Klienten sender en request; serveren kører de relevante resolvers og bygger en response i **samme form**, pakket i `data`. Operationer: **query** (read), **mutation** (write-then-read), **subscription** (realtid).

**Fordele:** lavere latency (nested data i ét kald) · ingen versionering (grafen vokser bare) · god til mobil.
**Ulemper:** DoS-risiko (dybe queries, alias-misbrug) · POST = ikke cacheable · stejl læringskurve · mest moden i JS-økosystemet.

### 23 — Hvordan specificeres syntaksen? (SDL)

Via et **schema** i **SDL**: object types i UpperCamelCase (`Movie`), fields i lowerCamelCase (`releaseYear`), scalars (`Int`, `String`, `ID`...), modifiers (`!` non-null, `[ ]` liste), og to root types: **`Query`** (read) og **`Mutation`** (write). Hos os skrives det i Python og genereres af Strawberry. Se den fulde SDL nedenfor.

---

## Projekt-spørgsmål (vis i kode)

### Hvor sker integrationen? (request → resolver → service → DB)

En request rejser sådan her gennem koden:

1. **`app/main.py`** (l. 48, 82) — `GraphQLRouter` modtager `POST /graphql` og kører den mod `schema`. Security-extensions (depth/alias) tjekkes først.
2. **Resolver** i `app/schema/queries.py` (`Query.movie`, l. 15):
   ```python
   def movie(self, id: strawberry.ID) -> Optional[Movie]:
       row = movies_service.get_by_id(int(id))   # <-- integration: resolver → service
       return movie_from_row(row) if row else None
   ```
3. **Service** i `app/services/movies_service.py` (`get_by_id`, l. 19):
   ```python
   with get_db() as conn:                          # <-- integration: service → database
       return conn.execute("SELECT ... FROM movies WHERE id = ?", (movie_id,)).fetchone()
   ```
4. **`app/utils/db.py`** åbner SQLite-forbindelsen; `movie_from_row()` (types.py, l. 58) mapper row → `Movie`.
5. Bad klienten også om `genres`, kører `Movie.genres` (types.py, l. 49) *lazily* og kalder `genre_service`.

**Kort:** HTTP → `main.py` → resolver (`queries`/`mutations`) → service → `db.py` → SQLite, og retur.

### Forklar queries (vis i kode)

**Hvor:** `app/schema/queries.py` (`Query.movie` l. 15, `Query.movies` l. 22).
**Hvad sker der:** `movie(id)` henter én film (eller `null`); `movies(...)` henter en liste med **filtering** (`genre`, `year`) og **pagination** (`limit`, `offset`). Limit clampes til 1–100.

```python
def movies(self, genre=None, year=None, limit=DEFAULT_PAGE_SIZE, offset=0) -> list[Movie]:
    limit = max(1, min(limit, MAX_PAGE_SIZE))   # <-- hard cap: max 100 pr. side
    offset = max(0, offset)
    rows = movies_service.get_all(genre=genre, year=year, limit=limit, offset=offset)
    return [movie_from_row(r) for r in rows]
```

```graphql
{ movies(genre: "Sci-Fi", limit: 3) { title releaseYear } }
```
```json
{ "data": { "movies": [
  { "title": "Blade Runner 2049", "releaseYear": 2017 },
  { "title": "Interstellar", "releaseYear": 2014 },
  { "title": "Inception", "releaseYear": 2010 } ] } }
```

### Forklar mutations (vis i kode)

**Hvor:** `app/schema/mutations.py` (`add_movie` l. 23, `update_movie` l. 44, `delete_movie` l. 68).
**Hvad sker der:** `addMovie` opretter en film (+ kobler genrer) og returnerer hele `Movie` → write-then-read. `updateMovie` = partial update (udeladte fields beholder gammel værdi). `deleteMovie` returnerer `true`, fejler hvis filmen ikke findes.

```python
@strawberry.mutation
def add_movie(self, title, release_year, ..., genre_ids=None) -> Movie:
    row = movies_service.create(title=title, release_year=release_year, ...,
                                genre_ids=[int(g) for g in (genre_ids or [])])
    return movie_from_row(row)   # <-- write, derefter read: klienten vælger hvad der returneres
```

```graphql
mutation { addMovie(title: "Dune", releaseYear: 2021, genreIds: ["3"]) { id title genres { name } } }
```
```json
{ "data": { "addMovie": { "id": "11", "title": "Dune", "genres": [{ "name": "Sci-Fi" }] } } }
```

### Forklar SDL-kode

**Hvor:** `schema.graphql` (genereret af `export_schema.py` via `schema.as_str()`).
**Pointe:** code-first → Strawberry laver SDL'en ud fra Python-klasserne og oversætter til camelCase. `!` = non-null, `[ ]` = liste, `Query`/`Mutation` = root types.

```graphql
type Movie {
  id: ID!            # non-null
  title: String!     # non-null
  releaseYear: Int!
  runtimeMinutes: Int   # nullable (intet "!")
  director: String
  synopsis: String
  genres: [Genre!]!  # non-null liste af non-null Genre  <-- gør det til en graf
}

type Genre { id: ID!  name: String!  movies: [Movie!]! }

type Query {
  movie(id: ID!): Movie                 # kan give null
  movies(genre: String = null, year: Int = null, limit: Int! = 20, offset: Int! = 0): [Movie!]!
}

type Mutation {
  addMovie(title: String!, releaseYear: Int!, ..., genreIds: [ID!] = null): Movie!
  updateMovie(id: ID!, ...): Movie!
  deleteMovie(id: ID!): Boolean!
}
```

`Movie.genres` ↔ `Genre.movies` peger på hinanden — det er det, der gør schema'et til en *graf*.

### Kør testene + request/response-format

Start: `poetry run uvicorn app.main:app --reload` → GraphiQL på `http://localhost:8000/graphql`, eller importér `postman/graphql_collection.json`.

**Request** = POST til `/graphql`, JSON med `query` (+ evt. `variables`):
```json
{ "query": "query($id: ID!){ movie(id:$id){ title } }", "variables": { "id": "2" } }
```
**Response** = JSON med `data` i samme form som requesten:
```json
{ "data": { "movie": { "title": "The Dark Knight" } } }
```

**Positiv vs. negativ test:**
- Positiv: gyldigt `id` → data.
- Negativ "ikke fundet": `movie(id: 999)` → `{ "data": { "movie": null } }` (ikke en fejl).
- Negativ "validation error": fejl i `errors`, `data: null`:
  ```json
  { "data": null, "errors": [{ "message": "Release year must be between 1888 and 2100." }] }
  ```

### SQL-injection, XSS, CSRF (vis i kode)

**SQL-injection** — `app/services/movies_service.py`: input bindes som parametre (`?`), aldrig sat ind i strengen.
```python
conn.execute("SELECT ... FROM movies WHERE id = ?", (movie_id,))   # <-- parameterized query
```

**XSS** — API'et returnerer **JSON, ikke HTML** → browseren eksekverer ikke indholdet.

**CSRF** — `app/main.py` (l. 64): ingen cookies (`allow_credentials=False`), CORS låst til kendte origins.
```python
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
    allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
```

**GraphQL-DoS** — `app/utils/security.py` (l. 42): depth + alias limiter.
```python
return [QueryDepthLimiter(max_depth=MAX_QUERY_DEPTH),    # > 5 niveauer afvises
        MaxAliasesLimiter(max_alias_count=MAX_ALIASES)]  # > 15 aliaser afvises
```
Fejlbeskeder: `'anonymous' exceeds maximum operation depth of 5` · `20 aliases found. Allowed: 15`. Dertil clampes `limit` til max 100 i `queries.py`.

---

## Demo — tre forespørgsler at have klar

```graphql
# 1) Nested data (løser over-/underfetching)
{ movie(id: 1) { title releaseYear genres { name } } }

# 2) Filtering + pagination
{ movies(genre: "Sci-Fi", limit: 3) { title releaseYear } }

# 3) Mutation (write-then-read)
mutation { addMovie(title: "Dune", releaseYear: 2021, genreIds: ["3"]) { id title genres { name } } }
```

---

Alt er **JSON over HTTP POST** til ét endpoint (`/graphql`). Response har samme form som requesten, pakket i `data`; fejl lægges i `errors`, og HTTP-status er typisk 200.