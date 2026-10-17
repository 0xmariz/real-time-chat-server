# Multi-stage Dockerfile for Real-Time Chat Server
# Stage 1: Build JAR using Maven
FROM maven:3.9.6-eclipse-temurin-17 AS build
WORKDIR /app

# Cache Maven dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source code and build production artifact
COPY src ./src
RUN mvn clean package -DskipTests -B

# Stage 2: Minimal Production JRE Runtime
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Create non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

# Copy JAR from build stage
COPY --from=build /app/target/realtime-chat-server-1.0.0.jar app.jar

# Expose HTTP/WebSocket port (default 8090) and raw TCP port (8888)
EXPOSE 8090 8888

# Dynamic port binding and memory optimization for cloud containers
ENV PORT=8090
ENV TCP_PORT=8888
ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0"

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
