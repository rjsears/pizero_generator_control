# Agent Handoff: Setup Scripts

## Purpose
This document provides complete specifications for the installation and setup scripts that configure GenMaster and GenSlave on fresh Raspberry Pi Zero 2W devices.

---

## Overview

The setup system consists of:
1. **Main setup script** (`setup.sh`) - Interactive installer
2. **Device-specific configuration** - GenMaster or GenSlave modes
3. **State persistence** - Resume interrupted installations
4. **Validation** - Hardware and configuration checks

---

## Setup Script Architecture

```
setup.sh
├── Phase 1: System Preparation
│   ├── Update system packages
│   ├── Install Docker
│   ├── Configure system settings
│   └── Reduce SSD writes
│
├── Phase 2: Hardware Validation
│   ├── Check GPIO access
│   ├── Test I2C/SPI (GenSlave)
│   └── Verify Automation Hat Mini (GenSlave)
│
├── Phase 3: Network Configuration
│   ├── Install/configure Tailscale
│   ├── Configure Cloudflare (optional)
│   └── Test connectivity
│
├── Phase 4: Application Deployment
│   ├── Clone/copy application code
│   ├── Configure environment
│   ├── Build containers
│   └── Run migrations
│
├── Phase 5: Service Setup
│   ├── Create systemd service
│   ├── Enable auto-start
│   └── Start services
│
└── Phase 6: Validation
    ├── Health checks
    ├── Connectivity tests
    └── Final status report
```

---

## Main Setup Script

```bash
#!/bin/bash
#
# PiZero Generator Control - Setup Script
# Usage: sudo ./setup.sh --genmaster | --genslave
#

set -e

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="/tmp/gencontrol_setup_state"
LOG_FILE="/var/log/gencontrol_setup.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Device configuration
DEVICE_TYPE=""
INSTALL_DIR=""
HOSTNAME=""

# ============================================================================
# Utility Functions
# ============================================================================

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case $level in
        INFO)  echo -e "${BLUE}[INFO]${NC} $message" ;;
        OK)    echo -e "${GREEN}[OK]${NC} $message" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $message" ;;
    esac
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${GREEN}▶ $1${NC}"
    echo ""
}

confirm_prompt() {
    local prompt=$1
    local default=${2:-y}

    if [ "$default" = "y" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi

    read -p "$prompt" response
    response=${response:-$default}

    [[ "$response" =~ ^[Yy]$ ]]
}

read_input() {
    local prompt=$1
    local default=$2
    local var_name=$3

    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        value=${value:-$default}
    else
        read -p "$prompt: " value
    fi

    eval "$var_name='$value'"
}

read_secret() {
    local prompt=$1
    local var_name=$2

    read -sp "$prompt: " value
    echo ""
    eval "$var_name='$value'"
}

save_state() {
    cat > "$STATE_FILE" << EOF
DEVICE_TYPE="$DEVICE_TYPE"
INSTALL_DIR="$INSTALL_DIR"
HOSTNAME="$HOSTNAME"
CURRENT_PHASE="$CURRENT_PHASE"
DB_PASSWORD="$DB_PASSWORD"
DB_ROOT_PASSWORD="$DB_ROOT_PASSWORD"
API_SECRET="$API_SECRET"
TAILSCALE_AUTHKEY="$TAILSCALE_AUTHKEY"
CLOUDFLARE_ENABLED="$CLOUDFLARE_ENABLED"
CLOUDFLARE_TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN"
SLAVE_IP="$SLAVE_IP"
WEBHOOK_URL="$WEBHOOK_URL"
WEBHOOK_SECRET="$WEBHOOK_SECRET"
EOF
    chmod 600 "$STATE_FILE"
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        return 0
    fi
    return 1
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log ERROR "This script must be run as root (sudo)"
        exit 1
    fi
}

check_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log WARN "This doesn't appear to be a Raspberry Pi"
        if ! confirm_prompt "Continue anyway?"; then
            exit 1
        fi
    fi
}

# ============================================================================
# Phase 1: System Preparation
# ============================================================================

phase1_system_prep() {
    print_header "Phase 1: System Preparation"

    print_section "Updating system packages"
    apt-get update
    apt-get upgrade -y
    log OK "System packages updated"

    print_section "Installing required packages"
    apt-get install -y \
        curl \
        wget \
        git \
        ca-certificates \
        gnupg \
        lsb-release \
        python3 \
        python3-pip \
        ufw
    log OK "Required packages installed"

    print_section "Installing Docker"
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | sh
        usermod -aG docker pi
        systemctl enable docker
        systemctl start docker
        log OK "Docker installed"
    else
        log OK "Docker already installed"
    fi

    # Install Docker Compose plugin
    if ! docker compose version &> /dev/null; then
        apt-get install -y docker-compose-plugin
        log OK "Docker Compose plugin installed"
    fi

    print_section "Configuring system for SSD longevity"
    configure_ssd_optimization

    print_section "Setting hostname"
    hostnamectl set-hostname "$HOSTNAME"
    echo "$HOSTNAME" > /etc/hostname
    log OK "Hostname set to $HOSTNAME"

    CURRENT_PHASE=2
    save_state
}

configure_ssd_optimization() {
    # Disable swap
    if [ -f /etc/dphys-swapfile ]; then
        systemctl disable dphys-swapfile 2>/dev/null || true
        swapoff -a 2>/dev/null || true
        log OK "Swap disabled"
    fi

    # Configure tmpfs for /tmp
    if ! grep -q "tmpfs /tmp" /etc/fstab; then
        echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0" >> /etc/fstab
        log OK "tmpfs configured for /tmp"
    fi

    # Reduce journald writes
    mkdir -p /etc/systemd/journald.conf.d/
    cat > /etc/systemd/journald.conf.d/reduce-writes.conf << EOF
[Journal]
Storage=volatile
RuntimeMaxUse=50M
EOF
    systemctl restart systemd-journald
    log OK "Journald configured for reduced writes"

    # Set noatime on root filesystem
    if ! grep -q "noatime" /etc/fstab; then
        sed -i 's/defaults/defaults,noatime/' /etc/fstab
        log OK "noatime set on root filesystem"
    fi
}

# ============================================================================
# Phase 2: Hardware Validation
# ============================================================================

phase2_hardware_validation() {
    print_header "Phase 2: Hardware Validation"

    print_section "Checking GPIO access"
    if [ -e /dev/gpiomem ]; then
        log OK "GPIO memory device available"
    else
        log WARN "GPIO memory device not found - GPIO may not work"
    fi

    if [ "$DEVICE_TYPE" = "genslave" ]; then
        print_section "Checking I2C"
        if [ -e /dev/i2c-1 ]; then
            log OK "I2C device available"
        else
            log WARN "I2C not enabled - enabling now"
            raspi-config nonint do_i2c 0
        fi

        print_section "Checking SPI"
        if [ -e /dev/spidev0.0 ]; then
            log OK "SPI device available"
        else
            log WARN "SPI not enabled - enabling now"
            raspi-config nonint do_spi 0
        fi

        print_section "Testing Automation Hat Mini"
        test_automation_hat
    fi

    if [ "$DEVICE_TYPE" = "genmaster" ]; then
        print_section "Testing GPIO17 (Victron input)"
        test_gpio17
    fi

    CURRENT_PHASE=3
    save_state
}

test_automation_hat() {
    log INFO "Testing Automation Hat Mini relay..."

    # Quick Python test
    python3 << 'EOF'
try:
    import automationhat
    import time
    time.sleep(0.1)

    # Test relay
    automationhat.relay.one.on()
    time.sleep(0.5)
    state = automationhat.relay.one.is_on()
    automationhat.relay.one.off()

    if state:
        print("RELAY_OK")
    else:
        print("RELAY_FAIL")
except Exception as e:
    print(f"RELAY_ERROR: {e}")
EOF

    log OK "Automation Hat Mini tested"
}

test_gpio17() {
    log INFO "Testing GPIO17..."

    python3 << 'EOF'
try:
    from gpiozero import Button
    btn = Button(17, pull_up=True)
    state = btn.is_pressed
    btn.close()
    print(f"GPIO17 state: {'LOW (pressed)' if state else 'HIGH (released)'}")
    print("GPIO17_OK")
except Exception as e:
    print(f"GPIO17_ERROR: {e}")
EOF

    log OK "GPIO17 tested"
}

# ============================================================================
# Phase 3: Network Configuration
# ============================================================================

phase3_network_config() {
    print_header "Phase 3: Network Configuration"

    print_section "Configuring Tailscale"
    configure_tailscale

    if [ "$DEVICE_TYPE" = "genmaster" ]; then
        print_section "Cloudflare Tunnel Configuration"
        configure_cloudflare
    fi

    print_section "Configuring firewall"
    configure_firewall

    CURRENT_PHASE=4
    save_state
}

configure_tailscale() {
    log INFO "Tailscale provides secure mesh networking"
    echo ""

    if [ -z "$TAILSCALE_AUTHKEY" ]; then
        echo "Get an auth key from: https://login.tailscale.com/admin/settings/keys"
        echo "Recommended settings: Reusable=Yes, Pre-approved=Yes"
        echo ""
        read_secret "Enter Tailscale Auth Key" TAILSCALE_AUTHKEY
    fi

    # Tailscale will be configured in Docker, just validate the key format
    if [[ ! "$TAILSCALE_AUTHKEY" =~ ^tskey-auth- ]]; then
        log WARN "Auth key doesn't match expected format (tskey-auth-...)"
        if ! confirm_prompt "Continue anyway?"; then
            read_secret "Enter Tailscale Auth Key" TAILSCALE_AUTHKEY
        fi
    fi

    log OK "Tailscale auth key configured"
}

configure_cloudflare() {
    echo "Cloudflare Tunnel provides public web access without exposing ports."
    echo "This adds ~75-100MB RAM usage."
    echo ""

    if [ -z "$CLOUDFLARE_ENABLED" ]; then
        if confirm_prompt "Enable Cloudflare Tunnel?" "n"; then
            CLOUDFLARE_ENABLED=true

            echo ""
            echo "Create a tunnel at: https://one.dash.cloudflare.com/"
            echo "Access → Tunnels → Create a tunnel"
            echo ""
            read_secret "Enter Cloudflare Tunnel Token" CLOUDFLARE_TUNNEL_TOKEN

            log OK "Cloudflare Tunnel configured"
        else
            CLOUDFLARE_ENABLED=false
            log OK "Cloudflare Tunnel skipped"
        fi
    fi
}

configure_firewall() {
    log INFO "Configuring UFW firewall"

    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH from local network
    ufw allow from 192.168.0.0/16 to any port 22

    # Allow Tailscale interface
    ufw allow in on tailscale0 2>/dev/null || true

    # Allow HTTP on local network
    ufw allow from 192.168.0.0/16 to any port 80

    ufw --force enable

    log OK "Firewall configured"
}

# ============================================================================
# Phase 4: Application Deployment
# ============================================================================

phase4_application_deploy() {
    print_header "Phase 4: Application Deployment"

    print_section "Creating installation directory"
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    print_section "Copying application files"
    # Assuming files are in the same directory as setup.sh
    if [ -d "$SCRIPT_DIR/$DEVICE_TYPE" ]; then
        cp -r "$SCRIPT_DIR/$DEVICE_TYPE/"* "$INSTALL_DIR/"
        log OK "Application files copied"
    else
        log ERROR "Application files not found at $SCRIPT_DIR/$DEVICE_TYPE"
        exit 1
    fi

    print_section "Creating environment configuration"
    create_env_file

    print_section "Building frontend (GenMaster only)"
    if [ "$DEVICE_TYPE" = "genmaster" ] && [ -d "frontend" ]; then
        build_frontend
    fi

    print_section "Building Docker containers"
    docker compose build
    log OK "Docker containers built"

    print_section "Starting database"
    docker compose up -d db
    sleep 10  # Wait for database to be ready

    print_section "Running database migrations"
    docker compose run --rm "$DEVICE_TYPE" alembic upgrade head
    log OK "Database migrations complete"

    CURRENT_PHASE=5
    save_state
}

create_env_file() {
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    fi
    if [ -z "$DB_ROOT_PASSWORD" ]; then
        DB_ROOT_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    fi
    if [ -z "$API_SECRET" ]; then
        API_SECRET=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    fi

    if [ "$DEVICE_TYPE" = "genmaster" ]; then
        # Get GenSlave configuration
        if [ -z "$SLAVE_IP" ]; then
            echo ""
            echo "Enter the GenSlave's Tailscale hostname or IP"
            read_input "GenSlave address" "genslave" SLAVE_IP
        fi

        if [ -z "$WEBHOOK_URL" ]; then
            echo ""
            echo "Enter the n8n webhook URL (or press Enter to skip)"
            read_input "Webhook URL" "" WEBHOOK_URL
        fi

        cat > "$INSTALL_DIR/.env" << EOF
# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=$(openssl rand -base64 32)

# Database
DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD
DB_PASSWORD=$DB_PASSWORD

# GenSlave Communication
SLAVE_API_URL=http://$SLAVE_IP:8000
SLAVE_API_SECRET=$API_SECRET

# Webhooks
WEBHOOK_BASE_URL=$WEBHOOK_URL
WEBHOOK_SECRET=$WEBHOOK_SECRET

# Tailscale
TAILSCALE_AUTHKEY=$TAILSCALE_AUTHKEY

# Cloudflare (optional)
CLOUDFLARE_TUNNEL_TOKEN=$CLOUDFLARE_TUNNEL_TOKEN
EOF
    else
        # GenSlave configuration
        cat > "$INSTALL_DIR/.env" << EOF
# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=$(openssl rand -base64 32)

# API Authentication
API_SECRET=$API_SECRET

# Database
DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD
DB_PASSWORD=$DB_PASSWORD

# Webhooks (failsafe only)
WEBHOOK_BASE_URL=$WEBHOOK_URL
WEBHOOK_SECRET=$WEBHOOK_SECRET

# LCD
LCD_ENABLED=true

# Tailscale
TAILSCALE_AUTHKEY=$TAILSCALE_AUTHKEY
EOF
    fi

    chmod 600 "$INSTALL_DIR/.env"
    log OK "Environment file created"

    # Save credentials
    save_credentials
}

save_credentials() {
    local creds_file="$INSTALL_DIR/CREDENTIALS.txt"
    cat > "$creds_file" << EOF
================================================================
PiZero Generator Control - Credentials
Generated: $(date)
Device: $DEVICE_TYPE ($HOSTNAME)
================================================================

Database Root Password: $DB_ROOT_PASSWORD
Database User Password: $DB_PASSWORD
API Secret: $API_SECRET

IMPORTANT: Store these credentials securely and delete this file!
================================================================
EOF
    chmod 600 "$creds_file"
    log WARN "Credentials saved to $creds_file - DELETE AFTER SAVING!"
}

build_frontend() {
    log INFO "Building Vue.js frontend..."

    # Check if Node.js is available
    if ! command -v node &> /dev/null; then
        log INFO "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt-get install -y nodejs
    fi

    cd "$INSTALL_DIR/frontend"
    npm install
    npm run build
    cd "$INSTALL_DIR"

    log OK "Frontend built"
}

# ============================================================================
# Phase 5: Service Setup
# ============================================================================

phase5_service_setup() {
    print_header "Phase 5: Service Setup"

    print_section "Creating systemd service"
    create_systemd_service

    print_section "Starting services"
    systemctl daemon-reload
    systemctl enable "$DEVICE_TYPE.service"
    systemctl start "$DEVICE_TYPE.service"

    log OK "Services started"

    CURRENT_PHASE=6
    save_state
}

create_systemd_service() {
    cat > "/etc/systemd/system/$DEVICE_TYPE.service" << EOF
[Unit]
Description=Generator Control System - $DEVICE_TYPE
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    log OK "Systemd service created"
}

# ============================================================================
# Phase 6: Validation
# ============================================================================

phase6_validation() {
    print_header "Phase 6: Validation"

    print_section "Checking container status"
    docker compose ps

    print_section "Running health checks"
    sleep 5  # Wait for services to start

    # Check API
    local api_url="http://localhost:8000/api/status"
    if [ "$DEVICE_TYPE" = "genmaster" ]; then
        api_url="http://localhost/api/status"
    fi

    if curl -sf "$api_url" > /dev/null 2>&1; then
        log OK "API responding"
    else
        log WARN "API not responding yet - may need more time"
    fi

    # Check Tailscale
    print_section "Checking Tailscale status"
    sleep 10  # Give Tailscale time to connect
    docker logs "${DEVICE_TYPE}-tailscale" 2>&1 | tail -5

    print_section "Setup Complete!"
    print_final_summary

    # Cleanup state file
    rm -f "$STATE_FILE"
}

print_final_summary() {
    local ts_ip=$(docker exec "${DEVICE_TYPE}-tailscale" tailscale ip -4 2>/dev/null || echo "pending...")

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Setup Complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "  Device:        $DEVICE_TYPE"
    echo "  Hostname:      $HOSTNAME"
    echo "  Install Dir:   $INSTALL_DIR"
    echo "  Tailscale IP:  $ts_ip"
    echo ""

    if [ "$DEVICE_TYPE" = "genmaster" ]; then
        echo "  Web Interface: http://$HOSTNAME (Tailscale)"
        echo "                 http://localhost (local)"
        if [ "$CLOUDFLARE_ENABLED" = "true" ]; then
            echo "                 https://your-domain.com (Cloudflare)"
        fi
    else
        echo "  API Endpoint:  http://$HOSTNAME:8000 (Tailscale)"
    fi

    echo ""
    echo "  Commands:"
    echo "    View logs:    docker compose logs -f"
    echo "    Restart:      sudo systemctl restart $DEVICE_TYPE"
    echo "    Stop:         sudo systemctl stop $DEVICE_TYPE"
    echo ""
    echo -e "${YELLOW}  IMPORTANT: Save the credentials from $INSTALL_DIR/CREDENTIALS.txt${NC}"
    echo -e "${YELLOW}             Then delete that file!${NC}"
    echo ""
}

# ============================================================================
# Main Entry Point
# ============================================================================

show_usage() {
    echo "PiZero Generator Control - Setup Script v$SCRIPT_VERSION"
    echo ""
    echo "Usage: sudo $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --genmaster    Install GenMaster (controller with web UI)"
    echo "  --genslave     Install GenSlave (relay controller)"
    echo "  --resume       Resume interrupted installation"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo $0 --genmaster"
    echo "  sudo $0 --genslave"
    echo ""
}

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --genmaster)
                DEVICE_TYPE="genmaster"
                INSTALL_DIR="/opt/genmaster"
                HOSTNAME="genmaster"
                shift
                ;;
            --genslave)
                DEVICE_TYPE="genslave"
                INSTALL_DIR="/opt/genslave"
                HOSTNAME="genslave"
                shift
                ;;
            --resume)
                if load_state; then
                    log INFO "Resuming installation from phase $CURRENT_PHASE"
                else
                    log ERROR "No saved state found"
                    exit 1
                fi
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log ERROR "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Validate device type
    if [ -z "$DEVICE_TYPE" ]; then
        show_usage
        exit 1
    fi

    # Initialize
    check_root
    check_pi

    # Create log file
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"

    print_header "PiZero Generator Control - $DEVICE_TYPE Setup"
    echo "Version: $SCRIPT_VERSION"
    echo "Log file: $LOG_FILE"
    echo ""

    # Run phases
    CURRENT_PHASE=${CURRENT_PHASE:-1}

    case $CURRENT_PHASE in
        1) phase1_system_prep ;&
        2) phase2_hardware_validation ;&
        3) phase3_network_config ;&
        4) phase4_application_deploy ;&
        5) phase5_service_setup ;&
        6) phase6_validation ;;
    esac
}

# Run main
main "$@"
```

---

## Additional Helper Scripts

### Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh

DEVICE=${1:-genmaster}

echo "=== $DEVICE Health Check ==="
echo ""

# Docker status
echo "Docker Containers:"
docker compose -f /opt/$DEVICE/docker-compose.yml ps
echo ""

# API health
echo "API Status:"
if [ "$DEVICE" = "genmaster" ]; then
    curl -s http://localhost/api/health | jq . 2>/dev/null || echo "API not responding"
else
    curl -s http://localhost:8000/api/health | jq . 2>/dev/null || echo "API not responding"
fi
echo ""

# Tailscale status
echo "Tailscale Status:"
docker exec ${DEVICE}-tailscale tailscale status 2>/dev/null || echo "Tailscale not running"
echo ""

# System resources
echo "System Resources:"
echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "  RAM: $(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')"
echo "  Disk: $(df -h / | awk 'NR==2{print $5}')"
echo "  Temp: $(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | awk '{printf "%.1f°C", $1/1000}')"
```

### Update Script

```bash
#!/bin/bash
# scripts/update.sh

set -e

DEVICE=${1:-genmaster}
INSTALL_DIR="/opt/$DEVICE"

echo "=== Updating $DEVICE ==="

cd "$INSTALL_DIR"

# Stop services
echo "Stopping services..."
docker compose down

# Pull latest images
echo "Pulling latest images..."
docker compose pull

# Rebuild if needed
echo "Rebuilding containers..."
docker compose build

# Run migrations
echo "Running migrations..."
docker compose run --rm $DEVICE alembic upgrade head

# Start services
echo "Starting services..."
docker compose up -d

echo "Update complete!"
docker compose ps
```

### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

set -e

DEVICE=${1:-genmaster}
INSTALL_DIR="/opt/$DEVICE"
BACKUP_DIR="$INSTALL_DIR/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "=== Backing up $DEVICE ==="

# Load environment
source "$INSTALL_DIR/.env"

# Backup database
echo "Backing up database..."
docker compose -f "$INSTALL_DIR/docker-compose.yml" exec -T db \
    mysqldump -u root -p"$DB_ROOT_PASSWORD" $DEVICE | gzip > "$BACKUP_DIR/${DEVICE}_${DATE}.sql.gz"

# Backup configuration
echo "Backing up configuration..."
cp "$INSTALL_DIR/.env" "$BACKUP_DIR/.env.${DATE}"

# Cleanup old backups (keep last 7)
echo "Cleaning old backups..."
ls -t "$BACKUP_DIR"/*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm

echo "Backup complete: $BACKUP_DIR/${DEVICE}_${DATE}.sql.gz"
```

---

## Agent Implementation Checklist

- [ ] Create main `setup.sh` script
- [ ] Implement Phase 1: System preparation
- [ ] Implement Phase 2: Hardware validation
- [ ] Implement Phase 3: Network configuration
- [ ] Implement Phase 4: Application deployment
- [ ] Implement Phase 5: Service setup
- [ ] Implement Phase 6: Validation
- [ ] Create `health-check.sh` script
- [ ] Create `update.sh` script
- [ ] Create `backup.sh` script
- [ ] Test on fresh Raspberry Pi OS
- [ ] Test resume functionality
- [ ] Test GenMaster installation
- [ ] Test GenSlave installation
- [ ] Verify all credentials are properly generated
- [ ] Test systemd service auto-start

---

## Related Documents

- `01-project-structure.md` - File structure created by setup
- `06-docker-infrastructure.md` - Docker configuration
- `07-networking.md` - Network configuration details
