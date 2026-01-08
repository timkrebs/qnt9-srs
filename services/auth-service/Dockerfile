# Dockerfile for Fastapi Auth Service
FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app/app

# Health check for zero-downtime deployment
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

# Graceful shutdown: handle SIGTERM properly
STOPSIGNAL SIGTERM

CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8010"]

EXPOSE 8010