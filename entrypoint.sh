#!/bin/sh
set -e

echo "⏳ Waiting for Postgres..."

until pg_isready -h progressionx_postgres -U postgres; do
  sleep 2
done

echo "✅ Postgres is ready"

echo "🧠 Ensuring database exists..."

PGPASSWORD=postgres psql -h progressionx_postgres -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'progressionx'" | grep -q 1 || \
PGPASSWORD=postgres psql -h progressionx_postgres -U postgres -c "CREATE DATABASE progressionx"

echo "📦 Running Alembic migrations..."
alembic upgrade head

echo "🚀 Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000