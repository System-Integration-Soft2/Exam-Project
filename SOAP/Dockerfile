FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder

WORKDIR /build

# Copy project file first for layer caching of the restore step
COPY SOAP/src/SoapService.csproj ./SOAP/src/SoapService.csproj

# Restore runtime project only — tests are not needed in the production image
RUN dotnet restore SOAP/src/SoapService.csproj

# Copy source (invalidates cache only when source changes, not on csproj-only changes)
COPY SOAP/src/ ./SOAP/src/

# Publish release build (restore is a no-op here; packages are already in the NuGet cache layer)
RUN dotnet publish SOAP/src/SoapService.csproj -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0

WORKDIR /app

# Install curl for the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/publish .

EXPOSE 8001

ENV ASPNETCORE_URLS=http://0.0.0.0:8001

CMD ["dotnet", "SoapService.dll"]
