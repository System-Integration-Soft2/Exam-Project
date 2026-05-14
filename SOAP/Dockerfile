FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder

WORKDIR /build

# Copy project file first for layer caching
COPY SOAP/src/SoapService.csproj ./SOAP/src/SoapService.csproj

# Restore runtime project only — tests are not needed in the production image
RUN dotnet restore SOAP/src/SoapService.csproj

# Copy source
COPY SOAP/src/ ./SOAP/src/

# Publish release build
RUN dotnet publish SOAP/src/SoapService.csproj -c Release -o /app/publish --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0

WORKDIR /app

# Install curl for the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/publish .

EXPOSE 8001

ENV ASPNETCORE_URLS=http://0.0.0.0:8001

CMD ["dotnet", "SoapService.dll"]
