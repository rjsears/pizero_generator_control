#!/bin/bash
# GenMaster Docker Entrypoint Script
#
# This script handles:
# 1. Waiting for PostgreSQL to be ready
# 2. Running database migrations
# 3. Starting the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Header
echo "============================================="
echo "  GenMaster - Generator Control System"
echo "  Master Controller Startup"
echo "============================================="
echo ""

# Check required environment variables
if [ -z "$DATABASE_URL" ] && [ -z "$DATABASE_HOST" ]; then
    log_error "DATABASE_URL or DATABASE_HOST must be set"
    exit 1
fi

# Construct DATABASE_URL if not provided
if [ -z "$DATABASE_URL" ]; then
    DB_USER="${DATABASE_USER:-genmaster}"
    DB_PASS="${DATABASE_PASSWORD:-genmaster}"
    DB_HOST="${DATABASE_HOST:-db}"
    DB_PORT="${DATABASE_PORT:-5432}"
    DB_NAME="${DATABASE_NAME:-genmaster}"
    export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    log_info "Constructed DATABASE_URL from components"
fi

# Wait for database to be ready
log_info "Waiting for PostgreSQL database..."
/wait-for-db.sh

# Run database migrations
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    log_info "Running database migrations..."

    # Create sync URL for Alembic (replace asyncpg with psycopg2)
    SYNC_DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/postgresql+asyncpg/postgresql/')
    export SYNC_DATABASE_URL

    if alembic upgrade head; then
        log_info "Database migrations completed successfully"
    else
        log_error "Database migrations failed!"
        exit 1
    fi
else
    log_warn "Skipping database migrations (RUN_MIGRATIONS=false)"
fi

# Create default config records if needed
log_info "Ensuring default configuration records..."
python -c "
from app.database import SessionLocal, init_database
from app.models import SystemState, Config
init_database()
db = SessionLocal()
try:
    if not db.query(SystemState).first():
        db.add(SystemState())
        db.commit()
        print('Created default SystemState')
    if not db.query(Config).first():
        db.add(Config())
        db.commit()
        print('Created default Config')
finally:
    db.close()
" 2>/dev/null || log_warn "Could not initialize default records (may already exist)"

# Show startup info
log_info "Starting GenMaster..."
echo ""
echo "  Environment: ${APP_ENV:-production}"
echo "  Debug Mode:  ${APP_DEBUG:-false}"
echo "  API Port:    8000"
echo ""

# Execute the main command
exec "$@"
