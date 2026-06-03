# gRPC — Eksamensnoter

## Filer — overblik

| Fil | Hvad den gør | Eksamensrelevans |
|-----|-------------|-----------------|
| `proto/catalog.proto` | Kontrakten — definerer beskeder og RPC-metoder | Skal du kende |
| `server.py` | Selve API'et — implementerer `GetMovie` og `LiveReviewFeed` | Skal du kende |
| `client.py` | Testskript til at kalde serveren og demonstrere begge RPCs | Skal du kende |
| `db.py` | Al databaselogik — viser SQL-injection-forebyggelse | Godt at kende |
| `security.py` | Input-validering og HTML-escaping — viser XSS-forebyggelse | Godt at kende |
| `generated/catalog_pb2*.py` | Auto-genereret fra `.proto` — rør den aldrig | Ikke nødvendigt |
| `add_test_review.py` | Indsætter test-reviews så streaming-demoen virker | Ikke nødvendigt |
| `Dockerfile` | Docker-opsætning | Ikke nødvendigt |

---

## Hurtige svar — én linje

**Hvad er gRPC?**  
gRPC = *Google Remote Procedure Call* — et framework til at kalde funktioner på en anden server som om de var lokale, over HTTP/2 med binær Protobuf-serialisering.

**Hvad står RPC for?**  
*Remote Procedure Call* — kald en funktion der kører på en anden maskine.

**Hvad er Protobuf?**  
*Protocol Buffers* — Googles binære serialiseringsformat, defineret i `.proto`-filer. Hurtigere og mere kompakt end JSON/XML.

**Hvad er en stub?**  
Auto-genereret proxy-klasse på klientsiden — den ser ud som en normal Python-klasse men sender kaldet over netværket.

**Hvad er forskellen på unary og streaming?**  
Unary: ét request, ét response. Streaming: én eller begge sider sender en strøm af beskeder over samme forbindelse.

**Hvorfor HTTP/2 og ikke HTTP/1.1?**  
HTTP/2 understøtter multiplexing (flere streams på én forbindelse) og er nødvendigt for bidirektionel streaming.

**Hvordan håndterer gRPC fejl?**  
Via statuskoder (`OK`, `NOT_FOUND`, `INVALID_ARGUMENT` osv.) sat med `context.abort()` — analogt med HTTP-statuskoder.

**Hvorfor er gRPC ikke sårbar over for CSRF?**  
Ingen cookies, ingen browser-support for native gRPC — en ondsindet side kan ikke sende et gRPC-kald på brugerens vegne.

**Hvad er `.proto`-filens rolle?**  
Den er den eneste kilde til sandhed — fra den genereres al kode til både server og klient på alle sprog.

**Typiske use cases for gRPC?**  
Intern microservice-kommunikation, realtids-datastreaming, mobile backends hvor båndbredde er begrænset.

---

## Forklar proto-filen (vis kode)

**Fil:** `proto/catalog.proto`

Proto-filen er **kontrakten** for servicen. Alt defineres her — message-typer, felttyper, feltnumre og RPC-signaturer. `grpc_tools.protoc` genererer al Python-koden i `generated/` automatisk fra denne fil.

```protobuf
// Messages — dataformater der sendes frem og tilbage
message MovieRequest        { int64 movie_id = 1; }
message MovieResponse       { int64 id = 1; string title = 2; ... repeated string genres = 7; }
message ReviewSubscribeRequest { int64 movie_id = 1; }
message ReviewUpdate        { int64 review_id = 1; string comment = 5; ... }

// Service — de to RPC-metoder
service CatalogService {
  rpc GetMovie (MovieRequest) returns (MovieResponse);                          // unary
  rpc LiveReviewFeed (stream ReviewSubscribeRequest) returns (stream ReviewUpdate); // bidi streaming
}
```

`stream` på begge sider af `LiveReviewFeed` gør den til **bidirektionel streaming**.

---

## Forklar den unary RPC (vis kode)

**Fil:** `server.py` linje 42–61, `client.py` linje 23–37

```python
# server.py — GetMovie modtager ét request og returnerer ét response
def GetMovie(self, request, context):
    security.validate_movie_id(request.movie_id)   # kaster ValueError ved ugyldigt input
    movie = db.fetch_movie(request.movie_id)
    if movie is None:
        context.abort(grpc.StatusCode.NOT_FOUND, f"No movie with id {request.movie_id}")
    return catalog_pb2.MovieResponse(
        title=security.sanitize_output(movie["title"]),  # HTML-escape mod XSS
        ...
    )
```

```python
# client.py — stub er en auto-genereret proxy fra .proto-filen
stub = catalog_pb2_grpc.CatalogServiceStub(channel)
response = stub.GetMovie(catalog_pb2.MovieRequest(movie_id=1))
```

Ingen `yield`, ingen iterator — plain `return` → det er det der gør den *unary*.  
`context.abort()` er gRPCs fejlhåndtering (svarende til HTTP 400/404).

---

## Forklar den bidirektionelle streaming RPC (vis kode)

**Fil:** `server.py` linje 65–103, `client.py` linje 40–59

```python
# server.py — LiveReviewFeed læser ind-stream og yield'er ud-stream samtidig
def LiveReviewFeed(self, request_iterator, context):
    subscribed_ids = set()
    last_review_id = db.fetch_latest_review_id()

    # Baggrundstråd: læser klientens indkommende stream (film-IDs)
    def consume_requests():
        for req in request_iterator:
            subscribed_ids.add(req.movie_id)
    threading.Thread(target=consume_requests, daemon=True).start()

    # Hovedloop: poller DB og sender nye anmeldelser til klienten
    while context.is_active():
        for r in db.fetch_new_reviews_for_movies(list(subscribed_ids), last_review_id):
            yield catalog_pb2.ReviewUpdate(...)   # yield sender til klientens stream
        time.sleep(2)
```

```python
# client.py — generator sender ind-stream, for-loop modtager ud-stream
for update in stub.LiveReviewFeed(request_generator()):
    print(update.comment)
```

Begge streams er åbne samtidig → **bidirektionel**. Serveren bruger en tråd til at læse mens den yield'er, klienten bruger en generator til at sende mens den itererer.

---

## Kør tests og forklar beskeder/responses

**Fil:** `postman_tests/test_plan.md`

| # | Metode | Input | Forventet |
|---|--------|-------|-----------|
| 1 | `GetMovie` | `movie_id: 1` | `OK` — Inception med genres |
| 2 | `GetMovie` | `movie_id: 9999` | `NOT_FOUND` |
| 3 | `GetMovie` | `movie_id: -1` | `INVALID_ARGUMENT` |
| 4 | `LiveReviewFeed` | subscribe → indsæt review | `ReviewUpdate` streames |
| 5 | `LiveReviewFeed` | `movie_id: 0` | Ignoreres, stream forbliver åben |
| 6 | `LiveReviewFeed` | XSS-payload i kommentar | Ankommer HTML-escaped |

Beskeder sendes som **binær Protobuf over HTTP/2** — Postman viser dem som JSON for læsbarhed. gRPC bruger egne statuskoder (`OK`, `NOT_FOUND`, `INVALID_ARGUMENT`) i stedet for HTTP-statuskoder.

---

## Konceptspørgsmål (ingen kode)

**Q24 — Hvordan fungerer gRPC?**  
Klienten kalder en metode på en **stub** (auto-genereret proxy). Frameworket serialiserer argumenterne til binær Protobuf, sender over HTTP/2 og deserialiserer svaret. Understøtter unary, server-streaming, client-streaming og bidirektionel streaming. Fordele: stærkt typet kontrakt, kompakt binærformat, HTTP/2 multiplexing, kodegenerering til mange sprog. Typiske use cases: intern microservice-kommunikation og realtids-streaming.

**Q25 — Hvordan specificeres syntaksen?**  
Via en `.proto`-fil skrevet i **Protocol Buffers IDL**. Man definerer `message`-typer og `service`-blokke. `grpc_tools.protoc` kompilerer filen til sprogspecifik kode — hos os `catalog_pb2.py` og `catalog_pb2_grpc.py`. Filen er sprogagnostisk: en Java-klient kan tale med en Python-server så længe begge bruger samme `.proto`.
