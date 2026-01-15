# Agent Handoff: Docker Infrastructure

## Purpose
This document provides complete specifications for containerizing GenMaster and GenSlave, including Dockerfiles, docker-compose configurations, nginx setup, and container orchestration.

---

## Overview

Both GenMaster and GenSlave run as containerized applications with:
- FastAPI application container
- MariaDB database container
- Nginx reverse proxy (GenMaster only)
- Tailscale sidecar container
- Optional Cloudflare Tunnel (GenMaster only)

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
    build:
      context: .
      dockerfile: Dockerfile
    container_name: genmaster-app
    restart: unless-stopped
    privileged: true  # Required for GPIO access
    environment:
      - APP_ENV=${APP_ENV:-production}
      - APP_DEBUG=${APP_DEBUG:-false}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - DATABASE_URL=mysql+pymysql://genmaster:${DB_PASSWORD}@db:3306/genmaster
      - SLAVE_API_URL=${SLAVE_API_URL}
      - SLAVE_API_SECRET=${SLAVE_API_SECRET}
      - WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL:-}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET:-}
    volumes:
      - ./data:/app/data  # For backups
      - /sys:/sys:ro      # For temperature readings
    depends_on:
      db:
        condition: service_healthy
    networks:
      - genmaster-net
    devices:
      - /dev/gpiomem:/dev/gpiomem  # GPIO access
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # MariaDB Database
  db:
    image: mariadb:10.11
    container_name: genmaster-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
      - MYSQL_DATABASE=genmaster
      - MYSQL_USER=genmaster
      - MYSQL_PASSWORD=${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - genmaster-net
    command: >
      --innodb_flush_log_at_trx_commit=2
      --sync_binlog=0
      --innodb_flush_method=O_DIRECT
      --skip-log-bin
      --general_log=0
      --slow_query_log=0
      --innodb_buffer_pool_size=64M
      --max_connections=20
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

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

## GenSlave Docker Configuration

### Dockerfile

```dockerfile
# genslave/Dockerfile
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
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run application (must run as root for GPIO/SPI/I2C access)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# genslave/docker-compose.yml
version: '3.8'

services:
  # FastAPI Application
  genslave:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: genslave-app
    restart: unless-stopped
    privileged: true  # Required for GPIO, SPI, I2C
    environment:
      - APP_ENV=${APP_ENV:-production}
      - APP_DEBUG=${APP_DEBUG:-false}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - API_SECRET=${API_SECRET}
      - DATABASE_URL=mysql+pymysql://genslave:${DB_PASSWORD}@db:3306/genslave
      - WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL:-}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET:-}
      - LCD_ENABLED=${LCD_ENABLED:-true}
    volumes:
      - /sys:/sys:ro      # Temperature readings
    depends_on:
      db:
        condition: service_healthy
    networks:
      - genslave-net
    devices:
      # GPIO access
      - /dev/gpiomem:/dev/gpiomem
      # I2C access
      - /dev/i2c-1:/dev/i2c-1
      # SPI access for LCD
      - /dev/spidev0.0:/dev/spidev0.0
      - /dev/spidev0.1:/dev/spidev0.1
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # MariaDB Database
  db:
    image: mariadb:10.11
    container_name: genslave-db
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=${DB_ROOT_PASSWORD}
      - MYSQL_DATABASE=genslave
      - MYSQL_USER=genslave
      - MYSQL_PASSWORD=${DB_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - genslave-net
    command: >
      --innodb_flush_log_at_trx_commit=2
      --sync_binlog=0
      --innodb_flush_method=O_DIRECT
      --skip-log-bin
      --general_log=0
      --slow_query_log=0
      --innodb_buffer_pool_size=48M
      --max_connections=10
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    logging:
      driver: "json-file"
      options:
        max-size: "5m"
        max-file: "2"

  # Tailscale Sidecar
  tailscale:
    image: tailscale/tailscale:latest
    container_name: genslave-tailscale
    hostname: genslave
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
  genslave-net:
    driver: bridge
```

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

## Database Initialization Scripts

### GenMaster init.sql

```sql
-- genmaster/init.sql
-- This runs when the database container is first created

-- Create initial system_state row
INSERT INTO system_state (id) VALUES (1)
ON DUPLICATE KEY UPDATE id = 1;

-- Create initial config row with defaults
INSERT INTO config (
    id,
    heartbeat_interval_seconds,
    heartbeat_failure_threshold,
    slave_api_url,
    slave_api_secret,
    webhook_enabled,
    temp_warning_celsius,
    temp_critical_celsius,
    disk_warning_percent,
    disk_critical_percent,
    ram_warning_percent,
    event_log_retention_days
) VALUES (
    1,
    60,
    3,
    'http://genslave:8000',
    'CHANGE_ME',
    TRUE,
    70,
    80,
    80,
    90,
    85,
    30
) ON DUPLICATE KEY UPDATE id = 1;
```

### GenSlave init.sql

```sql
-- genslave/init.sql
-- This runs when the database container is first created

-- Create initial system_state row
INSERT INTO system_state (id) VALUES (1)
ON DUPLICATE KEY UPDATE id = 1;

-- Create initial config row
INSERT INTO config (
    id,
    heartbeat_interval_seconds,
    heartbeat_failure_threshold,
    lcd_enabled,
    lcd_brightness
) VALUES (
    1,
    60,
    3,
    TRUE,
    100
) ON DUPLICATE KEY UPDATE id = 1;
```

---

## Environment Files

### GenMaster .env.example

```bash
# genmaster/.env.example

# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your-secret-key-change-this

# Database
DB_ROOT_PASSWORD=root-password-change-this
DB_PASSWORD=genmaster-password-change-this

# GenSlave Communication
SLAVE_API_URL=http://100.x.x.x:8000
SLAVE_API_SECRET=shared-secret-change-this

# Webhooks (n8n)
WEBHOOK_BASE_URL=http://100.x.x.x:5678/webhook/generator
WEBHOOK_SECRET=webhook-secret-change-this

# Tailscale
TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# Cloudflare Tunnel (optional)
CLOUDFLARE_TUNNEL_TOKEN=
```

### GenSlave .env.example

```bash
# genslave/.env.example

# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your-secret-key-change-this

# API Authentication (must match GenMaster's SLAVE_API_SECRET)
API_SECRET=shared-secret-change-this

# Database
DB_ROOT_PASSWORD=root-password-change-this
DB_PASSWORD=genslave-password-change-this

# Webhooks (direct failsafe notification)
WEBHOOK_BASE_URL=http://100.x.x.x:5678/webhook/generator
WEBHOOK_SECRET=webhook-secret-change-this

# LCD Display
LCD_ENABLED=true

# Tailscale
TAILSCALE_AUTHKEY=tskey-auth-xxxxx
```

---

## Container Management Scripts

### Start Script

```bash
#!/bin/bash
# scripts/start.sh

set -e

DEVICE=${1:-genmaster}

if [ "$DEVICE" = "genmaster" ]; then
    cd /opt/genmaster
elif [ "$DEVICE" = "genslave" ]; then
    cd /opt/genslave
else
    echo "Usage: $0 [genmaster|genslave]"
    exit 1
fi

echo "Starting $DEVICE..."

# Pull latest images
docker compose pull

# Run migrations
docker compose run --rm ${DEVICE} alembic upgrade head

# Start services
docker compose up -d

echo "$DEVICE started successfully"
docker compose ps
```

### Stop Script

```bash
#!/bin/bash
# scripts/stop.sh

set -e

DEVICE=${1:-genmaster}

if [ "$DEVICE" = "genmaster" ]; then
    cd /opt/genmaster
elif [ "$DEVICE" = "genslave" ]; then
    cd /opt/genslave
else
    echo "Usage: $0 [genmaster|genslave]"
    exit 1
fi

echo "Stopping $DEVICE..."
docker compose down

echo "$DEVICE stopped"
```

### Logs Script

```bash
#!/bin/bash
# scripts/logs.sh

set -e

DEVICE=${1:-genmaster}
SERVICE=${2:-}

if [ "$DEVICE" = "genmaster" ]; then
    cd /opt/genmaster
elif [ "$DEVICE" = "genslave" ]; then
    cd /opt/genslave
else
    echo "Usage: $0 [genmaster|genslave] [service]"
    exit 1
fi

if [ -n "$SERVICE" ]; then
    docker compose logs -f "$SERVICE"
else
    docker compose logs -f
fi
```

### Update Script

```bash
#!/bin/bash
# scripts/update.sh

set -e

DEVICE=${1:-genmaster}

if [ "$DEVICE" = "genmaster" ]; then
    cd /opt/genmaster
elif [ "$DEVICE" = "genslave" ]; then
    cd /opt/genslave
else
    echo "Usage: $0 [genmaster|genslave]"
    exit 1
fi

echo "Updating $DEVICE..."

# Pull latest code (if using git)
# git pull

# Rebuild containers
docker compose build --no-cache

# Run migrations
docker compose run --rm ${DEVICE} alembic upgrade head

# Restart with new images
docker compose up -d

echo "$DEVICE updated successfully"
```

---

## Systemd Service

### GenMaster Service

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

### GenSlave Service

```ini
# /etc/systemd/system/genslave.service
[Unit]
Description=GenSlave Generator Control System
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/genslave
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

### Enable Service

```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable genmaster.service  # or genslave.service
sudo systemctl start genmaster.service
```

---

## Resource Limits

For Pi Zero 2W with 512MB RAM, set container limits:

```yaml
# Add to docker-compose.yml services
services:
  genmaster:
    deploy:
      resources:
        limits:
          memory: 150M
        reservations:
          memory: 100M

  db:
    deploy:
      resources:
        limits:
          memory: 100M
        reservations:
          memory: 80M

  nginx:
    deploy:
      resources:
        limits:
          memory: 30M
        reservations:
          memory: 20M
```

---

## Building for ARM

When building on a different architecture:

```bash
# Build for ARM64 (Pi Zero 2W)
docker buildx build --platform linux/arm64 -t genmaster:latest .

# Or use multi-platform build
docker buildx build --platform linux/arm64,linux/amd64 -t genmaster:latest .
```

---

## Backup Configuration

### Database Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

DEVICE=${1:-genmaster}
BACKUP_DIR="/opt/${DEVICE}/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DEVICE}_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

cd /opt/${DEVICE}

# Dump database
docker compose exec -T db mysqldump -u root -p"${DB_ROOT_PASSWORD}" ${DEVICE} | gzip > "$BACKUP_FILE"

# Keep only last 7 backups
ls -t "${BACKUP_DIR}"/*.sql.gz | tail -n +8 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
```

### Cron Job

```bash
# Add to crontab
# Daily backup at 2 AM
0 2 * * * /opt/genmaster/scripts/backup.sh genmaster >> /var/log/genmaster-backup.log 2>&1
```

---

## Agent Implementation Checklist

- [ ] Create GenMaster Dockerfile
- [ ] Create GenMaster docker-compose.yml
- [ ] Create GenMaster docker-compose.override.yml (dev)
- [ ] Create GenMaster docker-compose.prod.yml
- [ ] Create GenMaster nginx.conf
- [ ] Create GenMaster init.sql
- [ ] Create GenMaster .env.example
- [ ] Create GenSlave Dockerfile
- [ ] Create GenSlave docker-compose.yml
- [ ] Create GenSlave init.sql
- [ ] Create GenSlave .env.example
- [ ] Create management scripts (start, stop, logs, update)
- [ ] Create systemd service files
- [ ] Create backup script
- [ ] Test GPIO access in containers
- [ ] Test I2C/SPI access for LCD
- [ ] Test database persistence
- [ ] Test Tailscale connectivity
- [ ] Verify resource limits work on Pi Zero 2W

---

## Related Documents

- `01-project-structure.md` - Project conventions
- `03-genmaster-backend.md` - GenMaster application
- `05-genslave-backend.md` - GenSlave application
- `07-networking.md` - Tailscale and Cloudflare configuration
- `08-setup-scripts.md` - Installation scripts
