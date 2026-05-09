#!/bin/bash
# Wait for PostgreSQL database to be ready
#
# This script will wait until PostgreSQL is accepting connections
# before allowing the application to start.

set -e

# Configuration
MAX_RETRIES=${DB_MAX_RETRIES:-30}
RETRY_INTERVAL=${DB_RETRY_INTERVAL:-2}

# Extract connection details from DATABASE_URL or environment
if [ -n "$DATABASE_URL" ]; then
    # Parse DATABASE_URL (format: postgresql+asyncpg://user:pass@host:port/dbname)
    DB_HOST=$(echo "$DATABASE_URL" | sed -E 's/.*@([^:\/]+).*/\1/')
    DB_PORT=$(echo "$DATABASE_URL" | sed -E 's/.*:([0-9]+)\/.*/\1/' | grep -E '^[0-9]+$' || echo "5432")
    DB_USER=$(echo "$DATABASE_URL" | sed -E 's/.*:\/\/([^:]+):.*/\1/')
    DB_NAME=$(echo "$DATABASE_URL" | sed -E 's/.*\/([^?]+).*/\1/')
else
    DB_HOST="${DATABASE_HOST:-db}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_USER="${DATABASE_USER:-genmaster}"
    DB_NAME="${DATABASE_NAME:-genmaster}"
fi

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

retry_count=0
while [ $retry_count -lt $MAX_RETRIES ]; do
    if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
        echo "PostgreSQL is ready!"
        exit 0
    fi

    retry_count=$((retry_count + 1))
    echo "PostgreSQL not ready yet... (attempt $retry_count/$MAX_RETRIES)"
    sleep $RETRY_INTERVAL
done

echo "ERROR: PostgreSQL did not become ready in time!"
exit 1
