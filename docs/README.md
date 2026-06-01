# DOCS IN THIS FOLDER


# WEBSOCKET 

## Question: Explain the WebSockets implementation of the gRPC API's unary RPC (show in code). Compare both implementations.

# Unary er den her simple request og response message pattern, hvor klienten sender 1 specifikt request og serveren retunerer et specifikt response. 

# I gRPC hvor man har en formel kontrakt i form af proto filen, hvor man definer sine typer. Det har man ikke i samme grad i websockets, hvor man bruger DTO'er som kontrakten til at sende JSON til klienten.

#### Sammenligning #####
**Kontrakt:**: I gRPC definerer vi typerne i en .proto fil. i Webscokets bruger vi DTO'er + JSON
**Dataformat:**: gRPC bruger protobuf (som er binært), og Websockets bruger JSON (tekst)
**Typesikkerhed:**: gRPC er stærkt typesikret, da det er genereret kode. Hvorimod Webscokets er manuel JSON parsing.
**Fejlhåndtering:**: gRPC har indbyggede gRPC statuskoder, hvorimod websockets har tekstbeskeder som vi selv definirer.

#### KODE #####
// Klient sender ét film-id
int movieId = Integer.parseInt(payload.trim());

// Server slår op i databasen
Optional<Movie> movie = movieRepository.findById(movieId);

// Server svarer ÉN gang
session.sendMessage(new TextMessage(json));


## Question: Explain the WebSockets implementation of the gRPC API's bidirectional streaming RPC (show in code). Compare both implementations 

# Streaming

# Bidirectional streaming er lidt mere anderledes i forhold til Unary, da det i stedet for er en vedvarende forbindelse med et enkelt request og response, er streaming en vedvarende forbindelse mellem klienten og serveren, hvorpå begge parter løbende kan sende beskeder til hindanen uafhængigt af hindanen. 

#### KODE #####
// Klient sender ét film-id
String payload = message.getPayload();

// Server sender løbende – én film hvert 2. sekund
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
            session.sendMessage(new TextMessage(json));
            Thread.sleep(2000);
        }

#### Sammenligning #####
**Kontrakt:**: I gRPC anvender vi os af keywoarded "stream" i vores protofil for at angive det er en bidrectional streaming, begge veje. I websockets er der ikke en formel kontrakt for dette.
**Dataformat:**: gRPC bruger protobuf (som er binært), og Websockets bruger JSON (tekst)
**Typesikkerhed:**: gRPC er stærkt typesikret, da det er genereret kode. Hvorimod Webscokets er manuel JSON parsing.
**Fejlhåndtering:**: gRPC har indbyggede gRPC statuskoder, hvorimod websockets har tekstbeskeder som vi selv definirer.
**Browsersupport:**: grpc KRÆVER EN gRPC-web proxy, hvirmod Websockets er native i alle browsers.

Begge implementerer de samme to mønstre, unary og bidirectional streaming. Den største forskel er at gRPC har en formel .proto kontrakt der genererer typesikker kode automatisk, mens WebSocket er mere fleksibelt og browservenligt men kræver at vi selv definerer og parser JSON formatet.