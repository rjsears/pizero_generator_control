# Agent Handoff: Setup Scripts

## Purpose
This document provides specifications for the installation scripts that configure GenMaster and GenSlave. Each device has its own setup script due to fundamentally different deployment approaches.

---

## Overview

### Deployment Differences

| Aspect | GenMaster | GenSlave |
|--------|-----------|----------|
| **Hardware** | Raspberry Pi 5 8GB + NVMe | Raspberry Pi Zero 2W |
| **Deployment** | Docker containers | Native Python + systemd |
| **Database** | PostgreSQL (Docker) | SQLite (file-based) |
| **Web Server** | Nginx (Docker) | Uvicorn only |
| **Setup Script** | `genmaster/setup.sh` | `genslave/setup.sh` |
| **Networking** | Docker Tailscale profile | Native Tailscale |

### Setup Scripts

1. **`genmaster/setup.sh`** - Full Docker deployment (~1300 lines)
   - PostgreSQL with performance tuning
   - Nginx reverse proxy
   - Optional Tailscale/Cloudflare profiles
   - Let's Encrypt SSL support

2. **`genslave/setup.sh`** - Lightweight native deployment
   - Python virtualenv setup
   - SQLite database
   - Native Tailscale installation
   - systemd service configuration

---

## Setup Script Architecture

### GenMaster (genmaster/setup.sh)

```
genmaster/setup.sh (Docker deployment)
├── Phase 1: System Preparation
│   ├── Update system packages
│   ├── Install Docker & Docker Compose
│   ├── Install Raspberry Pi 5 GPIO software (gpiozero + lgpio)
│   └── Configure system for NVMe SSD
│
├── Phase 2: Configuration
│   ├── Interactive prompts for settings
│   ├── PostgreSQL credentials
│   ├── Tailscale auth key
│   └── SSL certificate options
│
├── Phase 3: Docker Setup
│   ├── Create directory structure
│   ├── Generate .env file
│   ├── Configure nginx
│   └── Pull Docker images
│
├── Phase 4: Database Setup
│   ├── Start PostgreSQL container
│   ├── Wait for healthy status
│   └── Run Alembic migrations
│
├── Phase 5: Service Start
│   ├── Start all containers
│   ├── Create systemd service
│   └── Enable auto-start
│
└── Phase 6: Validation
    ├── Health checks
    ├── Display access URLs
    └── Credential summary
```

### GenSlave (genslave/setup.sh)

```
genslave/setup.sh (Native Python deployment)
├── Phase 1: System Preparation
│   ├── Update system packages
│   ├── Install Python 3.11+ and pip
│   ├── Enable I2C and SPI interfaces
│   └── Configure system for SD/SSD longevity
│
├── Phase 2: Hardware Validation
│   ├── Test Automation Hat Mini relay
│   ├── Test LCD display (ST7735)
│   └── Verify I2C/SPI communication
│
├── Phase 3: Application Setup
│   ├── Create virtualenv
│   ├── Install Python dependencies
│   ├── Initialize SQLite database
│   └── Configure .env file
│
├── Phase 4: Tailscale Setup
│   ├── Install Tailscale natively
│   ├── Authenticate with auth key
│   └── Test connectivity
│
├── Phase 5: Service Setup
│   ├── Create systemd service
│   ├── Configure log rotation
│   └── Enable auto-start
│
└── Phase 6: Validation
    ├── Health checks
    ├── Test relay operation
    └── Display Tailscale IP
```

---

## Setup Script Implementations

The actual setup scripts are already created in the repository:

- **`genmaster/setup.sh`** - Full Docker deployment for Pi 5 (~1300 lines)
- **`genslave/setup.sh`** - Lightweight native deployment for Pi Zero 2W

### Usage

**GenMaster Installation:**
```bash
# Download and run
curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genmaster/setup.sh -o setup.sh
chmod +x setup.sh
sudo ./setup.sh
```

**GenSlave Installation:**
```bash
# Download and run
curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genslave/setup.sh -o setup.sh
chmod +x setup.sh
sudo ./setup.sh
```

---

## Key Features of GenMaster Setup Script

The GenMaster setup script (`genmaster/setup.sh`) includes:

### Interactive Configuration
- Database credentials (auto-generated if not provided)
- Tailscale auth key
- SSL certificate options (Let's Encrypt via Cloudflare or Route53)
- GenSlave connection details

### Docker Compose Profiles
- Default: GenMaster + PostgreSQL + Nginx
- `--profile tailscale`: Add Tailscale container
- `--profile cloudflare`: Add Cloudflare Tunnel
- `--profile dev`: Development mode with hot reload

### Raspberry Pi 5 Specific
- gpiozero with lgpio backend for GPIO17 (Victron signal)
- NVMe SSD optimization
- Performance tuning for 8GB RAM

### Helper Functions
- Health checks
- Backup/restore scripts
- Update mechanism

---

## Key Features of GenSlave Setup Script

The GenSlave setup script (`genslave/setup.sh`) includes:

### Native Python Deployment
- Python 3.11+ virtualenv
- SQLite database (zero RAM overhead)
- systemd service management

### Hardware Support
- Automation Hat Mini relay control
- ST7735 LCD display
- I2C and SPI interface setup

### Memory Optimization
- No Docker daemon (~100MB saved)
- SQLite instead of PostgreSQL (~200MB saved)
- Native Tailscale instead of Docker container

### Tailscale Integration
- Native installation
- Auto-authentication with auth key
- tag:generator for ACL support

---

## Common Utility Functions

Both setup scripts share similar utility patterns:

```bash
# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging function
log() {
    local level=$1
    shift
    local message="$*"
    case $level in
        INFO)  echo -e "${BLUE}[INFO]${NC} $message" ;;
        OK)    echo -e "${GREEN}[OK]${NC} $message" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $message" ;;
    esac
}

# Print formatted header
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Additional utility functions...
# See actual setup scripts for complete implementation
```

**Note**: For the complete implementation, see:
- `genmaster/setup.sh` - Full Docker deployment script
- `genslave/setup.sh` - Native Python deployment script

---

## GenMaster Environment Configuration

The GenMaster setup script generates a `.env` file with:

```bash
# genmaster/.env (generated by setup.sh)

# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<auto-generated>

# PostgreSQL Database
DATABASE_USER=genmaster
DATABASE_PASSWORD=<auto-generated>
DATABASE_NAME=genmaster

# GenSlave Communication
SLAVE_API_URL=http://genslave:8000
SLAVE_API_SECRET=<auto-generated>

# Heartbeat Configuration
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# Webhooks (n8n)
WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
WEBHOOK_SECRET=<auto-generated>

# Tailscale (optional)
TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# Cloudflare (optional)
CLOUDFLARE_TUNNEL_TOKEN=

# Logging
LOG_LEVEL=INFO
```

---

## GenSlave Environment Configuration

The GenSlave setup script generates a `.env` file with:

```bash
# genslave/.env (generated by setup.sh)

# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<auto-generated>

# API Authentication (must match GenMaster's SLAVE_API_SECRET)
API_SECRET=<shared-with-genmaster>

# SQLite Database
DATABASE_PATH=/opt/genslave/data/genslave.db

# Webhooks (failsafe notifications only)
WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
WEBHOOK_SECRET=<shared-with-genmaster>

# LCD Display
LCD_ENABLED=true
LCD_BRIGHTNESS=100

# Logging
LOG_LEVEL=INFO
```

---

## Additional Helper Scripts

### GenMaster Health Check

```bash
#!/bin/bash
# genmaster/scripts/health-check.sh

echo "=== GenMaster Health Check ==="

# Container status
echo "Docker Containers:"
docker compose ps

# API health
echo "API Status:"
curl -s http://localhost/api/health | jq . 2>/dev/null || echo "API not responding"

# Database status
echo "PostgreSQL Status:"
docker compose exec -T db pg_isready -U genmaster

# Tailscale status (if enabled)
if docker ps | grep -q genmaster-tailscale; then
    echo "Tailscale Status:"
    docker exec genmaster-tailscale tailscale status
fi

# System resources
echo "System Resources:"
echo "  CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')%"
echo "  RAM: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "  Disk: $(df -h /opt/genmaster | awk 'NR==2{print $5}')"
echo "  Temp: $(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.1f°C", $1/1000}')"
```

### GenSlave Health Check

```bash
#!/bin/bash
# genslave/scripts/health-check.sh

echo "=== GenSlave Health Check ==="

# Service status
echo "Service Status:"
systemctl status genslave --no-pager

# API health
echo "API Status:"
curl -s http://localhost:8000/api/health | jq . 2>/dev/null || echo "API not responding"

# Database status
echo "SQLite Database:"
if [ -f /opt/genslave/data/genslave.db ]; then
    echo "  Size: $(du -h /opt/genslave/data/genslave.db | cut -f1)"
fi

# Tailscale status
echo "Tailscale Status:"
tailscale status

# Relay status
echo "Relay Status:"
curl -s http://localhost:8000/api/relay/status | jq . 2>/dev/null

# System resources
echo "System Resources:"
echo "  RAM: $(free -m | awk 'NR==2{printf "%dMB used / %dMB total (%.1f%%)", $3, $2, $3*100/$2}')"
echo "  Temp: $(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.1f°C", $1/1000}')"
```

### GenMaster Backup Script

```bash
#!/bin/bash
# genmaster/scripts/backup.sh

BACKUP_DIR="/opt/genmaster/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/genmaster_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"
cd /opt/genmaster

echo "Backing up PostgreSQL database..."
docker compose exec -T db pg_dump -U genmaster genmaster | gzip > "$BACKUP_FILE"

echo "Backing up configuration..."
cp .env "${BACKUP_DIR}/.env.${DATE}"

echo "Cleaning old backups (keeping last 7)..."
ls -t "${BACKUP_DIR}"/*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm

echo "Backup complete: $BACKUP_FILE"
```

### GenSlave Backup Script

```bash
#!/bin/bash
# genslave/scripts/backup.sh

BACKUP_DIR="/opt/genslave/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Backing up SQLite database..."
cp /opt/genslave/data/genslave.db "${BACKUP_DIR}/genslave_${DATE}.db"

echo "Backing up configuration..."
cp /opt/genslave/.env "${BACKUP_DIR}/.env.${DATE}"

echo "Cleaning old backups (keeping last 7)..."
ls -t "${BACKUP_DIR}"/*.db 2>/dev/null | tail -n +8 | xargs -r rm

echo "Backup complete"
```

---

## Agent Implementation Checklist

### GenMaster Setup Script (genmaster/setup.sh)
- [x] Create interactive setup script for Docker deployment
- [x] Implement Docker and Docker Compose installation
- [x] Implement PostgreSQL database configuration
- [x] Implement Nginx reverse proxy setup
- [x] Implement Tailscale container profile
- [x] Implement Cloudflare Tunnel profile
- [x] Implement Let's Encrypt SSL via certbot
- [x] Implement Pi 5 GPIO software (gpiozero + lgpio)
- [ ] Test on fresh Raspberry Pi 5

### GenSlave Setup Script (genslave/setup.sh)
- [x] Create native Python deployment script
- [x] Implement Python virtualenv setup
- [x] Implement SQLite database initialization
- [x] Implement Automation Hat Mini testing
- [x] Implement native Tailscale installation
- [x] Implement systemd service configuration
- [ ] Test on fresh Raspberry Pi Zero 2W

### Helper Scripts
- [x] Create GenMaster health-check.sh
- [x] Create GenSlave health-check.sh
- [x] Create GenMaster backup.sh (PostgreSQL)
- [x] Create GenSlave backup.sh (SQLite)
- [ ] Test all scripts on target hardware

---

## Related Documents

- `01-project-structure.md` - File structure created by setup
- `06-docker-infrastructure.md` - Docker configuration
- `07-networking.md` - Network configuration details
