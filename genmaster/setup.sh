#!/bin/bash
#
# GenMaster Setup Script
# Generator Control System - Master Controller Installation
#
# This script provides a complete guided installation for GenMaster including:
# - System preparation and dependency installation
# - Docker and Docker Compose setup
# - PostgreSQL database configuration
# - SSL certificate acquisition (Let's Encrypt via DNS-01)
# - Tailscale VPN configuration
# - Cloudflare Tunnel setup (optional)
# - Environment configuration
#
# Usage:
#   Interactive:  ./setup.sh
#   Preconfig:    ./setup.sh --preconfig /path/to/preconfig.conf
#   Unattended:   ./setup.sh --unattended
#
# Author: rjsears
# License: MIT

set -o pipefail

# =============================================================================
# Script Configuration
# =============================================================================
SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="GenMaster Setup"
INSTALL_DIR="/opt/genmaster"
CONFIG_FILE="${INSTALL_DIR}/.env"
STATE_FILE="${INSTALL_DIR}/.setup_state"
LOG_FILE="/var/log/genmaster-setup.log"

# Docker image
DOCKER_IMAGE="rjsears/genmaster"
DOCKER_TAG="latest"

# Required disk space (in MB)
REQUIRED_DISK_SPACE=2000

# =============================================================================
# Color Definitions
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# =============================================================================
# Global Variables
# =============================================================================
PRECONFIG_FILE=""
UNATTENDED_MODE=false
DEBUG_MODE=false
SKIP_CONFIRMATION=false

# Installation state
STATE_SYSTEM_PREPARED=false
STATE_DOCKER_INSTALLED=false
STATE_SSL_CONFIGURED=false
STATE_TAILSCALE_CONFIGURED=false
STATE_CLOUDFLARE_CONFIGURED=false
STATE_ENV_CONFIGURED=false
STATE_SERVICES_STARTED=false

# Configuration values (populated during setup)
DOMAIN_NAME=""
EMAIL_ADDRESS=""
SSL_PROVIDER=""  # cloudflare, route53, manual, none
CLOUDFLARE_API_TOKEN=""
AWS_ACCESS_KEY=""
AWS_SECRET_KEY=""
ENABLE_TAILSCALE=false
TAILSCALE_AUTHKEY=""
TAILSCALE_HOSTNAME="genmaster"
ENABLE_CLOUDFLARE_TUNNEL=false
CLOUDFLARE_TUNNEL_TOKEN=""
DB_PASSWORD=""
APP_SECRET_KEY=""
SLAVE_API_SECRET=""
SLAVE_API_URL=""

# =============================================================================
# Utility Functions
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" >> "$LOG_FILE"
}

log_info() {
    log "INFO" "$*"
}

log_warn() {
    log "WARN" "$*"
}

log_error() {
    log "ERROR" "$*"
}

log_debug() {
    if [ "$DEBUG_MODE" = true ]; then
        log "DEBUG" "$*"
    fi
}

print_header() {
    clear
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                    ║"
    echo "║   ██████╗ ███████╗███╗   ██╗███╗   ███╗ █████╗ ███████╗████████╗  ║"
    echo "║  ██╔════╝ ██╔════╝████╗  ██║████╗ ████║██╔══██╗██╔════╝╚══██╔══╝  ║"
    echo "║  ██║  ███╗█████╗  ██╔██╗ ██║██╔████╔██║███████║███████╗   ██║     ║"
    echo "║  ██║   ██║██╔══╝  ██║╚██╗██║██║╚██╔╝██║██╔══██║╚════██║   ██║     ║"
    echo "║  ╚██████╔╝███████╗██║ ╚████║██║ ╚═╝ ██║██║  ██║███████║   ██║     ║"
    echo "║   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝     ║"
    echo "║                                                                    ║"
    echo "║              Generator Control System - Master Setup               ║"
    echo "║                        Version ${SCRIPT_VERSION}                            ║"
    echo "║                                                                    ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

print_section() {
    local title="$1"
    echo ""
    echo -e "${BLUE}┌──────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│${NC} ${BOLD}${title}${NC}"
    echo -e "${BLUE}└──────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

print_step() {
    local step_num="$1"
    local step_desc="$2"
    echo -e "  ${CYAN}[${step_num}]${NC} ${step_desc}"
}

print_success() {
    echo -e "  ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "  ${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "  ${RED}✗${NC} $1"
}

print_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

# Prompt for yes/no
confirm() {
    local prompt="$1"
    local default="${2:-n}"

    if [ "$UNATTENDED_MODE" = true ] || [ "$SKIP_CONFIRMATION" = true ]; then
        [ "$default" = "y" ] && return 0 || return 1
    fi

    local yn_prompt
    if [ "$default" = "y" ]; then
        yn_prompt="[Y/n]"
    else
        yn_prompt="[y/N]"
    fi

    while true; do
        echo -en "  ${MAGENTA}?${NC} ${prompt} ${yn_prompt}: "
        read -r response
        response=${response:-$default}
        case "${response,,}" in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            *) echo -e "  ${RED}Please answer yes or no.${NC}" ;;
        esac
    done
}

# Prompt for input
prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local validation="$4"

    while true; do
        local display_default=""
        if [ -n "$default" ]; then
            display_default=" [${default}]"
        fi

        echo -en "  ${MAGENTA}?${NC} ${prompt}${display_default}: "
        read -r input
        input=${input:-$default}

        # Validate if function provided
        if [ -n "$validation" ] && ! $validation "$input"; then
            continue
        fi

        eval "$var_name=\"$input\""
        return 0
    done
}

# Prompt for password/secret (masked input)
prompt_secret() {
    local prompt="$1"
    local var_name="$2"
    local allow_empty="${3:-false}"

    while true; do
        echo -en "  ${MAGENTA}?${NC} ${prompt}: "
        read -rs input
        echo ""

        if [ -z "$input" ] && [ "$allow_empty" = "false" ]; then
            print_error "This field cannot be empty"
            continue
        fi

        # Confirm password
        if [ -n "$input" ]; then
            echo -en "  ${MAGENTA}?${NC} Confirm: "
            read -rs confirm_input
            echo ""

            if [ "$input" != "$confirm_input" ]; then
                print_error "Values do not match. Please try again."
                continue
            fi
        fi

        eval "$var_name=\"$input\""
        return 0
    done
}

# Prompt for selection from options
prompt_select() {
    local prompt="$1"
    local var_name="$2"
    shift 2
    local options=("$@")

    echo -e "  ${MAGENTA}?${NC} ${prompt}"
    local i=1
    for option in "${options[@]}"; do
        echo -e "     ${CYAN}${i})${NC} ${option}"
        ((i++))
    done

    while true; do
        echo -en "  ${MAGENTA}?${NC} Selection [1-${#options[@]}]: "
        read -r selection

        if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#options[@]}" ]; then
            eval "$var_name=\"${options[$((selection-1))]}\""
            return 0
        fi
        print_error "Invalid selection. Please enter a number between 1 and ${#options[@]}"
    done
}

# Generate random secret
generate_secret() {
    local length="${1:-32}"
    openssl rand -hex "$length"
}

# Check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        echo -e "  ${YELLOW}Please run: sudo $0${NC}"
        exit 1
    fi
}

# Check minimum disk space
check_disk_space() {
    local available=$(df -m "$INSTALL_DIR" 2>/dev/null | tail -1 | awk '{print $4}')
    if [ -z "$available" ]; then
        available=$(df -m / | tail -1 | awk '{print $4}')
    fi

    if [ "$available" -lt "$REQUIRED_DISK_SPACE" ]; then
        print_error "Insufficient disk space. Required: ${REQUIRED_DISK_SPACE}MB, Available: ${available}MB"
        return 1
    fi
    return 0
}

# Check internet connectivity
check_internet() {
    if ping -c 1 -W 5 8.8.8.8 &> /dev/null || ping -c 1 -W 5 1.1.1.1 &> /dev/null; then
        return 0
    fi
    return 1
}

# =============================================================================
# State Management
# =============================================================================

save_state() {
    cat > "$STATE_FILE" << EOF
# GenMaster Setup State - DO NOT EDIT MANUALLY
# Generated: $(date)
STATE_SYSTEM_PREPARED=${STATE_SYSTEM_PREPARED}
STATE_DOCKER_INSTALLED=${STATE_DOCKER_INSTALLED}
STATE_SSL_CONFIGURED=${STATE_SSL_CONFIGURED}
STATE_TAILSCALE_CONFIGURED=${STATE_TAILSCALE_CONFIGURED}
STATE_CLOUDFLARE_CONFIGURED=${STATE_CLOUDFLARE_CONFIGURED}
STATE_ENV_CONFIGURED=${STATE_ENV_CONFIGURED}
STATE_SERVICES_STARTED=${STATE_SERVICES_STARTED}
DOMAIN_NAME="${DOMAIN_NAME}"
EMAIL_ADDRESS="${EMAIL_ADDRESS}"
SSL_PROVIDER="${SSL_PROVIDER}"
ENABLE_TAILSCALE=${ENABLE_TAILSCALE}
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME}"
ENABLE_CLOUDFLARE_TUNNEL=${ENABLE_CLOUDFLARE_TUNNEL}
SLAVE_API_URL="${SLAVE_API_URL}"
EOF
    chmod 600 "$STATE_FILE"
    log_info "State saved to $STATE_FILE"
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        log_info "State loaded from $STATE_FILE"
        return 0
    fi
    return 1
}

# =============================================================================
# Preconfig Mode
# =============================================================================

load_preconfig() {
    local preconfig_file="$1"

    if [ ! -f "$preconfig_file" ]; then
        print_error "Preconfig file not found: $preconfig_file"
        exit 1
    fi

    source "$preconfig_file"
    SKIP_CONFIRMATION=true
    log_info "Loaded preconfig from $preconfig_file"
}

create_preconfig_template() {
    local template_file="${1:-genmaster-preconfig.conf.template}"

    cat > "$template_file" << 'EOF'
# GenMaster Preconfig Template
# Fill in the values and use with: ./setup.sh --preconfig /path/to/this/file
#
# Required values are marked with [REQUIRED]

# =============================================================================
# Domain and Email [REQUIRED]
# =============================================================================
DOMAIN_NAME="genmaster.example.com"
EMAIL_ADDRESS="admin@example.com"

# =============================================================================
# SSL Configuration [REQUIRED]
# Options: cloudflare, route53, manual, none
# =============================================================================
SSL_PROVIDER="cloudflare"

# For Cloudflare DNS-01 (if SSL_PROVIDER=cloudflare)
CLOUDFLARE_API_TOKEN=""

# For Route53 DNS-01 (if SSL_PROVIDER=route53)
AWS_ACCESS_KEY=""
AWS_SECRET_KEY=""

# =============================================================================
# GenSlave Configuration [REQUIRED]
# =============================================================================
SLAVE_API_URL="http://genslave:8000"
# Generate with: openssl rand -hex 32
SLAVE_API_SECRET=""

# =============================================================================
# Database Password [REQUIRED]
# Generate with: openssl rand -hex 32
# =============================================================================
DB_PASSWORD=""

# =============================================================================
# Application Secret [REQUIRED]
# Generate with: openssl rand -hex 32
# =============================================================================
APP_SECRET_KEY=""

# =============================================================================
# Tailscale VPN (Optional)
# =============================================================================
ENABLE_TAILSCALE=true
# Get from: https://login.tailscale.com/admin/settings/keys
TAILSCALE_AUTHKEY=""
TAILSCALE_HOSTNAME="genmaster"

# =============================================================================
# Cloudflare Tunnel (Optional)
# =============================================================================
ENABLE_CLOUDFLARE_TUNNEL=false
# Get from: https://one.dash.cloudflare.com/ -> Access -> Tunnels
CLOUDFLARE_TUNNEL_TOKEN=""

# =============================================================================
# Webhooks (Optional)
# =============================================================================
WEBHOOK_BASE_URL=""
WEBHOOK_SECRET=""
EOF

    echo "Preconfig template created: $template_file"
}

# =============================================================================
# System Preparation
# =============================================================================

prepare_system() {
    print_section "System Preparation"

    # Check OS
    print_step "1" "Checking operating system..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        print_success "Detected: $PRETTY_NAME"
    else
        print_warning "Could not detect OS version"
    fi

    # Check architecture
    print_step "2" "Checking system architecture..."
    local arch=$(uname -m)
    case "$arch" in
        x86_64)
            print_success "Architecture: x86_64 (amd64)"
            ;;
        aarch64|arm64)
            print_success "Architecture: ARM64"
            ;;
        *)
            print_error "Unsupported architecture: $arch"
            exit 1
            ;;
    esac

    # Check disk space
    print_step "3" "Checking disk space..."
    if check_disk_space; then
        local available=$(df -m "$INSTALL_DIR" 2>/dev/null | tail -1 | awk '{print $4}')
        [ -z "$available" ] && available=$(df -m / | tail -1 | awk '{print $4}')
        print_success "Available disk space: ${available}MB"
    else
        exit 1
    fi

    # Check internet
    print_step "4" "Checking internet connectivity..."
    if check_internet; then
        print_success "Internet connection available"
    else
        print_error "No internet connection"
        exit 1
    fi

    # Update package lists
    print_step "5" "Updating package lists..."
    apt-get update -qq
    print_success "Package lists updated"

    # Install required packages
    print_step "6" "Installing required packages..."
    local packages=(
        curl
        wget
        gnupg
        ca-certificates
        lsb-release
        software-properties-common
        apt-transport-https
        jq
        openssl
    )

    apt-get install -y -qq "${packages[@]}" > /dev/null 2>&1
    print_success "Required packages installed"

    # Check for Raspberry Pi 5 and install GPIO software
    print_step "7" "Checking for Raspberry Pi hardware..."
    if [ -f /proc/device-tree/model ]; then
        local pi_model=$(cat /proc/device-tree/model | tr -d '\0')
        print_success "Detected: $pi_model"

        if echo "$pi_model" | grep -q "Raspberry Pi 5"; then
            print_step "8" "Installing Raspberry Pi 5 GPIO software..."

            # Pi 5 uses libgpiod instead of RPi.GPIO
            apt-get install -y -qq \
                python3-libgpiod \
                libgpiod2 \
                libgpiod-dev \
                gpiod \
                python3-lgpio \
                > /dev/null 2>&1

            # Enable GPIO access for Docker containers
            if ! grep -q "^dtoverlay=gpio-shutdown" /boot/firmware/config.txt 2>/dev/null; then
                print_info "Configuring GPIO device tree overlays..."
            fi

            # Ensure /dev/gpiochip devices are accessible
            if [ ! -e /dev/gpiochip0 ]; then
                print_warning "GPIO chip device not found - may require reboot"
            else
                print_success "GPIO chip device available"
            fi

            # Add user to gpio group if needed
            if getent group gpio > /dev/null 2>&1; then
                usermod -aG gpio root 2>/dev/null || true
            fi

            print_success "Raspberry Pi 5 GPIO software installed"

        elif echo "$pi_model" | grep -q "Raspberry Pi"; then
            print_step "8" "Installing standard Raspberry Pi GPIO software..."

            # Older Pi models use RPi.GPIO
            apt-get install -y -qq \
                python3-rpi.gpio \
                python3-gpiozero \
                > /dev/null 2>&1

            print_success "Raspberry Pi GPIO software installed"
        fi
    else
        print_info "Not running on Raspberry Pi hardware"
    fi

    # Create installation directory
    print_step "9" "Creating installation directory..."
    mkdir -p "$INSTALL_DIR"/{nginx/conf.d,nginx/ssl,logs,data,backups}
    print_success "Created $INSTALL_DIR"

    STATE_SYSTEM_PREPARED=true
    save_state
    print_success "System preparation complete"
}

# =============================================================================
# Docker Installation
# =============================================================================

install_docker() {
    print_section "Docker Installation"

    # Check if Docker is already installed
    if command_exists docker; then
        local docker_version=$(docker --version | cut -d' ' -f3 | tr -d ',')
        print_info "Docker is already installed (version $docker_version)"

        if confirm "Would you like to reinstall Docker?"; then
            print_step "1" "Removing existing Docker installation..."
            apt-get remove -y docker docker-engine docker.io containerd runc > /dev/null 2>&1
        else
            # Just ensure Docker is running
            systemctl start docker
            systemctl enable docker
            STATE_DOCKER_INSTALLED=true
            save_state
            return 0
        fi
    fi

    # Install Docker
    print_step "1" "Adding Docker repository..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    print_success "Docker repository added"

    print_step "2" "Installing Docker Engine..."
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1
    print_success "Docker Engine installed"

    print_step "3" "Starting Docker service..."
    systemctl start docker
    systemctl enable docker
    print_success "Docker service started"

    print_step "4" "Verifying Docker installation..."
    if docker run --rm hello-world &> /dev/null; then
        print_success "Docker is working correctly"
    else
        print_error "Docker verification failed"
        exit 1
    fi

    STATE_DOCKER_INSTALLED=true
    save_state
    print_success "Docker installation complete"
}

# =============================================================================
# SSL Certificate Configuration
# =============================================================================

configure_ssl() {
    print_section "SSL Certificate Configuration"

    echo "  SSL certificates provide secure HTTPS connections to GenMaster."
    echo "  You can obtain certificates automatically via Let's Encrypt"
    echo "  using DNS-01 challenge (requires DNS API access)."
    echo ""

    # Select SSL provider
    prompt_select "Select SSL certificate method:" SSL_PROVIDER \
        "Cloudflare DNS-01 (Recommended)" \
        "AWS Route53 DNS-01" \
        "Manual (bring your own certificates)" \
        "None (HTTP only - not recommended)"

    case "$SSL_PROVIDER" in
        "Cloudflare DNS-01 (Recommended)")
            SSL_PROVIDER="cloudflare"
            configure_ssl_cloudflare
            ;;
        "AWS Route53 DNS-01")
            SSL_PROVIDER="route53"
            configure_ssl_route53
            ;;
        "Manual (bring your own certificates)")
            SSL_PROVIDER="manual"
            configure_ssl_manual
            ;;
        "None (HTTP only - not recommended)")
            SSL_PROVIDER="none"
            print_warning "Running without SSL is not recommended for production"
            ;;
    esac

    STATE_SSL_CONFIGURED=true
    save_state
}

configure_ssl_cloudflare() {
    print_step "1" "Configuring Cloudflare DNS-01..."

    echo ""
    echo "  To use Cloudflare DNS-01, you need an API token with the following permissions:"
    echo "  - Zone:DNS:Edit"
    echo "  - Zone:Zone:Read"
    echo ""
    echo "  Create token at: https://dash.cloudflare.com/profile/api-tokens"
    echo ""

    prompt_input "Enter your domain name" "" DOMAIN_NAME
    prompt_input "Enter your email address" "" EMAIL_ADDRESS
    prompt_secret "Enter Cloudflare API Token" CLOUDFLARE_API_TOKEN

    print_step "2" "Installing certbot with Cloudflare plugin..."
    apt-get install -y -qq certbot python3-certbot-dns-cloudflare > /dev/null 2>&1
    print_success "Certbot installed"

    print_step "3" "Creating Cloudflare credentials file..."
    mkdir -p /root/.secrets
    cat > /root/.secrets/cloudflare.ini << EOF
dns_cloudflare_api_token = ${CLOUDFLARE_API_TOKEN}
EOF
    chmod 600 /root/.secrets/cloudflare.ini
    print_success "Credentials file created"

    print_step "4" "Obtaining SSL certificate..."
    if certbot certonly \
        --dns-cloudflare \
        --dns-cloudflare-credentials /root/.secrets/cloudflare.ini \
        --dns-cloudflare-propagation-seconds 60 \
        -d "$DOMAIN_NAME" \
        --email "$EMAIL_ADDRESS" \
        --agree-tos \
        --non-interactive; then
        print_success "SSL certificate obtained"

        # Copy certificates to nginx ssl directory
        cp /etc/letsencrypt/live/"$DOMAIN_NAME"/fullchain.pem "$INSTALL_DIR/nginx/ssl/"
        cp /etc/letsencrypt/live/"$DOMAIN_NAME"/privkey.pem "$INSTALL_DIR/nginx/ssl/"

        # Update nginx configuration
        configure_nginx_ssl
    else
        print_error "Failed to obtain SSL certificate"
        print_warning "You can retry later or use manual certificate mode"
    fi
}

configure_ssl_route53() {
    print_step "1" "Configuring AWS Route53 DNS-01..."

    prompt_input "Enter your domain name" "" DOMAIN_NAME
    prompt_input "Enter your email address" "" EMAIL_ADDRESS
    prompt_secret "Enter AWS Access Key" AWS_ACCESS_KEY
    prompt_secret "Enter AWS Secret Key" AWS_SECRET_KEY

    print_step "2" "Installing certbot with Route53 plugin..."
    apt-get install -y -qq certbot python3-certbot-dns-route53 > /dev/null 2>&1
    print_success "Certbot installed"

    print_step "3" "Configuring AWS credentials..."
    mkdir -p /root/.aws
    cat > /root/.aws/credentials << EOF
[default]
aws_access_key_id = ${AWS_ACCESS_KEY}
aws_secret_access_key = ${AWS_SECRET_KEY}
EOF
    chmod 600 /root/.aws/credentials
    print_success "AWS credentials configured"

    print_step "4" "Obtaining SSL certificate..."
    if certbot certonly \
        --dns-route53 \
        -d "$DOMAIN_NAME" \
        --email "$EMAIL_ADDRESS" \
        --agree-tos \
        --non-interactive; then
        print_success "SSL certificate obtained"

        cp /etc/letsencrypt/live/"$DOMAIN_NAME"/fullchain.pem "$INSTALL_DIR/nginx/ssl/"
        cp /etc/letsencrypt/live/"$DOMAIN_NAME"/privkey.pem "$INSTALL_DIR/nginx/ssl/"
        configure_nginx_ssl
    else
        print_error "Failed to obtain SSL certificate"
    fi
}

configure_ssl_manual() {
    print_step "1" "Manual SSL certificate configuration..."

    prompt_input "Enter your domain name" "" DOMAIN_NAME

    echo ""
    echo "  Please place your SSL certificates in the following locations:"
    echo "  - Certificate: $INSTALL_DIR/nginx/ssl/fullchain.pem"
    echo "  - Private Key: $INSTALL_DIR/nginx/ssl/privkey.pem"
    echo ""

    if confirm "Have you placed your certificates in the above locations?"; then
        if [ -f "$INSTALL_DIR/nginx/ssl/fullchain.pem" ] && [ -f "$INSTALL_DIR/nginx/ssl/privkey.pem" ]; then
            print_success "SSL certificates found"
            configure_nginx_ssl
        else
            print_error "SSL certificates not found"
        fi
    fi
}

configure_nginx_ssl() {
    print_step "5" "Configuring nginx for SSL..."

    cat > "$INSTALL_DIR/nginx/conf.d/default.conf" << EOF
# GenMaster HTTPS Configuration
# Auto-generated by setup.sh

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN_NAME};

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    location /api {
        proxy_pass http://genmaster:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /ws {
        proxy_pass http://genmaster:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }

    location / {
        proxy_pass http://genmaster:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

    print_success "Nginx SSL configuration created"
}

# =============================================================================
# Tailscale Configuration
# =============================================================================

configure_tailscale() {
    print_section "Tailscale VPN Configuration"

    echo "  Tailscale provides secure mesh networking between GenMaster and GenSlave."
    echo "  This is the recommended way to connect the two devices."
    echo ""

    if ! confirm "Would you like to configure Tailscale VPN?"; then
        ENABLE_TAILSCALE=false
        save_state
        return 0
    fi

    ENABLE_TAILSCALE=true

    print_step "1" "Gathering Tailscale configuration..."

    echo ""
    echo "  Create an auth key at: https://login.tailscale.com/admin/settings/keys"
    echo "  Recommended settings:"
    echo "  - Reusable: Yes"
    echo "  - Ephemeral: No"
    echo "  - Pre-approved: Yes"
    echo "  - Tags: tag:generator"
    echo ""

    prompt_secret "Enter Tailscale Auth Key (tskey-auth-...)" TAILSCALE_AUTHKEY
    prompt_input "Enter Tailscale hostname" "genmaster" TAILSCALE_HOSTNAME

    print_success "Tailscale configuration saved"

    STATE_TAILSCALE_CONFIGURED=true
    save_state
}

# =============================================================================
# Cloudflare Tunnel Configuration
# =============================================================================

configure_cloudflare_tunnel() {
    print_section "Cloudflare Tunnel Configuration (Optional)"

    echo "  Cloudflare Tunnel allows public access to GenMaster without port forwarding."
    echo "  This is optional - Tailscale is sufficient for most use cases."
    echo ""

    if ! confirm "Would you like to configure Cloudflare Tunnel?"; then
        ENABLE_CLOUDFLARE_TUNNEL=false
        save_state
        return 0
    fi

    ENABLE_CLOUDFLARE_TUNNEL=true

    print_step "1" "Gathering Cloudflare Tunnel configuration..."

    echo ""
    echo "  Create a tunnel at: https://one.dash.cloudflare.com/"
    echo "  Navigate to: Access -> Tunnels -> Create a tunnel"
    echo ""

    prompt_secret "Enter Cloudflare Tunnel Token" CLOUDFLARE_TUNNEL_TOKEN

    print_success "Cloudflare Tunnel configuration saved"

    STATE_CLOUDFLARE_CONFIGURED=true
    save_state
}

# =============================================================================
# Environment Configuration
# =============================================================================

configure_environment() {
    print_section "Environment Configuration"

    print_step "1" "Gathering application configuration..."

    # GenSlave configuration
    if [ -z "$SLAVE_API_URL" ]; then
        if [ "$ENABLE_TAILSCALE" = true ]; then
            prompt_input "GenSlave API URL (Tailscale hostname)" "http://genslave:8000" SLAVE_API_URL
        else
            prompt_input "GenSlave API URL" "" SLAVE_API_URL
        fi
    fi

    # Generate secrets if not provided
    if [ -z "$APP_SECRET_KEY" ]; then
        print_step "2" "Generating application secret key..."
        APP_SECRET_KEY=$(generate_secret 32)
        print_success "Secret key generated"
    fi

    if [ -z "$DB_PASSWORD" ]; then
        print_step "3" "Generating database password..."
        DB_PASSWORD=$(generate_secret 32)
        print_success "Database password generated"
    fi

    if [ -z "$SLAVE_API_SECRET" ]; then
        print_step "4" "Generating GenSlave API secret..."
        SLAVE_API_SECRET=$(generate_secret 32)
        print_success "GenSlave API secret generated"
        echo ""
        print_warning "IMPORTANT: You must configure GenSlave with this same secret:"
        echo "           API_SECRET=$SLAVE_API_SECRET"
        echo ""
    fi

    # Create .env file
    print_step "5" "Creating environment configuration file..."

    cat > "$CONFIG_FILE" << EOF
# GenMaster Environment Configuration
# Generated by setup.sh on $(date)

# =============================================================================
# Application Settings
# =============================================================================
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=${APP_SECRET_KEY}

# GenMaster Docker image version
GENMASTER_VERSION=${DOCKER_TAG}

# =============================================================================
# Database Configuration (PostgreSQL)
# =============================================================================
DATABASE_USER=genmaster
DATABASE_PASSWORD=${DB_PASSWORD}
DATABASE_NAME=genmaster

# =============================================================================
# GenSlave Communication
# =============================================================================
SLAVE_API_URL=${SLAVE_API_URL}
SLAVE_API_SECRET=${SLAVE_API_SECRET}

# =============================================================================
# Heartbeat Settings
# =============================================================================
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# =============================================================================
# Webhook Notifications (Optional)
# =============================================================================
# WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
# WEBHOOK_SECRET=

# =============================================================================
# Logging
# =============================================================================
LOG_LEVEL=INFO

# =============================================================================
# Web Server Ports
# =============================================================================
HTTP_PORT=80
HTTPS_PORT=443

# =============================================================================
# SSL Configuration
# =============================================================================
SSL_CERT_PATH=${INSTALL_DIR}/nginx/ssl

# =============================================================================
# Tailscale VPN
# =============================================================================
EOF

    if [ "$ENABLE_TAILSCALE" = true ]; then
        cat >> "$CONFIG_FILE" << EOF
TAILSCALE_AUTHKEY=${TAILSCALE_AUTHKEY}
TAILSCALE_EXTRA_ARGS=--advertise-tags=tag:generator --hostname=${TAILSCALE_HOSTNAME}
EOF
    else
        cat >> "$CONFIG_FILE" << EOF
# TAILSCALE_AUTHKEY=
# TAILSCALE_EXTRA_ARGS=
EOF
    fi

    cat >> "$CONFIG_FILE" << EOF

# =============================================================================
# Cloudflare Tunnel
# =============================================================================
EOF

    if [ "$ENABLE_CLOUDFLARE_TUNNEL" = true ]; then
        cat >> "$CONFIG_FILE" << EOF
CLOUDFLARE_TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
EOF
    else
        cat >> "$CONFIG_FILE" << EOF
# CLOUDFLARE_TUNNEL_TOKEN=
EOF
    fi

    chmod 600 "$CONFIG_FILE"
    print_success "Environment configuration created: $CONFIG_FILE"

    # Copy docker-compose and nginx files
    print_step "6" "Copying Docker configuration files..."

    # Download latest docker-compose.yml
    if [ ! -f "$INSTALL_DIR/docker-compose.yml" ]; then
        curl -fsSL "https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genmaster/docker-compose.yml" \
            -o "$INSTALL_DIR/docker-compose.yml" 2>/dev/null || {
            print_warning "Could not download docker-compose.yml, using local copy"
        }
    fi

    # Copy nginx configuration if not exists
    if [ ! -f "$INSTALL_DIR/nginx/nginx.conf" ]; then
        curl -fsSL "https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genmaster/nginx/nginx.conf" \
            -o "$INSTALL_DIR/nginx/nginx.conf" 2>/dev/null || {
            print_warning "Could not download nginx.conf"
        }
    fi

    STATE_ENV_CONFIGURED=true
    save_state
    print_success "Environment configuration complete"
}

# =============================================================================
# Start Services
# =============================================================================

start_services() {
    print_section "Starting Services"

    cd "$INSTALL_DIR" || exit 1

    # Build profile arguments
    local profiles=""
    if [ "$ENABLE_TAILSCALE" = true ]; then
        profiles="$profiles --profile tailscale"
    fi
    if [ "$ENABLE_CLOUDFLARE_TUNNEL" = true ]; then
        profiles="$profiles --profile cloudflare"
    fi

    print_step "1" "Pulling Docker images..."
    docker compose $profiles pull
    print_success "Docker images pulled"

    print_step "2" "Starting containers..."
    docker compose $profiles up -d
    print_success "Containers started"

    print_step "3" "Waiting for services to be healthy..."
    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        if docker compose ps | grep -q "healthy"; then
            print_success "Services are healthy"
            break
        fi
        sleep 2
        ((waited+=2))
    done

    if [ $waited -ge $max_wait ]; then
        print_warning "Services may not be fully healthy yet"
    fi

    print_step "4" "Checking service status..."
    docker compose ps

    STATE_SERVICES_STARTED=true
    save_state
}

# =============================================================================
# Final Summary
# =============================================================================

print_summary() {
    print_section "Installation Complete!"

    echo "  GenMaster has been successfully installed and configured."
    echo ""
    echo -e "  ${BOLD}Access Information:${NC}"
    if [ "$SSL_PROVIDER" != "none" ] && [ -n "$DOMAIN_NAME" ]; then
        echo -e "  Web Dashboard:    ${GREEN}https://${DOMAIN_NAME}${NC}"
    else
        echo -e "  Web Dashboard:    ${GREEN}http://$(hostname -I | awk '{print $1}')${NC}"
    fi
    echo -e "  API Health:       ${GREEN}http://localhost/api/health${NC}"
    echo ""

    echo -e "  ${BOLD}Configuration Files:${NC}"
    echo "  Environment:      $CONFIG_FILE"
    echo "  Docker Compose:   $INSTALL_DIR/docker-compose.yml"
    echo "  Nginx Config:     $INSTALL_DIR/nginx/conf.d/default.conf"
    echo ""

    echo -e "  ${BOLD}Useful Commands:${NC}"
    echo "  View logs:        docker compose -f $INSTALL_DIR/docker-compose.yml logs -f"
    echo "  Restart:          docker compose -f $INSTALL_DIR/docker-compose.yml restart"
    echo "  Stop:             docker compose -f $INSTALL_DIR/docker-compose.yml down"
    echo "  Update:           docker compose -f $INSTALL_DIR/docker-compose.yml pull && docker compose up -d"
    echo ""

    if [ -n "$SLAVE_API_SECRET" ]; then
        echo -e "  ${BOLD}${YELLOW}IMPORTANT - GenSlave Configuration:${NC}"
        echo "  You must configure GenSlave with the following secret:"
        echo -e "  ${CYAN}API_SECRET=${SLAVE_API_SECRET}${NC}"
        echo ""
    fi

    echo -e "  ${BOLD}Next Steps:${NC}"
    echo "  1. Configure GenSlave with the shared secret shown above"
    echo "  2. Verify both devices can communicate via Tailscale"
    echo "  3. Test the web dashboard"
    echo ""

    log_info "Installation completed successfully"
}

# =============================================================================
# Main Function
# =============================================================================

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --preconfig)
                PRECONFIG_FILE="$2"
                shift 2
                ;;
            --unattended)
                UNATTENDED_MODE=true
                shift
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --create-preconfig)
                create_preconfig_template "$2"
                exit 0
                ;;
            --help|-h)
                echo "GenMaster Setup Script"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --preconfig FILE    Use preconfig file for unattended installation"
                echo "  --unattended        Run in unattended mode (requires preconfig)"
                echo "  --debug             Enable debug logging"
                echo "  --create-preconfig  Create a preconfig template file"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Initialize logging
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    log_info "GenMaster setup started"

    # Check root
    check_root

    # Print header
    print_header

    # Load preconfig if specified
    if [ -n "$PRECONFIG_FILE" ]; then
        load_preconfig "$PRECONFIG_FILE"
    fi

    # Load previous state if exists
    if load_state; then
        print_info "Found previous installation state"
        if ! confirm "Would you like to resume the previous installation?"; then
            rm -f "$STATE_FILE"
            STATE_SYSTEM_PREPARED=false
            STATE_DOCKER_INSTALLED=false
            STATE_SSL_CONFIGURED=false
            STATE_TAILSCALE_CONFIGURED=false
            STATE_CLOUDFLARE_CONFIGURED=false
            STATE_ENV_CONFIGURED=false
            STATE_SERVICES_STARTED=false
        fi
    fi

    # Run installation steps
    if [ "$STATE_SYSTEM_PREPARED" != true ]; then
        prepare_system
    else
        print_info "System already prepared, skipping..."
    fi

    if [ "$STATE_DOCKER_INSTALLED" != true ]; then
        install_docker
    else
        print_info "Docker already installed, skipping..."
    fi

    if [ "$STATE_SSL_CONFIGURED" != true ]; then
        configure_ssl
    else
        print_info "SSL already configured, skipping..."
    fi

    if [ "$STATE_TAILSCALE_CONFIGURED" != true ]; then
        configure_tailscale
    else
        print_info "Tailscale already configured, skipping..."
    fi

    if [ "$STATE_CLOUDFLARE_CONFIGURED" != true ]; then
        configure_cloudflare_tunnel
    else
        print_info "Cloudflare Tunnel already configured, skipping..."
    fi

    if [ "$STATE_ENV_CONFIGURED" != true ]; then
        configure_environment
    else
        print_info "Environment already configured, skipping..."
    fi

    if [ "$STATE_SERVICES_STARTED" != true ]; then
        start_services
    else
        print_info "Services already started"
        if confirm "Would you like to restart the services?"; then
            start_services
        fi
    fi

    # Print summary
    print_summary

    log_info "GenMaster setup completed"
}

# Run main function
main "$@"
