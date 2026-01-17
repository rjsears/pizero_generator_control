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
# Usage: curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genslave/setup-docker.sh | bash
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

# Configuration
IMAGE_NAME="rjsears/pizero_generator_control:genslave"
INSTALL_DIR="/opt/genslave"
COMPOSE_URL="https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genslave/docker-compose.yml"

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

    PI_MODEL=$(cat /proc/device-tree/model)
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

    log_info "Installing Docker..."

    # Install Docker using convenience script
    curl -fsSL https://get.docker.com | sh

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

# Install Docker Compose plugin
install_compose() {
    if docker compose version &>/dev/null; then
        log_info "Docker Compose already installed: $(docker compose version)"
        return
    fi

    log_info "Installing Docker Compose plugin..."

    # Docker Compose is included with modern Docker installations
    # If not, install the plugin
    apt-get update
    apt-get install -y docker-compose-plugin

    log_success "Docker Compose installed"
}

# Create installation directory
setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    log_success "Created $INSTALL_DIR"
}

# Download docker-compose.yml
download_compose() {
    log_info "Downloading docker-compose.yml..."

    curl -fsSL "$COMPOSE_URL" -o "$INSTALL_DIR/docker-compose.yml"

    log_success "Downloaded docker-compose.yml"
}

# Create .env file for configuration
create_env_file() {
    if [[ -f "$INSTALL_DIR/.env" ]]; then
        log_info "Environment file already exists, keeping existing configuration"
        return
    fi

    log_info "Creating environment configuration..."

    cat > "$INSTALL_DIR/.env" << 'EOF'
# GenSlave Environment Configuration
# Edit these values as needed

# API Secret (shared with GenMaster for authentication)
GENSLAVE_API_SECRET=

# Failsafe timeout in seconds (relay turns off if no heartbeat received)
FAILSAFE_TIMEOUT_SECONDS=30

# Webhook URL for backup notifications (optional)
WEBHOOK_URL=
WEBHOOK_SECRET=

# Log level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO
EOF

    log_success "Created .env file at $INSTALL_DIR/.env"
    log_warn "Edit $INSTALL_DIR/.env to configure your settings"
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
    docker compose up -d

    # Wait for container to start
    sleep 5

    # Check if running
    if docker compose ps | grep -q "running"; then
        log_success "GenSlave container started successfully"
    else
        log_error "Container failed to start. Check logs with: docker compose logs"
        exit 1
    fi
}

# Setup systemd service for auto-start
setup_systemd() {
    log_info "Setting up systemd service for auto-start..."

    cat > /etc/systemd/system/genslave.service << EOF
[Unit]
Description=GenSlave Generator Control
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable genslave.service

    log_success "Systemd service created and enabled"
}

# Install Tailscale (optional)
install_tailscale() {
    if command -v tailscale &>/dev/null; then
        log_info "Tailscale already installed"
        return
    fi

    echo ""
    read -p "Install Tailscale for remote access? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log_info "Skipping Tailscale installation"
        return
    fi

    log_info "Installing Tailscale..."

    curl -fsSL https://tailscale.com/install.sh | sh

    log_success "Tailscale installed"
    log_info "Run 'sudo tailscale up' to connect to your Tailnet"
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
    echo "  docker compose logs -f        # View logs"
    echo "  docker compose restart        # Restart container"
    echo "  docker compose pull && docker compose up -d  # Update to latest"
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
    echo "  2. Restart: docker compose restart"
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
    download_compose
    create_env_file
    pull_image
    start_container
    setup_systemd
    install_tailscale

    print_success
}

# Run main
main "$@"
