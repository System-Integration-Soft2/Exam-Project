# gRPC — Eksamensnoter & svar

> Dækker alle gRPC-relaterede eksamensspørgsmål + letforståelige "quick answers" + et
> filoverblik. **Alle linjenumre er tjekket mod koden** i `GRPC/` (juni 2026).
> Forretningsscenarie: et **filmkatalog med anmeldelser** (movies, genres, reviews).

---

## Del 1 — Quick answers (forklaret simpelt)

**Hvad er gRPC?**
Et framework der lader ét program kalde en funktion inde i et andet program på en anden
maskine — som om funktionen lå lokalt. Lavet af Google (2016). Analogi: i stedet for at
udfylde og sende en blanket frem og tilbage (sådan fungerer REST), trykker du bare på en
knap mærket `GetMovie(1)` på din egen maskine, og svaret kommer tilbage som om du selv
havde kørt funktionen. "RPC" = Remote Procedure Call = fjern-funktionskald.

**Hvad er Protobuf / en `.proto`-fil?**
Protocol Buffers er Googles format til at *beskrive* og *pakke* data. Du skriver en
`.proto`-fil med hvilke beskeder (`message`) og funktioner (`rpc`) der findes; derfra
**genereres** kode automatisk til både server og klient. Data sendes som kompakt **binær**
(ikke tekst som JSON) — ca. 4× mindre payload end JSON. Analogi: proto-filen er en
**kontrakt** begge parter er enige om på forhånd, så de slipper for at sende feltnavne med
hver eneste gang.

**Hvad er en stub?**
Den auto-genererede "proxy"-klasse på klientsiden. Den ligner en helt normal klasse med en
metode `GetMovie()`, men bag kulissen pakker den dit kald, sender det over netværket og
pakker svaret ud igen. Du mærker ikke at det er et netværkskald. Hos os:
`catalog_pb2_grpc.CatalogServiceStub`.

**Hvad er HTTP/2, og hvorfor bruger gRPC det?**
HTTP/2 er en nyere version af HTTP. Den vigtigste egenskab her er **multiplexing**: flere
samtidige "spor" (streams) på én forbindelse, og data kan flyde løbende begge veje. Det er
præcis dét, der gør **streaming** (og bidirektionel streaming) muligt. HTTP/1.1 kunne reelt
kun én anmodning ad gangen per forbindelse.

**De fire kommunikationstyper i gRPC:**

- **Unary** — 1 request → 1 response (fx hent én film). ← vores `GetMovie`
- **Server-streaming** — 1 request → en strøm af svar (fx live-log).
- **Client-streaming** — en strøm af requests → 1 svar (fx upload i bidder).
- **Bidirektionel** — begge sider sender strømme samtidig (fx chat). ← vores `LiveReviewFeed`

**Hvad er marshalling/serialisering?**
At oversætte data fra hukommelse til en byte-strøm der kan sendes over netværket
(*marshalling/serialisering*) og pakke den ud igen i den anden ende
(*unmarshalling/deserialisering*). Protobuf gør det binært og kompakt.

**Hvordan håndterer gRPC fejl?**
Med **statuskoder** — ligesom HTTP har 404/400. Fx `OK`, `NOT_FOUND`, `INVALID_ARGUMENT`.
I koden sættes de med `context.abort(StatusCode.X, "besked")`.

**Hvorfor er gRPC ikke sårbar over for CSRF?**
CSRF udnytter at en browser **automatisk** vedhæfter cookies til requests. gRPC bruger
ingen cookies, og browsere kan ikke lave native gRPC-kald. Derfor kan en ondsindet
hjemmeside ikke narre brugerens browser til at sende et gRPC-kald på dennes vegne — der er
intet at angribe.

---

## Del 2 — Filoverblik

| Fil | Hvad den indeholder / gør | Linjer du bør kunne pege på |
|-----|---------------------------|------------------------------|
| `proto/catalog.proto` | **Kontrakten.** proto3, package `catalog`, 4 messages + service `CatalogService` med 2 RPC'er. | `service` linje 36; `GetMovie` linje 39; `LiveReviewFeed` linje 43 |
| `generated/catalog_pb2.py` | Auto-genereret: message-klasser + (de)serialisering. **Rør aldrig.** | — |
| `generated/catalog_pb2_grpc.py` | Auto-genereret: server-baseklasse (`CatalogServiceServicer`) + klient-`Stub`. **Rør aldrig.** | — |
| `server.py` | **Selve API'et.** Implementerer begge RPC'er; starter serveren på port 9000. | `GetMovie` 26–45; `LiveReviewFeed` 47–86; `serve()` 89–95 |
| `db.py` | **Al SQL** (data-laget). Parameteriserede queries = SQLi-forsvar. Fejler højlydt hvis `catalog.db` mangler. | `fetch_movie` 33–56; `fetch_new_reviews_for_movies` 65–85 |
| `security.py` | `sanitize_output` (HTML-escape mod XSS) + validerings­funktioner. | `sanitize_output` 7–10; `validate_movie_id` 13–15 |
| `client.py` | CLI-testklient. `get <id>` = unary; `feed <ids>` = stream. Viser stub-brug. | `call_get_movie` 21–34; `call_live_review_feed` 37–53 |
| `add_test_review.py` | Hjælpescript der indsætter et review direkte i DB'en, så streaming-demoen har noget at sende. **Ikke en del af API'et.** | — |
| `requirements.txt` | `grpcio`, `grpcio-tools`, `protobuf` (pinned). | — |
| `Dockerfile` | `python:3.11-slim`, installerer deps, kører `server.py`, `EXPOSE 9000`. | — |
| `postman_tests/test_plan.md` | 6 tests (3 × `GetMovie`, 3 × `LiveReviewFeed` inkl. XSS) + screenshots. Postman kan ikke eksportere gRPC-kald, derfor dokumenteret manuelt. | — |

**Arkitektur-note (hvis censor spørger til lagdeling):** SQL'en ligger korrekt isoleret i
`db.py` (data-laget). Til forskel fra REST/GraphQL har gRPC ikke et separat service-lag —
`server.py` håndterer både transport *og* forretningslogik (især streaming-loopet). Bevidst
svar: "Vi fulgte gRPC's quickstart-mønster; bagklogt ville vi trække et service-lag ud som i
REST/GraphQL, så handleren kun stod for transport."

---

## Del 3 — Eksamensspørgsmålene besvaret

Fra eksamensinformationen er **disse** spørgsmål gRPC-relevante:

*Praktiske (vis kode):* proto-filen · unary RPC · bidirektionel streaming RPC · kør testene
· (tværgående) SQLi/XSS/CSRF · "peg på konkrete linjer" · WebSockets-sammenligning.
*Konceptuelle (de eksakte, mindst 2 per studerende):* **Q24** og **Q25** (+ **Q16** om
HTTP-versioner er tæt forbundet).

### Q24 — How do gRPC APIs work, including advantages and typical use cases

gRPC er Googles RPC-framework. Klienten kalder en metode på en **stub** (en auto-genereret
proxy). Frameworket **serialiserer** argumenterne til binær Protobuf, sender dem over
**HTTP/2**, serveren **deserialiserer**, kører funktionen og sender svaret tilbage samme vej.
Kontrakten ligger i en `.proto`-fil, hvorfra al kode genereres til både server og klient.

Det understøtter fire kald-typer: unary, server-streaming, client-streaming og
bidirektionel streaming.

**Fordele:** kompakt binærformat (hurtigere/mindre end JSON), lav latency via HTTP/2,
stærkt typet kontrakt (færre fejl, let vedligehold), kode­generering til mange sprog
(sprog-agnostisk — en Java-klient kan tale med en Python-server), og indbygget streaming.
**Ulemper/begrænsninger:** ikke browser-venligt uden en proxy, binærformatet er ikke
menneske-læsbart, og det er mindre velegnet til offentlige web-API'er.

**Typiske use cases:** intern microservice-kommunikation, realtids-/streaming-systemer,
mobile backends (begrænset båndbredde), IoT. *Ikke* egnet når API'et repræsenterer
ressourcer (brug REST), når man har gavn af caching, eller når det skal følge web-konventioner.

> I vores projekt: `GetMovie` er "hent én række fra databasen" (lærebogseksemplet på unary),
> og `LiveReviewFeed` er et realtids-feed af nye anmeldelser (streaming).

### Q25 — How is a gRPC API's syntax specified?

Via en **`.proto`-fil** skrevet i **Protocol Buffers IDL** (Interface Description Language).
Man angiver `syntax = "proto3"`, et `package`, et antal `message`-typer (dataformaterne) og
en `service`-blok med `rpc`-metoder. Hvert felt i en message har et **feltnummer** (`= 1`,
`= 2`, …) — nødvendigt fordi data serialiseres til binær: nummeret, ikke navnet, identificerer
feltet på wiren.

`grpc_tools.protoc`-compileren oversætter `.proto`-filen til sprog­specifik kode — hos os
`catalog_pb2.py` (messages) og `catalog_pb2_grpc.py` (server-stub + klient-stub). Filen er
**sprog-agnostisk**: samme `.proto` kan generere både en Python-server og en Java-klient.

Navnekonventioner (proto-style guide): `service` og `rpc` i `UpperCamelCase`, messages i
`UpperCamelCase`, felter i `lower_snake_case`. Vores fil følger dette.

### Q16 (bonus) — HTTP/1.1 vs HTTP/2 vs HTTP/3

Relevant fordi gRPC kører på HTTP/2. **HTTP/1.1:** én request ad gangen per forbindelse
(head-of-line blocking), tekst-baseret. **HTTP/2:** binær, **multiplexing** (flere streams
på én TCP-forbindelse), header-komprimering, server push — fundamentet for gRPC-streaming.
**HTTP/3:** kører over **QUIC** (på UDP) i stedet for TCP, hvilket fjerner TCP's
head-of-line blocking og giver hurtigere opstart. gRPC bruger HTTP/2.

---

### Praktisk: Forklar proto-filen (vis kode)

**Fil:** `proto/catalog.proto`. Det er kontrakten — alt genereres herfra.

```protobuf
syntax = "proto3";
package catalog;

// ── Messages (dataformaterne) ──
message MovieRequest  { int64 movie_id = 1; }          // input til GetMovie

message MovieResponse {                                  // output fra GetMovie
  int64           id              = 1;
  string          title           = 2;
  int32           release_year    = 3;
  int32           runtime_minutes = 4;
  string          director        = 5;
  string          synopsis        = 6;
  repeated string genres          = 7;                   // 'repeated' = liste
}

message ReviewSubscribeRequest { int64 movie_id = 1; }   // klient → server i streamen
message ReviewUpdate {                                    // server → klient i streamen
  int64  review_id = 1; int64 movie_id = 2; string movie_title = 3;
  int32  rating    = 4; string comment = 5; string created_at  = 6;
}

// ── Service (de to RPC-metoder) ──
service CatalogService {
  rpc GetMovie (MovieRequest) returns (MovieResponse);                              // linje 39 — unary
  rpc LiveReviewFeed (stream ReviewSubscribeRequest) returns (stream ReviewUpdate); // linje 43 — bidi
}
```

**Det vigtige at sige:** feltnumrene (`= 1`, `= 2`) identificerer felterne på wiren.
`repeated` betyder en liste. Ordet **`stream` på *begge* sider** af `LiveReviewFeed` er
præcis dét, der gør den **bidirektionel**. `GetMovie` har intet `stream` → den er unary.

### Praktisk: Hvordan er den unary RPC implementeret? (vis kode)

**Server — `server.py` linje 26–45:**

```python
def GetMovie(self, request, context):
    try:
        security.validate_movie_id(request.movie_id)        # afvis ugyldigt input
    except ValueError as e:
        context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))

    movie = db.fetch_movie(request.movie_id)                # ét DB-opslag
    if movie is None:
        context.abort(grpc.StatusCode.NOT_FOUND, f"No movie with id {request.movie_id}")

    return catalog_pb2.MovieResponse(
        id=movie["id"],
        title=security.sanitize_output(movie["title"]),     # HTML-escape mod XSS
        release_year=movie["release_year"],
        runtime_minutes=movie["runtime_minutes"],
        director=security.sanitize_output(movie["director"]),
        synopsis=security.sanitize_output(movie["synopsis"]),
        genres=[security.sanitize_output(g) for g in movie["genres"]],
    )
```

**Klient — `client.py` linje 21–34:**

```python
with grpc.insecure_channel(SERVER) as channel:
    stub = catalog_pb2_grpc.CatalogServiceStub(channel)              # auto-genereret proxy
    response = stub.GetMovie(catalog_pb2.MovieRequest(movie_id=movie_id))
    print(response.title, response.genres)
```

**Det vigtige at sige:** Ét request ind, ét response ud. **Ingen `yield`, ingen iterator —
bare `return`** → det er dét, der gør den *unary*. `context.abort()` er gRPC's fejlhåndtering
(svarer til HTTP 400/404). På klienten ser `stub.GetMovie(...)` ud som et helt almindeligt
funktionskald — netværket er skjult.

### Praktisk: Hvordan er den bidirektionelle streaming RPC implementeret? (vis kode)

**Server — `server.py` linje 47–86:**

```python
def LiveReviewFeed(self, request_iterator, context):
    subscribed_ids = set()
    last_review_id = db.fetch_latest_review_id()      # send kun reviews der er NYERE end nu

    # Baggrundstråd: læser klientens indkommende strøm af film-IDs
    def consume_requests():
        for req in request_iterator:
            incoming.put(req)
    threading.Thread(target=consume_requests, daemon=True).start()

    # Hovedloop: poller DB hvert 2. sekund og yield'er nye reviews ud til klienten
    while context.is_active():
        # ... tag nye subscriptions fra køen, validér movie_id, læg i subscribed_ids ...
        if subscribed_ids:
            for r in db.fetch_new_reviews_for_movies(list(subscribed_ids), last_review_id):
                last_review_id = max(last_review_id, r["review_id"])
                yield catalog_pb2.ReviewUpdate(                 # yield = send i ud-strømmen
                    review_id=r["review_id"], movie_id=r["movie_id"],
                    movie_title=security.sanitize_output(r["movie_title"]),
                    rating=r["rating"], comment=security.sanitize_output(r["comment"]),
                    created_at=r["created_at"],
                )
        time.sleep(POLL_INTERVAL_SECONDS)               # = 2 sekunder
```

**Klient — `client.py` linje 37–53:**

```python
def request_generator():                  # generator = klientens UD-strøm (subscriptions)
    for mid in movie_ids:
        yield catalog_pb2.ReviewSubscribeRequest(movie_id=mid)

for update in stub.LiveReviewFeed(request_generator()):   # for-loop = klientens IND-strøm
    print(update.movie_title, update.rating, update.comment)
```

**Det vigtige at sige:** Begge strømme er åbne **samtidig** → bidirektionel. Serveren bruger
en **baggrundstråd** til at læse indkommende subscriptions, mens hovedloopet `yield`'er
reviews ud. Klienten bruger en **generator** til at sende, mens dens `for`-loop modtager.
`last_review_id` sættes til DB'ens nuværende max ved tilslutning, så kun anmeldelser oprettet
*efter* at man abonnerer bliver streamet (derfor indsætter testen et review *efter* subscribe).

> **Ærlig note (hvis censor graver):** feedet er **poll-baseret** (`time.sleep(2)` + DB-query),
> ikke ægte event-push, og hver stream optager én tråd i pool'en (`max_workers=10`). Fint til
> demo; til produktion ville man bruge pub/sub. Sig det selv — det viser overblik.

### Praktisk: Kør testene og forklar beskeder/responses

**Sådan kører du det live (cheat-sheet):**

```bash
# Terminal 1 — server
cd GRPC && python server.py            # "gRPC server listening on port 9000"
# Terminal 2 — unary
python client.py get 1                 # → Inception + genres, status OK
python client.py get 9999              # → Error: NOT_FOUND
python client.py get -1                # → Error: INVALID_ARGUMENT
# Terminal 3 — streaming
python client.py feed 1                # abonnér på film 1, lad den køre
python add_test_review.py 1 8 "Great"  # i en 4. terminal → dukker op i terminal 3
```

**Testplanen (`postman_tests/test_plan.md`) har 6 tests:** GetMovie positiv (id 1),
GetMovie not-found (9999), GetMovie invalid (-1), LiveReviewFeed modtager nyt review,
LiveReviewFeed ignorerer ugyldigt `movie_id: 0` (stream forbliver åben), og XSS-testen.

**Det vigtige at sige om beskeder/responses:** På wiren er alt **binær Protobuf over HTTP/2**
— Postman/printet viser det som JSON for læsbarhed. gRPC bruger sine **egne statuskoder**
(`OK`, `NOT_FOUND`, `INVALID_ARGUMENT`), ikke HTTP-statuskoder. Postman kan ikke eksportere
gRPC-collections, derfor er testene dokumenteret med screenshots.

### Praktisk: Hvordan forhindrer gRPC-API'et SQL-injection, XSS og CSRF?

**SQL-injection — `db.py`.** Hver eneste query bruger `?`-pladsholdere; ingen værdier
sættes sammen i strengen. Også det "farlige" sted — den dynamiske `IN (...)` — er korrekt:
f-strengen indsætter kun `?`-pladsholdere (én per ID), aldrig værdierne. Værdierne sendes
som parametre (`server.py`/`db.py` linje 65–85):

```python
placeholders = ",".join("?" for _ in movie_ids)        # → "?,?,?" — KUN pladsholdere
params = (*movie_ids, since_review_id)                  # værdierne sendes separat
rows = conn.execute(f"... WHERE r.movie_id IN ({placeholders}) AND r.id > ?", params)
```

**XSS — `security.py` linje 7–10.** Tekstfelter HTML-escapes på vej ud
(`html.escape`), så `<script>` bliver til `&lt;script&gt;`. Brugt i `server.py` på `title`,
`director`, `synopsis`, `genres` (GetMovie) og `movie_title`, `comment` (streamen).

```python
def sanitize_output(value):
    return html.escape(value, quote=True) if value is not None else ""
```

> **Ærlig note:** at escape'e inde i en *binær gRPC-payload* er strengt taget det forkerte
> lag (XSS hører hjemme i render-laget/browseren — en mobil-klient får `&lt;script&gt;` og
> skal af-escape). Det opfylder opgavekravet, men vær klar til at sige at du ved det.

**CSRF — ikke relevant.** gRPC bruger ingen cookies og kan ikke kaldes native fra en
browser, så der er **intet at implementere**. Forklar *hvorfor* (se Del 1) frem for at lede
efter kode.

### Praktisk: "Peg på de konkrete linjer hvor integrationen sker"

Integrationen = RPC-grænsen. Peg på: `proto/catalog.proto` (kontrakten), `server.py` linje
91 (`add_CatalogServiceServicer_to_server` — kobler din implementering til serveren) og linje
92 (`add_insecure_port("[::]:9000")` — åbner porten), samt selve `GetMovie`/`LiveReviewFeed`.
På klientsiden: `client.py` linje 22–23 (`insecure_channel` + `CatalogServiceStub`) — dér
oversættes et lokalt metodekald til et netværkskald.

### Praktisk: WebSockets-sammenligning (de to "compare both implementations"-spørgsmål)

To eksamensspørgsmål beder dig sammenligne gRPC's unary/bidi med **WebSocket**-servicens
tilsvarende endpoints. gRPC-siden:

| | gRPC | WebSocket (Spring Boot) |
|--|------|--------------------------|
| Unary | `GetMovie` | `ws://…/ws/movies/detail` |
| Bidi | `LiveReviewFeed` | `ws://…/ws/movies/reviews/stream` |
| Format | binær **Protobuf**, skema + kodegenerering | **JSON**-tekstframes, håndskrevet parsing |
| Kontrakt | `.proto` (stærkt typet) | ingen formel kontrakt |
| Fejl | gRPC-statuskoder | applikations-/close-koder |

**Det vigtige at sige:** Begge kører over én vedvarende forbindelse og kan streame. Forskel:
gRPC giver en *typet kontrakt + auto-genereret kode + kompakt binær*, mens WebSocket er
*rå JSON* man selv parser. (Detaljeret WS-kode hører til WebSocket-servicens egen
forberedelse — sig til hvis du vil have den gennemgået.)

---

## Del 4 — Hvad censor kan grave i (vær forberedt)

- **Authentication/TLS:** der er ingen. `add_insecure_port` = ingen kryptering, ingen auth.
  Bevidst scope: opgaven krævede kun auth på REST. Sig det selv.
- **XSS-laget:** escaping i en binær payload er debatérbart (se ovenfor).
- **`validate_rating`/`validate_comment` i `security.py` er ubrugt** — gRPC-servicen skriver
  aldrig (kun læser). Reviews kommer ind via `add_test_review.py`. Hvis du bliver spurgt
  "hvor validerer I rating?", så peg på at servicen er read-only.
- **Skalering:** poll hvert 2. sek. + én tråd per stream (`max_workers=10`).
- **Reflection/deadlines/interceptors:** ikke slået til (derfor importeres `.proto` manuelt i
  Postman). Kend begreberne — det er sandsynlige opfølgningsspørgsmål.

---

## Del 5 — Begreber i én linje (lyn-repetition)

RPC = kald funktion på fjern-maskine · gRPC = Googles RPC over HTTP/2 + Protobuf · Protobuf =
binært skema i `.proto` · stub = auto-genereret klient-proxy · marshalling = pak data til
bytes · unary = 1↔1 · bidi = strøm↔strøm samtidig · `stream` på begge sider = bidirektionel ·
`context.abort()` = sæt gRPC-statuskode · HTTP/2 multiplexing = forudsætning for streaming ·
CSRF n/a fordi ingen cookies.
