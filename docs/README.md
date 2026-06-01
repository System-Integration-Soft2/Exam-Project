# DOCS IN THIS FOLDER

# WEBSOCKET

## Question: Explain the WebSockets implementation of the gRPC API's unary RPC (show in code). Compare both implementations.

# Unary

Unary er det simple request-response message pattern, hvor klienten sender ét specifikt request og serveren returnerer ét specifikt response.

I gRPC har man en formel kontrakt i form af en `.proto` fil, hvor man definerer sine typer. Denne kontrakt bruges til automatisk at generere stærkt typesikret kode til både klient og server.

I WebSockets har man ikke den samme formelle kontrakt. Her bruger man i stedet DTO’er som kontrakt og sender data som JSON mellem klient og server.

#### Sammenligning

**Kontrakt:**
I gRPC definerer vi typerne i en `.proto` fil. I WebSockets bruger vi DTO’er og JSON.

**Dataformat:**
gRPC bruger Protobuf (binært format), mens WebSockets typisk bruger JSON (tekstformat).

**Typesikkerhed:**
gRPC er stærkt typesikret, fordi koden genereres automatisk fra `.proto` filen.
I WebSockets håndterer vi selv parsing af JSON.

**Fejlhåndtering:**
gRPC har indbyggede gRPC statuskoder, mens WebSockets typisk bruger egne tekstbaserede fejlbeskeder.

#### KODE

```java id="b0vjs9"
// Klient sender ét film-id
int movieId = Integer.parseInt(payload.trim());

// Server slår filmen op i databasen
Optional<Movie> movie = movieRepository.findById(movieId);

// Server sender ét response tilbage
session.sendMessage(new TextMessage(json));
```

---

## Question: Explain the WebSockets implementation of the gRPC API's bidirectional streaming RPC (show in code). Compare both implementations.

# Bidirectional Streaming

Bidirectional streaming fungerer anderledes end Unary, fordi forbindelsen mellem klient og server forbliver åben under hele kommunikationen.

I stedet for ét request og ét response kan både klienten og serveren løbende sende beskeder til hinanden uafhængigt af hinanden.

I gRPC implementeres dette ved hjælp af keywordet `stream` i `.proto` filen, som gør det muligt at streame beskeder i begge retninger over samme forbindelse.

I WebSockets er forbindelsen persistent som standard, hvilket gør WebSockets velegnet til real-time kommunikation og streaming.

#### KODE

```java id="z6i6ij"
// Klient sender et request
String payload = message.getPayload();

// Server sender løbende filmopdateringer
List<Movie> movies = movieRepository.findAll();

for (Movie movie : movies) {

    MovieUpdate response = new MovieUpdate(
            movie.getId(),
            movie.getTitle(),
            movie.getReleaseYear(),
            movie.getRuntimeMinutes(),
            movie.getDirector(),
            movie.getSynopsis()
    );

    String json = objectMapper.writeValueAsString(response);

    // Sender én film ad gangen til klienten
    session.sendMessage(new TextMessage(json));

    // Simulerer streaming hvert 2. sekund
    Thread.sleep(2000);
}
```

#### Sammenligning

**Kontrakt:**
I gRPC anvender vi keywordet `stream` i `.proto` filen for at definere bidirectional streaming.
I WebSockets findes der ikke en formel kontrakt.

**Dataformat:**
gRPC bruger Protobuf (binært format), mens WebSockets bruger JSON (tekstformat).

**Typesikkerhed:**
gRPC er stærkt typesikret, fordi koden genereres automatisk.
I WebSockets håndterer vi selv parsing og strukturering af JSON.

**Fejlhåndtering:**
gRPC har indbyggede statuskoder, mens WebSockets typisk anvender egne tekstbaserede fejlbeskeder.

**Browsersupport:**
Browser-klienter kræver typisk en gRPC-Web proxy for at kommunikere med gRPC services, mens WebSockets er understøttet direkte i moderne browsere.

Begge implementeringer understøtter de samme kommunikationsmønstre: Unary og Bidirectional Streaming.

Den største forskel er, at gRPC benytter en formel `.proto` kontrakt, som automatisk genererer typesikker kode, mens WebSockets er mere fleksibelt og browservenligt, men kræver manuel håndtering af JSON og beskedstrukturer.
