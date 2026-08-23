# Single-Stage Production Dockerfile for StokVigil AI FastAPI Backend
# Optimized for Google Cloud Run (Free Tier) with native C-extensions support

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Install build dependencies, curl for health checks, and OpenMP runtime for numpy/pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app ./app

# Expose default Cloud Run port
EXPOSE 8080

# Dynamic port binding with exec form for proper signal handling
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
