FROM --platform=$BUILDPLATFORM eclipse-temurin:21-jdk AS builder

WORKDIR /app

# Copy Maven wrapper and pom
COPY WEBSOCKET/pom.xml .
COPY WEBSOCKET/.mvn .mvn
COPY WEBSOCKET/mvnw .

# Download dependencies
RUN chmod +x mvnw
RUN ./mvnw dependency:go-offline

# Copy source
COPY WEBSOCKET/src ./src

# Build jar
RUN ./mvnw clean package -DskipTests

FROM eclipse-temurin:21-jre

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy built jar
COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8080

CMD ["java", "-jar", "app.jar"]