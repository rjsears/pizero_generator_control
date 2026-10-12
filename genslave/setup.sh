#!/bin/bash
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# GenSlave Docker Setup Script for Pi Zero
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# This script sets up GenSlave using a pre-built Docker image
# No local compilation required - just pull and run!
#
# Self-contained: No GitHub downloads required (except the optional
# WiFi watchdog, which is fetched from GitHub when not run from a checkout)
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

# Configuration
IMAGE_NAME="rjsears/pizero_generator_control:genslave"
INSTALL_DIR="/opt/genslave"
WATCHDOG_RAW_URL="https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/scripts"
WATCHDOG_INSTALLED=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           GenSlave Docker Setup for Pi Zero               ║"
    echo "║              Pre-built Image Installation                 ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check if this is a Raspberry Pi
check_pi() {
    if [[ ! -f /proc/device-tree/model ]]; then
        log_warn "Cannot detect Raspberry Pi model"
        return
    fi

    PI_MODEL=$(tr -d '\0' < /proc/device-tree/model)
    log_info "Detected: $PI_MODEL"

    if [[ "$PI_MODEL" != *"Zero"* ]]; then
        log_warn "This script is optimized for Pi Zero. Detected: $PI_MODEL"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Install Docker if not present
install_docker() {
    if command -v docker &>/dev/null; then
        log_info "Docker already installed: $(docker --version)"
        return
    fi

    log_info "Installing Docker from Debian repos..."

    # Install Docker from Debian's official repos
    # (Docker's repos don't support trixie yet)
    apt-get update
    apt-get install -y docker.io

    # Add current user to docker group (if not root)
    if [[ -n "$SUDO_USER" ]]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Added $SUDO_USER to docker group"
    fi

    # Enable and start Docker
    systemctl enable docker
    systemctl start docker

    log_success "Docker installed successfully"
}

# Install Docker Compose
install_compose() {
    if docker-compose version &>/dev/null; then
        log_info "Docker Compose already installed: $(docker-compose version)"
        return
    fi

    log_info "Installing Docker Compose..."

    # Install docker-compose from Debian repos
    apt-get install -y docker-compose

    log_success "Docker Compose installed"
}

# Create installation directory
setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/scripts"
    cd "$INSTALL_DIR"

    log_success "Created $INSTALL_DIR"
}

# Create safe reboot script for maintenance reboots
create_safe_reboot_script() {
    log_info "Creating safe reboot script..."

    cat > "$INSTALL_DIR/scripts/safe_reboot.sh" << 'REBOOT_EOF'
#!/bin/bash
# Safe reboot script for GenSlave Pi Zero
# Only reboots if the generator is NOT running

set -e

GENSLAVE_API="http://localhost:8001/api/health"
COMPOSE_DIR="/opt/genslave"
LOG_TAG="[safe_reboot]"
MAX_RETRIES=3
RETRY_DELAY=5

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_TAG $1"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_TAG ERROR: $1" >&2
}

check_generator_status() {
    local retry=0
    while [ $retry -lt $MAX_RETRIES ]; do
        response=$(curl -s --max-time 10 "$GENSLAVE_API" 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$response" ]; then
            relay_state=$(echo "$response" | grep -o '"relay_state":[^,}]*' | cut -d':' -f2 | tr -d ' ')
            if [ "$relay_state" = "true" ]; then
                log "Generator is RUNNING - reboot NOT safe"
                return 1
            elif [ "$relay_state" = "false" ]; then
                log "Generator is STOPPED - reboot is safe"
                return 0
            fi
        fi
        retry=$((retry + 1))
        [ $retry -lt $MAX_RETRIES ] && sleep $RETRY_DELAY
    done
    log_error "Failed to get status after $MAX_RETRIES attempts - aborting"
    return 1
}

stop_genslave() {
    log "Stopping genslave container..."
    cd "$COMPOSE_DIR" && docker compose stop -t 30 genslave
}

main() {
    log "Safe reboot check initiated"
    if ! check_generator_status; then
        log "Reboot aborted - generator running or status unknown"
        exit 1
    fi
    log "Proceeding with safe reboot..."
    stop_genslave || { log_error "Failed to stop container"; exit 1; }
    sleep 2
    sync
    /sbin/reboot
}

main "$@"
REBOOT_EOF

    chmod +x "$INSTALL_DIR/scripts/safe_reboot.sh"
    log_success "Created safe_reboot.sh script"
    log_info "To enable automatic maintenance reboots, add to crontab:"
    log_info "  0 4 * * 0 $INSTALL_DIR/scripts/safe_reboot.sh >> /var/log/genslave_reboot.log 2>&1"
}

# Create docker-compose.yaml (embedded - no download needed)
create_compose_file() {
    log_info "Creating docker-compose.yaml..."

    cat > "$INSTALL_DIR/docker-compose.yaml" << 'COMPOSE_EOF'
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# GenSlave Docker Compose
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Run on Pi Zero: docker-compose up -d
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

services:
  genslave:
    image: rjsears/pizero_generator_control:genslave
    container_name: genslave
    restart: unless-stopped
    env_file: .env

    # Privileged mode required for GPIO access
    # pid: host required for scheduled reboot (nsenter to host namespace)
    privileged: true
    pid: host

    # Device mappings for GPIO (alternative to privileged)
    # devices:
    #   - /dev/gpiomem:/dev/gpiomem
    #   - /dev/mem:/dev/mem
    #   - /dev/i2c-1:/dev/i2c-1

    # Use host network for easy access and Tailscale compatibility
    network_mode: host

    # Environment variables
    environment:
      - HOST=0.0.0.0
      - PORT=8001
      - LOG_LEVEL=INFO
      - FAILSAFE_TIMEOUT_SECONDS=30
      - MOCK_HAT_MODE=false
      - GENSLAVE_API_SECRET=${GENSLAVE_API_SECRET:-}
      - APPRISE_URLS=${APPRISE_URLS:-}
      - WEBHOOK_URL=${WEBHOOK_URL:-}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET:-}

    # Persist data and logs
    # Mount D-Bus socket for nmcli to communicate with host NetworkManager
    volumes:
      - genslave_data:/opt/genslave/data
      - genslave_logs:/opt/genslave/logs
      - /var/run/dbus:/var/run/dbus:rw

    # Health check
    healthcheck:
      test: ["CMD", "python3", "-c", "import httpx; httpx.get('http://localhost:8001/api/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  genslave_data:
  genslave_logs:
COMPOSE_EOF

    log_success "Created docker-compose.yaml"
}

# Create .env file for configuration
create_env_file() {
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        log_info "Environment file already exists, keeping existing configuration"
        return
    fi

    log_info "Creating environment configuration..."

    # Prompt for API secret (required)
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║              API Secret Configuration                     ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}GenSlave's API requires authentication. There is no unauthenticated mode.${NC}"
    echo ""
    echo -e "You can either:"
    echo -e "  ${CYAN}[A]${NC} Auto-generate a new secret here (recommended for fresh setups)"
    echo -e "  ${CYAN}[B]${NC} Paste an existing secret from GenMaster's ${CYAN}SLAVE_API_SECRET${NC}"
    echo ""

    while true; do
        read -p "Press Enter to auto-generate, or paste an existing secret: " API_SECRET_INPUT

        if [[ -z "$API_SECRET_INPUT" ]]; then
            # Auto-generate a 64-char hex secret (32 bytes of entropy)
            API_SECRET_INPUT=$(openssl rand -hex 32)
            echo ""
            echo -e "${GREEN}✓ Generated new API secret:${NC}"
            echo -e "  ${CYAN}${API_SECRET_INPUT}${NC}"
            echo ""
            echo -e "${YELLOW}IMPORTANT:${NC} Copy this value into GenMaster's ${CYAN}SLAVE_API_SECRET${NC}"
            echo -e "in its ${CYAN}.env${NC} file (or set it via GenMaster's Settings > GenSlave"
            echo -e "Configuration UI). GenMaster and GenSlave must share the same secret."
            echo ""
            read -p "Press Enter once you've recorded the secret to continue..."
            break
        fi

        # Validate minimum length (16 characters) for pasted secrets
        if [[ ${#API_SECRET_INPUT} -lt 16 ]]; then
            log_error "API secret must be at least 16 characters long"
            continue
        fi

        # Confirm the pasted key
        echo ""
        echo -e "API Secret: ${CYAN}${API_SECRET_INPUT}${NC}"
        read -p "Is this correct? (Y/n) " -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            break
        fi
    done

    # Optional: Configure notifications
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           Notification Configuration (Optional)           ║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}GenSlave can send notifications when failsafe triggers.${NC}"
    echo -e "${YELLOW}Supports 80+ services via Apprise (Telegram, Slack, SMS, etc.)${NC}"
    echo ""
    echo -e "Common URL formats:"
    echo -e "  ${CYAN}tgram://bottoken/chatid${NC}          - Telegram"
    echo -e "  ${CYAN}slack://token/channel${NC}            - Slack"
    echo -e "  ${CYAN}discord://webhook_id/token${NC}       - Discord"
    echo -e "  ${CYAN}twilio://sid:token@from/to${NC}       - Twilio SMS"
    echo -e "  ${CYAN}pover://user@token${NC}               - Pushover"
    echo ""
    echo -e "Full list: ${CYAN}https://github.com/caronc/apprise/wiki${NC}"
    echo ""

    APPRISE_URLS_INPUT=""
    read -p "Configure notifications now? (y/N) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "Enter Apprise URL(s), comma-separated for multiple:"
        read -p "> " APPRISE_URLS_INPUT

        if [[ -n "$APPRISE_URLS_INPUT" ]]; then
            log_success "Notification URL(s) configured"
        fi
    else
        log_info "Skipping notification setup - can be configured later via GenMaster UI"
    fi

    cat > "$INSTALL_DIR/.env" << EOF
# GenSlave Environment Configuration
# Created during setup - $(date)

# API Secret (shared with GenMaster for authentication)
# This key must match the SLAVE_API_SECRET in GenMaster
GENSLAVE_API_SECRET=${API_SECRET_INPUT}

# Failsafe timeout in seconds (relay turns off if no heartbeat received)
FAILSAFE_TIMEOUT_SECONDS=30

# Apprise notification URLs (comma-separated)
# Supports 80+ services: https://github.com/caronc/apprise/wiki
# Can also be configured via GenMaster UI
APPRISE_URLS=${APPRISE_URLS_INPUT}

# Legacy webhook (replaced by Apprise)
WEBHOOK_URL=
WEBHOOK_SECRET=

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
EOF

    log_success "Created .env file at $INSTALL_DIR/.env"
    log_success "API secret configured successfully"
}

# Pull the Docker image
pull_image() {
    log_info "Pulling GenSlave Docker image..."
    log_info "Image: $IMAGE_NAME"

    docker pull "$IMAGE_NAME"

    log_success "Image pulled successfully"
}

# Start the container
start_container() {
    log_info "Starting GenSlave container..."

    cd "$INSTALL_DIR"
    docker-compose up -d

    # Wait for container to start
    sleep 5

    # Check if running (works with various docker-compose versions)
    if docker ps --filter "name=genslave" --format "{{.Status}}" | grep -qi "up"; then
        log_success "GenSlave container started successfully"
    else
        log_warn "Container may still be starting. Check status with: docker ps"
        log_info "View logs with: docker-compose logs -f"
    fi
}

# Setup systemd service for auto-start
setup_systemd() {
    log_info "Setting up systemd service for auto-start..."

    # Find docker-compose path
    COMPOSE_PATH=$(which docker-compose)

    cat > /etc/systemd/system/genslave.service << EOF
[Unit]
Description=GenSlave Generator Control
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=$COMPOSE_PATH up -d
ExecStop=$COMPOSE_PATH down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable genslave.service

    log_success "Systemd service created and enabled"
}

# Detect the WiFi interface (same method as the GenMaster installer)
detect_wifi_interface() {
    local wifi_iface=""
    if command -v iw &>/dev/null; then
        wifi_iface=$(iw dev 2>/dev/null | grep Interface | awk '{print $2}' | head -1)
    fi
    if [ -z "$wifi_iface" ]; then
        for i in /sys/class/net/*/wireless; do
            if [ -d "$i" ]; then
                wifi_iface=$(basename "$(dirname "$i")")
                break
            fi
        done
    fi
    echo "$wifi_iface"
}

# Install WiFi watchdog (optional, recommended)
install_wifi_watchdog() {
    echo ""

    read -p "Install WiFi watchdog (auto-recovers WiFi after an outage)? [Y/n] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Skipping WiFi watchdog installation"
        return 0
    fi

    log_info "Installing WiFi watchdog..."

    local wifi_iface
    wifi_iface=$(detect_wifi_interface)
    if [ -z "$wifi_iface" ]; then
        log_warn "No WiFi interface detected - WiFi watchdog may not function"
    else
        log_info "Detected WiFi interface: $wifi_iface"
    fi

    # Use the files from a repository checkout if present, otherwise download
    local src_dir
    src_dir="$(dirname "$0")/../scripts"
    local tmp_dir=""
    local watchdog_script
    local watchdog_service

    if [ -f "$src_dir/wifi-watchdog.sh" ] && [ -f "$src_dir/wifi-watchdog.service" ]; then
        log_info "Using WiFi watchdog files from $src_dir"
        watchdog_script="$src_dir/wifi-watchdog.sh"
        watchdog_service="$src_dir/wifi-watchdog.service"
    else
        tmp_dir=$(mktemp -d)
        log_info "Downloading WiFi watchdog files..."
        if ! curl -fsSL "$WATCHDOG_RAW_URL/wifi-watchdog.sh" -o "$tmp_dir/wifi-watchdog.sh" || \
           ! curl -fsSL "$WATCHDOG_RAW_URL/wifi-watchdog.service" -o "$tmp_dir/wifi-watchdog.service"; then
            log_warn "Failed to download WiFi watchdog files - skipping"
            log_warn "WiFi will NOT auto-recover after an access point outage"
            rm -rf "$tmp_dir"
            return 0
        fi
        watchdog_script="$tmp_dir/wifi-watchdog.sh"
        watchdog_service="$tmp_dir/wifi-watchdog.service"
    fi

    # Install script and unit
    cp "$watchdog_script" /usr/local/bin/wifi-watchdog.sh
    chmod +x /usr/local/bin/wifi-watchdog.sh
    log_success "Installed /usr/local/bin/wifi-watchdog.sh"

    cp "$watchdog_service" /etc/systemd/system/wifi-watchdog.service
    log_success "Installed /etc/systemd/system/wifi-watchdog.service"

    if [ -n "$tmp_dir" ]; then
        rm -rf "$tmp_dir"
    fi

    # GenSlave-specific drop-in: never reboot while the generator relay is energized
    mkdir -p /etc/systemd/system/wifi-watchdog.service.d
    cat > /etc/systemd/system/wifi-watchdog.service.d/genslave.conf << 'EOF'
[Service]
Environment="WATCHDOG_REBOOT_GUARD_URL=http://localhost:8001/api/health"
EOF
    log_success "Installed reboot guard drop-in (refuses reboot while generator relay is energized)"

    systemctl daemon-reload
    systemctl enable --now wifi-watchdog || true

    # Verify it's running
    if systemctl is-active --quiet wifi-watchdog; then
        log_success "WiFi Watchdog is running"
        WATCHDOG_INSTALLED=true
    else
        log_warn "WiFi Watchdog service may not have started properly"
        log_info "Check status with: systemctl status wifi-watchdog"
    fi

    return 0
}

# Disable WiFi power save (prevents dropped/unrecovered connections on Pi Zero)
disable_wifi_powersave() {
    echo ""

    if [ ! -d /etc/NetworkManager ]; then
        log_warn "NetworkManager not found - skipping WiFi power save configuration"
        return 0
    fi

    log_info "Disabling WiFi power save..."

    mkdir -p /etc/NetworkManager/conf.d
    cat > /etc/NetworkManager/conf.d/wifi-powersave-off.conf << 'EOF'
[connection]
wifi.powersave = 2
EOF
    nmcli general reload 2>/dev/null || true
    log_success "Created /etc/NetworkManager/conf.d/wifi-powersave-off.conf"

    # Apply immediately without re-activating the connection (that would drop SSH)
    local wifi_iface
    wifi_iface=$(detect_wifi_interface)
    if [ -n "$wifi_iface" ] && command -v iw &>/dev/null; then
        iw dev "$wifi_iface" set power_save off 2>/dev/null || true
        log_info "Power save turned off on $wifi_iface for the current connection"
    fi

    log_info "The NetworkManager setting takes full effect on the next connection activation (e.g. reboot)"
}

# Install and configure Tailscale (optional)
install_tailscale() {
    echo ""

    # Check if already installed and connected
    if command -v tailscale &>/dev/null; then
        # Ensure tailscaled service is enabled and running
        systemctl enable tailscaled 2>/dev/null || true
        systemctl start tailscaled 2>/dev/null || true

        if tailscale status &>/dev/null; then
            log_info "Tailscale already installed and connected"
            TS_IP=$(tailscale ip -4 2>/dev/null || echo "unknown")
            log_info "Tailscale IP: $TS_IP"
            return
        else
            log_info "Tailscale installed but not connected"
        fi
    else
        # Not installed - ask if they want it
        read -p "Install Tailscale for remote access? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Skipping Tailscale installation"
            return
        fi

        log_info "Installing Tailscale..."
        curl -fsSL https://tailscale.com/install.sh | sh

        # Enable and start the tailscaled service
        systemctl enable tailscaled
        systemctl start tailscaled

        log_success "Tailscale installed and service enabled"
    fi

    # Ask for auth key to configure
    echo ""
    log_info "To connect Tailscale, you need an auth key from:"
    log_info "  https://login.tailscale.com/admin/settings/keys"
    echo ""
    read -p "Enter Tailscale auth key (or press Enter to skip): " TS_AUTHKEY

    if [[ -n "$TS_AUTHKEY" ]]; then
        log_info "Connecting to Tailscale..."
        tailscale up --authkey="$TS_AUTHKEY"

        # Wait a moment for connection
        sleep 3

        if tailscale status &>/dev/null; then
            TS_IP=$(tailscale ip -4 2>/dev/null || echo "unknown")
            log_success "Tailscale connected! IP: $TS_IP"
        else
            log_warn "Tailscale may still be connecting. Check with: tailscale status"
        fi
    else
        log_info "Skipping Tailscale configuration"
        log_info "Run 'sudo tailscale up' later to connect"
    fi
}

# Print final instructions
print_success() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              GenSlave Installation Complete!              ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Installation Directory:${NC} $INSTALL_DIR"
    echo ""
    echo -e "${CYAN}Useful Commands:${NC}"
    echo "  cd $INSTALL_DIR"
    echo "  docker-compose logs -f        # View logs"
    echo "  docker-compose restart        # Restart container"
    echo "  docker-compose pull && docker-compose up -d  # Update to latest"
    echo ""
    echo -e "${CYAN}API Endpoint:${NC}"
    echo "  http://$(hostname -I | awk '{print $1}'):8001"
    echo "  http://$(hostname).local:8001"
    echo ""
    echo -e "${CYAN}Health Check:${NC}"
    echo "  curl http://localhost:8001/api/health"
    echo ""

    if command -v tailscale &>/dev/null; then
        TS_IP=$(tailscale ip -4 2>/dev/null || echo "not connected")
        echo -e "${CYAN}Tailscale IP:${NC} $TS_IP"
        echo ""
    fi

    if [ "$WATCHDOG_INSTALLED" = true ]; then
        echo -e "${CYAN}WiFi Watchdog:${NC} running"
        echo "  journalctl -u wifi-watchdog -f   # View watchdog log"
        echo ""
    fi

    echo -e "${YELLOW}Next Steps:${NC}"
    echo "  1. Edit $INSTALL_DIR/.env to set GENSLAVE_API_SECRET"
    echo "  2. Restart: docker-compose restart"
    echo "  3. Configure GenMaster to connect to this GenSlave"
    echo ""
}

# Main installation flow
main() {
    print_banner
    check_root
    check_pi

    log_info "Starting GenSlave Docker installation..."
    echo ""

    install_docker
    install_compose
    setup_directories
    create_safe_reboot_script
    create_compose_file
    create_env_file
    pull_image
    start_container
    setup_systemd
    install_wifi_watchdog
    disable_wifi_powersave
    install_tailscale

    print_success
}

# Run main
main "$@"
