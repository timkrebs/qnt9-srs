FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8011

# Health check for zero-downtime deployment
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8011/health || exit 1

# Graceful shutdown: handle SIGTERM properly
STOPSIGNAL SIGTERM

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]

