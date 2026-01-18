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
# Self-contained: No GitHub downloads required
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

# Configuration
IMAGE_NAME="rjsears/pizero_generator_control:genslave"
INSTALL_DIR="/opt/genslave"

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
    cd "$INSTALL_DIR"

    log_success "Created $INSTALL_DIR"
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

    # Privileged mode required for GPIO access
    # Alternatively, use device mappings below
    privileged: true

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
      - WEBHOOK_URL=${WEBHOOK_URL:-}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET:-}

    # Persist data and logs
    volumes:
      - genslave_data:/opt/genslave/data
      - genslave_logs:/opt/genslave/logs

    # Health check
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8001/health', timeout=5)"]
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
    echo -e "${YELLOW}The API secret is required for secure communication with GenMaster.${NC}"
    echo -e "${YELLOW}You must copy this value from your GenMaster configuration.${NC}"
    echo ""
    echo -e "In GenMaster, find the value of ${CYAN}SLAVE_API_SECRET${NC} in your .env file"
    echo -e "or generate a new key in GenMaster's Settings > GenSlave Configuration."
    echo ""

    while true; do
        read -p "Enter the API secret from GenMaster: " API_SECRET_INPUT

        # Validate minimum length (16 characters)
        if [[ ${#API_SECRET_INPUT} -lt 16 ]]; then
            log_error "API secret must be at least 16 characters long"
            continue
        fi

        # Confirm the key
        echo ""
        echo -e "API Secret: ${CYAN}${API_SECRET_INPUT}${NC}"
        read -p "Is this correct? (Y/n) " -n 1 -r
        echo ""

        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            break
        fi
    done

    cat > "$INSTALL_DIR/.env" << EOF
# GenSlave Environment Configuration
# Created during setup - $(date)

# API Secret (shared with GenMaster for authentication)
# This key must match the SLAVE_API_SECRET in GenMaster
GENSLAVE_API_SECRET=${API_SECRET_INPUT}

# Failsafe timeout in seconds (relay turns off if no heartbeat received)
FAILSAFE_TIMEOUT_SECONDS=30

# Webhook URL for backup notifications (optional)
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
    echo "  curl http://localhost:8001/health"
    echo ""

    if command -v tailscale &>/dev/null; then
        TS_IP=$(tailscale ip -4 2>/dev/null || echo "not connected")
        echo -e "${CYAN}Tailscale IP:${NC} $TS_IP"
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
    create_compose_file
    create_env_file
    pull_image
    start_container
    setup_systemd
    install_tailscale

    print_success
}

# Run main
main "$@"
