# Agent Handoff: Docker Infrastructure

## Purpose
This document provides complete specifications for containerizing **GenMaster only**, including Dockerfile, docker-compose configuration, nginx setup, and container orchestration.

**Note**: GenSlave runs as a native Python application (not Docker) to conserve RAM on the Pi Zero 2W. See `05-genslave-backend.md` for GenSlave deployment details.

---

## Overview

**GenMaster** (Raspberry Pi 5 8GB + NVMe) runs as a containerized application with:
- FastAPI application container
- PostgreSQL 16 database container
- Nginx reverse proxy
- Optional Tailscale container (--profile tailscale)
- Optional Cloudflare Tunnel (--profile cloudflare)

**GenSlave** (Raspberry Pi Zero 2W) runs natively without Docker:
- Native Python with virtualenv
- SQLite database (file-based)
- systemd service management
- Native Tailscale installation

---

## GenMaster Docker Configuration

### Dockerfile

```dockerfile
# genmaster/Dockerfile
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user (but run as root for GPIO access)
# USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# genmaster/docker-compose.yml
version: '3.8'

services:
  # FastAPI Application
  genmaster:
    image: rjsears/genmaster:${GENMASTER_VERSION:-latest}
    container_name: genmaster
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      - APP_ENV=${APP_ENV:-production}
      - APP_DEBUG=${APP_DEBUG:-false}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - DATABASE_USER=${DATABASE_USER:-genmaster}
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - DATABASE_NAME=${DATABASE_NAME:-genmaster}
      - SLAVE_API_URL=${SLAVE_API_URL:-http://genslave:8000}
      - SLAVE_API_SECRET=${SLAVE_API_SECRET}
      - WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
      - HEARTBEAT_INTERVAL_SECONDS=${HEARTBEAT_INTERVAL_SECONDS:-60}
      - HEARTBEAT_FAILURE_THRESHOLD=${HEARTBEAT_FAILURE_THRESHOLD:-3}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - genmaster_logs:/app/logs
      - genmaster_data:/app/data
    devices:
      # GPIO device access for Raspberry Pi 5 (gpiozero uses lgpio backend)
      - /dev/gpiochip0:/dev/gpiochip0
      - /dev/gpiochip4:/dev/gpiochip4
      - /dev/gpiomem:/dev/gpiomem
    group_add:
      - gpio
      - dialout
    networks:
      - genmaster-internal
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # PostgreSQL Database
  db:
    image: postgres:16-alpine
    container_name: genmaster-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=${DATABASE_USER:-genmaster}
      - POSTGRES_PASSWORD=${DATABASE_PASSWORD}
      - POSTGRES_DB=${DATABASE_NAME:-genmaster}
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # PostgreSQL performance tuning for Pi 5 with 8GB RAM
    command: >
      postgres
      -c shared_buffers=512MB
      -c effective_cache_size=2GB
      -c maintenance_work_mem=256MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
      -c work_mem=10MB
      -c min_wal_size=1GB
      -c max_wal_size=4GB
      -c max_worker_processes=4
      -c max_parallel_workers_per_gather=2
      -c max_parallel_workers=4
      -c max_parallel_maintenance_workers=2
    networks:
      - genmaster-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-genmaster} -d ${DATABASE_NAME:-genmaster}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: genmaster-nginx
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - genmaster
    networks:
      - genmaster-net
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  # Tailscale Sidecar
  tailscale:
    image: tailscale/tailscale:latest
    container_name: genmaster-tailscale
    hostname: genmaster
    restart: unless-stopped
    environment:
      - TS_AUTHKEY=${TAILSCALE_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=false
      - TS_EXTRA_ARGS=--advertise-tags=tag:generator
    volumes:
      - tailscale_state:/var/lib/tailscale
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
      - NET_RAW
    network_mode: host
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

volumes:
  db_data:
  tailscale_state:

networks:
  genmaster-net:
    driver: bridge
```

### Docker Compose Override (Development)

```yaml
# genmaster/docker-compose.override.yml
version: '3.8'

services:
  genmaster:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - APP_DEBUG=true
    volumes:
      - ./app:/app/app:ro  # Live reload
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  # Don't start Tailscale in development
  tailscale:
    profiles:
      - production
```

### Docker Compose Production Overrides

```yaml
# genmaster/docker-compose.prod.yml
# Use: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

version: '3.8'

services:
  genmaster:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  # Optional Cloudflare Tunnel
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: genmaster-cloudflared
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped
    network_mode: host
    profiles:
      - cloudflare
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"
```

---

## GenSlave Deployment (Native - No Docker)

GenSlave runs as a **native Python application** on Raspberry Pi Zero 2W to conserve the limited 512MB RAM.

**Why Native instead of Docker?**
- Docker daemon overhead: ~50-100MB RAM
- Container images: additional storage requirements
- Limited benefit on single-application device
- Native systemd provides reliable service management

For complete GenSlave deployment instructions, see:
- `05-genslave-backend.md` - Application implementation
- `08-setup-scripts.md` - Installation script (genslave/setup.sh)

**Key differences from GenMaster:**
| Aspect | GenMaster (Docker) | GenSlave (Native) |
|--------|-------------------|-------------------|
| Hardware | Pi 5 8GB + NVMe | Pi Zero 2W 512MB |
| Database | PostgreSQL 16 | SQLite |
| Deployment | Docker Compose | systemd service |
| Networking | Docker container | Native Tailscale |

---

## Nginx Configuration

```nginx
# genmaster/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 256;
    use epoll;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    # Performance settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript
               application/xml application/xml+rss text/javascript;

    # Upstream for FastAPI
    upstream api {
        server genmaster:8000;
        keepalive 8;
    }

    # Geo-based access classification
    geo $access_level {
        default          "external";
        127.0.0.1/32     "internal";
        100.64.0.0/10    "internal";    # Tailscale CGNAT range
        172.16.0.0/12    "internal";    # Docker networks
        10.0.0.0/8       "internal";    # Private networks
        192.168.0.0/16   "internal";    # Private networks
    }

    server {
        listen 80;
        server_name _;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # Root for static files (Vue.js build)
        root /usr/share/nginx/html;
        index index.html;

        # API endpoints
        location /api/ {
            proxy_pass http://api;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Access-Level $access_level;
            proxy_set_header Connection "";

            # Timeouts
            proxy_connect_timeout 10s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;

            # Buffer settings
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # Static files with caching
        location /assets/ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Vue.js SPA - serve index.html for all routes
        location / {
            try_files $uri $uri/ /index.html;

            # No caching for index.html
            location = /index.html {
                expires -1;
                add_header Cache-Control "no-store, no-cache, must-revalidate";
            }
        }

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # Deny access to hidden files
        location ~ /\. {
            deny all;
        }
    }
}
```

---

## Database Initialization

GenMaster uses **Alembic migrations** for database schema management rather than init.sql scripts.

On first startup, the entrypoint script runs:
```bash
alembic upgrade head
```

This creates all tables and initializes default rows. See `02-database-schema.md` for the complete PostgreSQL schema.

**Note**: GenSlave uses SQLite with application-level initialization (no migrations needed for single-file database).

---

## Environment Files

### GenMaster .env.example

```bash
# genmaster/.env.example

# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your-secret-key-change-this

# PostgreSQL Database
DATABASE_USER=genmaster
DATABASE_PASSWORD=your-database-password-change-this
DATABASE_NAME=genmaster

# GenSlave Communication (use Tailscale IP)
SLAVE_API_URL=http://100.x.x.x:8000
SLAVE_API_SECRET=shared-secret-change-this

# Heartbeat Configuration
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# Webhooks (n8n)
WEBHOOK_BASE_URL=http://100.x.x.x:5678/webhook/generator
WEBHOOK_SECRET=webhook-secret-change-this

# Tailscale (optional - use --profile tailscale)
TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# Cloudflare Tunnel (optional - use --profile cloudflare)
CLOUDFLARE_TUNNEL_TOKEN=

# Logging
LOG_LEVEL=INFO
```

**Note**: GenSlave environment configuration is documented in `05-genslave-backend.md`.

---

## Container Management Scripts

These scripts are for **GenMaster only**. GenSlave uses systemd service commands (see `05-genslave-backend.md`).

### Start GenMaster

```bash
#!/bin/bash
# genmaster/scripts/start.sh

set -e
cd /opt/genmaster

echo "Starting GenMaster..."

# Pull latest images
docker compose pull

# Start services (migrations run automatically via entrypoint)
docker compose up -d

echo "GenMaster started successfully"
docker compose ps
```

### Stop GenMaster

```bash
#!/bin/bash
# genmaster/scripts/stop.sh

set -e
cd /opt/genmaster

echo "Stopping GenMaster..."
docker compose down

echo "GenMaster stopped"
```

### View Logs

```bash
#!/bin/bash
# genmaster/scripts/logs.sh

set -e
cd /opt/genmaster

SERVICE=${1:-}

if [ -n "$SERVICE" ]; then
    docker compose logs -f "$SERVICE"
else
    docker compose logs -f
fi
```

### Update GenMaster

```bash
#!/bin/bash
# genmaster/scripts/update.sh

set -e
cd /opt/genmaster

echo "Updating GenMaster..."

# Pull latest images from Docker Hub
docker compose pull

# Restart with new images (migrations run automatically)
docker compose up -d

echo "GenMaster updated successfully"
docker compose ps
```

---

## Systemd Service

### GenMaster Docker Service

```ini
# /etc/systemd/system/genmaster.service
[Unit]
Description=GenMaster Generator Control System
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/genmaster
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

### Enable GenMaster Service

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable genmaster.service
sudo systemctl start genmaster.service
```

**Note**: GenSlave uses a native Python systemd service (not Docker). See `05-genslave-backend.md` for the GenSlave systemd configuration.

---

## Resource Considerations

GenMaster runs on Raspberry Pi 5 with 8GB RAM, so resource limits are optional but can be configured for stability:

```yaml
# Optional: Add to docker-compose.yml services
services:
  genmaster:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  db:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G

  nginx:
    deploy:
      resources:
        limits:
          memory: 128M
        reservations:
          memory: 64M
```

**Note**: GenSlave runs natively on Pi Zero 2W without Docker, so container resource limits don't apply to it.

---

## Building for ARM

GenMaster images are built for multiple architectures via GitHub Actions CI/CD:

```bash
# Build multi-arch image locally
docker buildx build --platform linux/arm64,linux/amd64 -t rjsears/genmaster:latest --push .

# Build for specific architecture
docker buildx build --platform linux/arm64 -t genmaster:local .
```

The GitHub Actions workflow automatically builds and pushes to Docker Hub on tagged releases.

---

## Backup Configuration

### PostgreSQL Backup Script

```bash
#!/bin/bash
# genmaster/scripts/backup.sh

BACKUP_DIR="/opt/genmaster/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/genmaster_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"
cd /opt/genmaster

# Dump PostgreSQL database
docker compose exec -T db pg_dump -U genmaster genmaster | gzip > "$BACKUP_FILE"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}"/*.sql.gz | tail -n +8 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
```

### Restore from Backup

```bash
#!/bin/bash
# genmaster/scripts/restore.sh

BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

cd /opt/genmaster

# Stop application (keep database running)
docker compose stop genmaster nginx

# Restore database
gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U genmaster genmaster

# Restart application
docker compose start genmaster nginx

echo "Restore complete"
```

### Cron Job

```bash
# Add to crontab
# Daily backup at 2 AM
0 2 * * * /opt/genmaster/scripts/backup.sh >> /var/log/genmaster-backup.log 2>&1
```

**Note**: GenSlave uses SQLite which can be backed up by simply copying the database file. See `05-genslave-backend.md` for GenSlave backup procedures.

---

## Agent Implementation Checklist

### GenMaster (Docker)
- [ ] Create Dockerfile with multi-arch support
- [ ] Create docker-compose.yml with PostgreSQL
- [ ] Create nginx configuration files
- [ ] Create .env.example
- [ ] Create entrypoint and helper scripts
- [ ] Create management scripts (start, stop, logs, update)
- [ ] Create systemd service file
- [ ] Create backup/restore scripts
- [ ] Test GPIO access in container (Pi 5 with gpiozero/lgpio)
- [ ] Test PostgreSQL persistence
- [ ] Test Tailscale connectivity (profile)
- [ ] Test Cloudflare tunnel (profile)

### GenSlave (Native - see 05-genslave-backend.md)
- [ ] Native Python deployment
- [ ] SQLite database setup
- [ ] systemd service configuration
- [ ] Native Tailscale installation

---

## Related Documents

- `01-project-structure.md` - Project conventions
- `03-genmaster-backend.md` - GenMaster application
- `05-genslave-backend.md` - GenSlave application
- `07-networking.md` - Tailscale and Cloudflare configuration
- `08-setup-scripts.md` - Installation scripts
