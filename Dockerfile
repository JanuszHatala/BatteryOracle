# ==============================================================================
# Multi-stage Dockerfile for BatteryOracle 2.0 (FastAPI + React 19 SPA)
# ==============================================================================

# Stage 1: Build React 19 Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build

# Copy package manifests and install dependencies
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source code and build production assets
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Runtime
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BATTERY_ORACLE_DB_PATH=/app/data/battery_oracle.db

WORKDIR /app

# Install curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY db.py parser.py llm_manager.py web_search.py telemetry_service.py schemas.py api_server.py ./

# Copy compiled frontend from builder into /app/static
COPY --from=frontend-builder /build/dist ./static

# Ensure persistent SQLite data directory exists
RUN mkdir -p /app/data

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8088/api/v1/health || exit 1

ENTRYPOINT ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8088"]
