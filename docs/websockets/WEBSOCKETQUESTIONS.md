# WebSocket

## Question: Explain the WebSockets implementation of the gRPC API's unary RPC (show in code). Compare both implementations.

### Unary

Unary er det simple request-response message pattern, hvor klienten sender ét specifikt request og serveren returnerer ét specifikt response.

I gRPC har man en formel kontrakt i form af en `.proto` fil, hvor man definerer sine typer. Denne kontrakt bruges til automatisk at generere stærkt typesikret kode til både klient og server.

I WebSockets har man ikke den samme formelle kontrakt. Her bruger vi i stedet DTO'er (`MovieIdRequest`, `MovieDetailResponse`, `ErrorResponse`) som kontrakt og sender data som JSON mellem klient og server.

#### Sammenligning

**Kontrakt:**
I gRPC definerer vi typerne i en `.proto` fil. I WebSockets bruger vi DTO'er og JSON — `MovieIdRequest` som indgående besked og `MovieDetailResponse` som svar.

**Dataformat:**
gRPC bruger Protobuf (binært format), mens WebSockets typisk bruger JSON (tekstformat).

**Typesikkerhed:**
gRPC er stærkt typesikret, fordi koden genereres automatisk fra `.proto` filen.
I WebSockets deserialiserer vi JSON via `ObjectMapper` til `MovieIdRequest` og håndterer selv parsing-fejl.

**Fejlhåndtering:**
gRPC har indbyggede gRPC statuskoder. WebSockets returnerer strukturerede JSON-fejlkuverter med `error`- og `message`-felter, f.eks. `{"error": "movie_not_found", "message": "No movie found with id 9999"}`.

#### Kode

```java
// Klient sender ét film-id som JSON
MovieIdRequest request = objectMapper.readValue(payload, MovieIdRequest.class);
// ^ kaster JacksonException ved ugyldig JSON → returnerer invalid_request-fejl

Integer movieId = request.getMovieId();

// Server slår filmen op i databasen
Optional<Movie> movieOpt = movieRepository.findById(movieId);

if (movieOpt.isEmpty()) {
    sendError(session, "movie_not_found", "No movie found with id " + movieId);
    return;
}

// Server bygger et MovieDetailResponse med HTML-escaped felter og genres-array
MovieDetailResponse response = new MovieDetailResponse(movieOpt.get());
// ^ escaper title, director, synopsis og genres via HtmlUtils.htmlEscape

// Server sender ét response tilbage
session.sendMessage(new TextMessage(objectMapper.writeValueAsString(response)));
```

---

## Question: Explain the WebSockets implementation of the gRPC API's bidirectional streaming RPC (show in code). Compare both implementations.

### Bidirectional Streaming

Begge WebSocket-endpoints holder forbindelsen åben — det er selve WebSocket-protokollens natur. Forskellen mellem Unary og Bidirectional Streaming er beskedmønsteret:

- **Unary** (`/ws/movies/detail`): request-response — klienten sender én besked, serveren svarer med én besked. Gentages så mange gange man vil på samme forbindelse.
- **Bidirectional Streaming** (`/ws/movies/reviews/stream`): begge sider kan sende beskeder uafhængigt af hinanden til enhver tid. Klienten sender abonnementer, serveren pusher nye anmeldelser — uden at vente på hinanden.

I gRPC implementeres dette ved hjælp af keywordet `stream` i `.proto` filen, som gør det muligt at streame beskeder i begge retninger over samme forbindelse. Klienten streamer film-id'er, og serveren streamer anmeldelser tilbage.

I WebSockets er forbindelsen persistent som standard. Her implementerer vi et pub/sub-mønster: klienten abonnerer på et film ved at sende `{"movieId": N}`, og serveren vedligeholder per-session abonnementstilstand og poller databasen hvert 2. sekund for nye anmeldelser, som derefter pushes til klienten som `ReviewResponse`-frames. Forbindelsen lukkes aldrig af serveren — `session.close()` kaldes ikke.

#### Kode

```java
// Per-session tilstand: hvilke film er abonneret på, og hvad er sidst set review-id
private final ConcurrentHashMap<String, SessionState> sessions = new ConcurrentHashMap<>();

// Når forbindelsen oprettes, startes en ScheduledExecutorService
state.scheduler = Executors.newSingleThreadScheduledExecutor();
state.scheduler.scheduleAtFixedRate(
        () -> pollAndPush(session, state),
        POLL_INTERVAL_MS, POLL_INTERVAL_MS, TimeUnit.MILLISECONDS
);

// Klient sender et abonnement
MovieIdRequest request = objectMapper.readValue(payload, MovieIdRequest.class);
state.subscribedMovieIds.add(movieId);
state.lastSeenByMovie.putIfAbsent(movieId, 0);

// Catch-up: send alle eksisterende anmeldelser for dette film med det samme
List<Review> catchUp = reviewRepository
        .findByMovieIdInAndIdGreaterThanOrderByIdAsc(List.of(movieId), 0);
for (Review review : catchUp) {
    synchronized (session) {
        session.sendMessage(new TextMessage(objectMapper.writeValueAsString(toResponse(review))));
    }
    state.lastSeenByMovie.merge(review.getMovieId(), review.getId(), Math::max);
}

// Polling-task: push nye anmeldelser hvert 2. sekund
private void pollAndPush(WebSocketSession session, SessionState state) {
    for (Integer movieId : state.subscribedMovieIds) {
        int sinceId = state.lastSeenByMovie.getOrDefault(movieId, 0);
        List<Review> newReviews = reviewRepository
                .findByMovieIdInAndIdGreaterThanOrderByIdAsc(List.of(movieId), sinceId);
        for (Review review : newReviews) {
            synchronized (session) {
                session.sendMessage(new TextMessage(objectMapper.writeValueAsString(toResponse(review))));
            }
            state.lastSeenByMovie.merge(review.getMovieId(), review.getId(), Math::max);
        }
    }
}
```

#### Sammenligning

**Kontrakt:**
I gRPC anvender vi keywordet `stream` i `.proto` filen for at definere bidirectional streaming.
I WebSockets bruger vi `MovieIdRequest` som abonnementsbesked og `ReviewResponse` som stream-frame — DTO'erne udgør kontrakten.

**Dataformat:**
gRPC bruger Protobuf (binært format), mens WebSockets bruger JSON (tekstformat).

**Typesikkerhed:**
gRPC er stærkt typesikret, fordi koden genereres automatisk.
I WebSockets håndterer vi selv parsing og strukturering af JSON via `ObjectMapper`.

**Fejlhåndtering:**
gRPC har indbyggede statuskoder. WebSockets returnerer strukturerede JSON-fejlkuverter (`{"error": "...", "message": "..."}`). Fejl på en enkelt besked lukker ikke forbindelsen — klienten kan fortsætte med at sende nye abonnementer på samme session.

**Browsersupport:**
Browser-klienter kræver typisk en gRPC-Web proxy for at kommunikere med gRPC services, mens WebSockets er understøttet direkte i moderne browsere.

Begge implementeringer understøtter  bidirectional streaming: begge sider sender uafhængigt af hinanden over samme forbindelse.
