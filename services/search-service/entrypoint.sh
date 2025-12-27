#!/bin/bash
set -e

echo "================================================"
echo "Search Service - Starting..."
echo "================================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
# Extract host and port from DATABASE_URL for Supabase compatibility
# Format: postgresql://user:pass@host:port/db
DB_HOST=$(echo $DATABASE_URL | sed -e 's|.*@\([^:/]*\).*|\1|')
DB_PORT=$(echo $DATABASE_URL | sed -e 's|.*:\([0-9]*\)/.*|\1|')

# Fallback to default port if extraction fails
if [ -z "$DB_PORT" ] || ! [[ "$DB_PORT" =~ ^[0-9]+$ ]]; then
    DB_PORT=5432
fi

echo "Checking PostgreSQL at ${DB_HOST}:${DB_PORT}..."
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Migrations completed successfully!"

# Start the application
echo "Starting Search Service..."
exec uvicorn app.app:app --host 0.0.0.0 --port 8000
