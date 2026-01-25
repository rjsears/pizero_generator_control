# GenMaster - Generator Control System Master Controller
# Multi-architecture Dockerfile (linux/amd64, linux/arm64)
#
# Build locally:
#   docker build -t genmaster:local .
#
# Build multi-arch:
#   docker buildx build --platform linux/amd64,linux/arm64 -t rjsears/genmaster:latest --push .

# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy package files first for better caching
COPY frontend/package.json ./

# Install dependencies
RUN npm install --legacy-peer-deps

# Copy frontend source
COPY frontend/ .

# Build production assets
RUN npm run build

# =============================================================================
# Stage 2: Python Runtime
# =============================================================================
FROM python:3.11-slim-bookworm AS runtime

# Labels for container registry
LABEL org.opencontainers.image.title="GenMaster"
LABEL org.opencontainers.image.description="Generator Control System - Master Controller"
LABEL org.opencontainers.image.source="https://github.com/rjsears/pizero_generator_control"
LABEL org.opencontainers.image.vendor="rjsears"
LABEL org.opencontainers.image.licenses="MIT"

# Build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=latest

# Additional labels with build info
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.version="${VERSION}"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app \
    VIRTUAL_ENV=/opt/venv

# Create non-root user
RUN groupadd --gid 1000 genmaster \
    && useradd --uid 1000 --gid genmaster --shell /bin/bash --create-home genmaster

# Install system dependencies
# Note: GPIO packages (gpiozero, rpi-lgpio) are installed via pip in requirements.txt
# docker.io provides the Docker CLI for container management (nginx reload, etc.)
# gcc and python3-dev are needed to compile psutil from source
# network-manager provides nmcli for WiFi configuration
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    iputils-ping \
    docker.io \
    gcc \
    python3-dev \
    network-manager \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create virtual environment
RUN python -m venv ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

# Create application directories
RUN mkdir -p ${APP_HOME}/app ${APP_HOME}/static ${APP_HOME}/logs ${APP_HOME}/data \
    && chown -R genmaster:genmaster ${APP_HOME}

WORKDIR ${APP_HOME}

# Copy and install Python dependencies first (better caching)
COPY --chown=genmaster:genmaster backend/requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# Copy backend application
COPY --chown=genmaster:genmaster backend/app ./app

# Copy built frontend from builder stage
COPY --from=frontend-builder --chown=genmaster:genmaster /build/dist ./static

# Copy Alembic configuration
COPY --chown=genmaster:genmaster backend/alembic.ini .
COPY --chown=genmaster:genmaster backend/alembic ./alembic

# Copy startup scripts
COPY --chown=genmaster:genmaster docker/entrypoint.sh /entrypoint.sh
COPY --chown=genmaster:genmaster docker/wait-for-db.sh /wait-for-db.sh
RUN chmod +x /entrypoint.sh /wait-for-db.sh

# Switch to non-root user
USER genmaster

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default command
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
