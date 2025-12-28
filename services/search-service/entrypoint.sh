#!/bin/bash
set -e

echo "================================================"
echo "Search Service - Starting..."
echo "================================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."

# Extract connection details from DATABASE_URL for Supabase compatibility
# Format: postgresql://user:pass@host:port/db
DB_USER=$(echo "$DATABASE_URL" | sed -e 's|.*://\([^:]*\):.*|\1|')
DB_HOST=$(echo "$DATABASE_URL" | sed -e 's|.*@||' -e 's|:.*||')
DB_PORT=$(echo "$DATABASE_URL" | sed -e 's|.*@[^:]*:||' -e 's|/.*||')

# Fallback to default port if extraction fails
if [ -z "$DB_PORT" ] || ! [[ "$DB_PORT" =~ ^[0-9]+$ ]]; then
    DB_PORT=5432
fi

echo "Checking PostgreSQL at ${DB_HOST}:${DB_PORT} (user: ${DB_USER})..."

# For Supabase pgbouncer, we need to specify the username
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        break
    fi
    echo "PostgreSQL is unavailable (attempt $((RETRY_COUNT+1))/$MAX_RETRIES) - sleeping"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT+1))
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: PostgreSQL did not become ready after $MAX_RETRIES attempts"
    echo "Attempting to start anyway - SQLAlchemy will retry..."
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"

# Start the application
echo "Starting Search Service..."
exec uvicorn app.app:app --host 0.0.0.0 --port 8000
