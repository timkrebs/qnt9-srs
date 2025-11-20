#!/bin/bash
set -e

echo "================================================"
echo "Search Service - Starting..."
echo "================================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h ${DATABASE_URL##*@} -p 5432 > /dev/null 2>&1; do
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
