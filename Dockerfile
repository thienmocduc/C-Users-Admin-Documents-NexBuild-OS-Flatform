FROM python:3.12-slim

# Prevent apt prompts & speed up Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies for asyncpg + cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (cached layer)
COPY backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy backend code — code imports via `api.*` so symlink backend → api
COPY backend/ ./api/

# Create required directories
RUN mkdir -p uploads keys

# Railway sets PORT dynamically — default to 8000 for local
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start FastAPI — use $PORT from Railway, single worker (Railway scales horizontally)
# --proxy-headers + --forwarded-allow-ips="*" so request.client.host reflects real client IP
# (needed for rate limiting behind Railway/Vercel proxy chain)
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers --forwarded-allow-ips="*"
