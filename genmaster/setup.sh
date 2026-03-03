#!/bin/bash
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /setup.sh
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║                                                                           ║
# ║     GenMaster Interactive Setup Script                                    ║
# ║                                                                           ║
# ║     Automated deployment for GenMaster generator control system           ║
# ║     with PostgreSQL, Nginx reverse proxy, and optional services           ║
# ║                                                                           ║
# ║     Version 1.0.0                                                         ║
# ║     Richard J. Sears                                                      ║
# ║     richardjsears@protonmail.com                                          ║
# ║     January 2026                                                          ║
# ║                                                                           ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/.genmaster_setup_config"
STATE_FILE="${SCRIPT_DIR}/.genmaster_setup_state"

# Detect the real user (handles both direct execution and sudo ./setup.sh)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
elif [ -n "$USER" ]; then
    REAL_USER="$USER"
else
    REAL_USER=$(whoami)
fi

# Default container names
DEFAULT_POSTGRES_CONTAINER="genmaster_db"
DEFAULT_GENMASTER_CONTAINER="genmaster"
DEFAULT_NGINX_CONTAINER="genmaster_nginx"
DEFAULT_REDIS_CONTAINER="genmaster_redis"

# Default database settings
DEFAULT_DB_NAME="genmaster"
DEFAULT_DB_USER="genmaster"

# Default ports
DEFAULT_HTTPS_PORT="443"
DEFAULT_PORTAINER_PORT="9000"

# Optional service flags (set during configuration)
INSTALL_CLOUDFLARE_TUNNEL=false
INSTALL_TAILSCALE=false
INSTALL_PORTAINER=false
INSTALL_WIFI_WATCHDOG=false

# GenSlave configuration
GENSLAVE_ENABLED=true
GENSLAVE_API_URL=""
GENSLAVE_API_SECRET=""
GENSLAVE_IP=""
GENSLAVE_HOSTNAME="genslave"
AUTO_ARM_RELAY_ON_CONNECT=false

# Mock GPIO mode (auto-detected based on hardware)
MOCK_GPIO_MODE=false

# Docker image source: true = pull from Docker Hub (faster), false = build locally
USE_DOCKER_HUB_IMAGE=true
DOCKER_HUB_IMAGE="rjsears/genmaster:latest"

# Docker socket group ID (auto-detected for container management)
DOCKER_GID="999"

# Admin user configuration
ADMIN_USERNAME="admin"
ADMIN_PASSWORD=""

# Auto-generated credential tracking (for display at end of setup)
AUTOGEN_DB_PASSWORD=false
AUTOGEN_SECRET_KEY=false
AUTOGEN_SLAVE_SECRET=false
AUTOGEN_ADMIN_PASSWORD=false

# DNS Provider and SSL Configuration
DNS_PROVIDER_NAME=""
DNS_CERTBOT_IMAGE=""
DNS_CREDENTIALS_FILE=""
DNS_CERTBOT_FLAGS=""
LETSENCRYPT_EMAIL=""

# Internal IP ranges that get full access (space-separated CIDR blocks)
DEFAULT_INTERNAL_IP_RANGES="127.0.0.1/32 100.64.0.0/10 172.16.0.0/12 10.0.0.0/8 192.168.0.0/16 10.200.40.0/24 98.173.155.64/26"
INTERNAL_IP_RANGES="${INTERNAL_IP_RANGES:-$DEFAULT_INTERNAL_IP_RANGES}"

# ═══════════════════════════════════════════════════════════════════════════════
# COLORS & STYLING
# ═══════════════════════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
NC='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

print_header() {
    local title="$1"
    local width=75
    local padding=$(( (width - ${#title} - 2) / 2 ))

    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    printf "${CYAN}║${NC}%*s${WHITE}${BOLD} %s ${NC}%*s${CYAN}║${NC}\n" $padding "" "$title" $((padding + (width - ${#title} - 2) % 2)) ""
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    local title="$1"
    echo ""
    echo -e "${BLUE}┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│${NC} ${WHITE}${BOLD}$title${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────────────────────────┘${NC}"
}

print_subsection() {
    echo ""
    echo -e "${GRAY}───────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}  ✓${NC} $1"
}

print_error() {
    echo -e "${RED}  ✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}  ⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}  ℹ${NC} $1"
}

print_step() {
    local step_num="$1"
    local total_steps="$2"
    local description="$3"
    echo ""
    echo -e "${MAGENTA}  [$step_num/$total_steps]${NC} ${WHITE}${BOLD}$description${NC}"
    echo ""
}

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    local current_value="${!var_name}"
    if [ -n "$current_value" ]; then
        default="$current_value"
    fi

    if [ "$PRECONFIG_AUTO_CONFIRM" = "true" ]; then
        print_info "Using: $prompt = $default"
        eval "$var_name='$default'"
        return
    fi

    echo -ne "${WHITE}  $prompt [$default]${NC}: "
    read value

    if [ -z "$value" ]; then
        eval "$var_name='$default'"
    else
        eval "$var_name='$value'"
    fi
}

confirm_prompt() {
    local prompt="$1"
    local default="${2:-y}"

    if [ "$PRECONFIG_AUTO_CONFIRM" = "true" ]; then
        if [ "$default" = "y" ]; then
            print_info "Auto-confirming: $prompt [Y]"
            return 0
        else
            print_info "Auto-declining: $prompt [N]"
            return 1
        fi
    fi

    if [ "$default" = "y" ]; then
        echo -ne "${WHITE}  $prompt [Y/n]${NC}: "
    else
        echo -ne "${WHITE}  $prompt [y/N]${NC}: "
    fi

    read response
    response=${response:-$default}

    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Read sensitive input with masking (shows first 10 chars, rest as *)
read_masked_token() {
    MASKED_INPUT=""
    local char=""
    local display=""

    # Disable echo and enable raw mode
    stty -echo

    while IFS= read -r -n1 char; do
        # Check for Enter (empty char after read -n1)
        if [[ -z "$char" ]]; then
            break
        fi

        # Check for backspace (ASCII 127 or 8)
        if [[ "$char" == $'\x7f' ]] || [[ "$char" == $'\x08' ]]; then
            if [[ -n "$MASKED_INPUT" ]]; then
                # Remove last character from input
                MASKED_INPUT="${MASKED_INPUT%?}"
                # Clear line and redisplay
                echo -ne "\r\033[K"
                local len=${#MASKED_INPUT}
                if [[ $len -le 10 ]]; then
                    display="$MASKED_INPUT"
                else
                    display="${MASKED_INPUT:0:10}$(printf '%*s' $((len - 10)) '' | tr ' ' '*')"
                fi
                echo -ne "$display"
            fi
            continue
        fi

        # Add character to input
        MASKED_INPUT+="$char"

        # Display: first 10 chars visible, rest as *
        local len=${#MASKED_INPUT}
        if [[ $len -le 10 ]]; then
            echo -ne "$char"
        else
            echo -ne "*"
        fi
    done

    # Re-enable echo
    stty echo
    echo ""  # New line after input
}

# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Check if running on a Raspberry Pi
is_raspberry_pi() {
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        return 0
    fi
    return 1
}

# Check if running inside an LXC container
is_lxc_container() {
    if command_exists systemd-detect-virt && [ "$(systemd-detect-virt)" = "lxc" ]; then
        return 0
    fi
    if grep -qa 'container=lxc' /proc/1/environ 2>/dev/null; then
        return 0
    fi
    if [ -f /run/host/container-manager ]; then
        return 0
    fi
    return 1
}

# Get all local IP addresses
get_local_ips() {
    hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^$' || \
    ip addr show 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | cut -d'/' -f1 || \
    ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}'
}

# Detect hardware and set mock GPIO mode if not on Raspberry Pi
detect_hardware_mode() {
    print_section "Hardware Detection"

    if is_raspberry_pi; then
        local pi_model=$(grep "Model" /proc/cpuinfo 2>/dev/null | cut -d':' -f2 | xargs)
        print_success "Raspberry Pi detected: $pi_model"
        print_success "GPIO mode: REAL (hardware GPIO enabled)"
        MOCK_GPIO_MODE=false
    else
        if is_lxc_container; then
            print_info "LXC container environment"
        else
            print_info "Non-Raspberry Pi system detected"
        fi
        print_warning "GPIO mode: MOCK (simulated GPIO for testing)"
        print_info "Development API will be available at /api/dev/*"
        MOCK_GPIO_MODE=true
    fi
    echo ""
}

# Show LXC container warning with Proxmox configuration instructions
show_lxc_warning() {
    echo ""
    echo -e "  ${RED}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "  ${RED}║${NC}                          ${WHITE}${BOLD}LXC CONTAINER DETECTED${NC}                           ${RED}║${NC}"
    echo -e "  ${RED}╠═══════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "  ${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "  ${RED}║${NC}  ${YELLOW}IMPORTANT:${NC} Docker inside LXC requires special Proxmox configuration.     ${RED}║${NC}"
    echo -e "  ${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "  ${RED}║${NC}  On your ${WHITE}Proxmox host${NC}, add this line to the container config:             ${RED}║${NC}"
    echo -e "  ${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "  ${RED}║${NC}      ${CYAN}/etc/pve/lxc/<CTID>.conf${NC}                                             ${RED}║${NC}"
    echo -e "  ${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "  ${RED}║${NC}      ${WHITE}lxc.apparmor.profile: unconfined${NC}                                     ${RED}║${NC}"
    echo -e "  ${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "  ${RED}║${NC}  Then restart this container from Proxmox before continuing.              ${RED}║${NC}"
    echo -e "  ${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "  ${RED}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    if ! confirm_prompt "Have you added this configuration and restarted the container?"; then
        echo ""
        print_info "Please configure Proxmox and restart the container, then run this script again."
        exit 0
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# OS DETECTION & PACKAGE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

detect_os() {
    DISTRO=""
    DISTRO_FAMILY=""
    PKG_MANAGER=""
    PKG_UPDATE=""
    PKG_INSTALL=""

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    fi

    case $DISTRO in
        ubuntu|debian|linuxmint|pop|raspbian)
            DISTRO_FAMILY="debian"
            PKG_MANAGER="apt-get"
            PKG_UPDATE="apt-get update"
            PKG_INSTALL="apt-get install -y"
            ;;
        centos|rhel|rocky|almalinux|ol)
            DISTRO_FAMILY="rhel"
            if command_exists dnf; then
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update || true"
                PKG_INSTALL="dnf install -y"
            else
                PKG_MANAGER="yum"
                PKG_UPDATE="yum check-update || true"
                PKG_INSTALL="yum install -y"
            fi
            ;;
        fedora)
            DISTRO_FAMILY="fedora"
            PKG_MANAGER="dnf"
            PKG_UPDATE="dnf check-update || true"
            PKG_INSTALL="dnf install -y"
            ;;
        arch|manjaro)
            DISTRO_FAMILY="arch"
            PKG_MANAGER="pacman"
            PKG_UPDATE="pacman -Sy"
            PKG_INSTALL="pacman -S --noconfirm"
            ;;
        opensuse*|sles)
            DISTRO_FAMILY="suse"
            PKG_MANAGER="zypper"
            PKG_UPDATE="zypper refresh"
            PKG_INSTALL="zypper install -y"
            ;;
        alpine)
            DISTRO_FAMILY="alpine"
            PKG_MANAGER="apk"
            PKG_UPDATE="apk update"
            PKG_INSTALL="apk add"
            ;;
        *)
            if command_exists apt-get; then
                DISTRO_FAMILY="debian"
                PKG_MANAGER="apt-get"
                PKG_UPDATE="apt-get update"
                PKG_INSTALL="apt-get install -y"
            elif command_exists dnf; then
                DISTRO_FAMILY="rhel"
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update || true"
                PKG_INSTALL="dnf install -y"
            elif command_exists yum; then
                DISTRO_FAMILY="rhel"
                PKG_MANAGER="yum"
                PKG_UPDATE="yum check-update || true"
                PKG_INSTALL="yum install -y"
            else
                print_error "Could not detect package manager"
                return 1
            fi
            ;;
    esac

    return 0
}

update_system() {
    print_info "Updating system packages..."

    if [ -z "$PKG_MANAGER" ]; then
        detect_os || return 1
    fi

    case $DISTRO_FAMILY in
        debian)
            run_privileged apt-get update -qq
            run_privileged apt-get upgrade -y -qq
            ;;
        rhel)
            if [ "$PKG_MANAGER" = "dnf" ]; then
                run_privileged dnf update -y -q
            else
                run_privileged yum update -y -q
            fi
            ;;
        fedora)
            run_privileged dnf upgrade -y -q
            ;;
        arch)
            run_privileged pacman -Syu --noconfirm
            ;;
        alpine)
            run_privileged apk update -q
            run_privileged apk upgrade -q
            ;;
        suse)
            run_privileged zypper refresh -q
            run_privileged zypper update -y -q
            ;;
        *)
            print_warning "System update not supported for this distribution"
            return 1
            ;;
    esac

    print_success "System packages updated"
    return 0
}

install_required_utilities() {
    print_info "Checking required utilities..."

    if [ -z "$PKG_MANAGER" ]; then
        detect_os || return 1
    fi

    local missing_utils=""
    command_exists curl || missing_utils="$missing_utils curl"
    command_exists git || missing_utils="$missing_utils git"
    command_exists openssl || missing_utils="$missing_utils openssl"
    command_exists jq || missing_utils="$missing_utils jq"
    command_exists tmux || missing_utils="$missing_utils tmux"

    if [ -z "$missing_utils" ]; then
        print_success "All required utilities are installed"
        return 0
    fi

    print_info "Installing:$missing_utils"
    run_privileged $PKG_UPDATE

    # Alpine uses different package handling
    if [ "$DISTRO_FAMILY" = "alpine" ]; then
        run_privileged apk add $missing_utils
    else
        run_privileged $PKG_INSTALL $missing_utils
    fi

    # Verify installation
    local failed_utils=""
    for util in $missing_utils; do
        if ! command_exists "$util"; then
            failed_utils="$failed_utils $util"
        fi
    done

    if [ -n "$failed_utils" ]; then
        print_warning "Failed to install:$failed_utils"
        print_info "You may need to install these manually"
    else
        print_success "Required utilities installed"
    fi

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGEMENT FOR RESUME CAPABILITY
# ═══════════════════════════════════════════════════════════════════════════════

CURRENT_STEP=0

save_state() {
    local step_name=$1
    CURRENT_STEP=$2

    cat > "$STATE_FILE" << EOF
# GenMaster Setup State File - DO NOT EDIT MANUALLY
# Generated: $(date -Iseconds)
SAVED_STEP_NAME="$step_name"
SAVED_STEP_NUM="$CURRENT_STEP"
SAVED_DOMAIN="$DOMAIN"
SAVED_DB_NAME="$DB_NAME"
SAVED_DB_USER="$DB_USER"
SAVED_DB_PASSWORD="$DB_PASSWORD"
SAVED_POSTGRES_CONTAINER="$POSTGRES_CONTAINER"
SAVED_GENMASTER_CONTAINER="$GENMASTER_CONTAINER"
SAVED_NGINX_CONTAINER="$NGINX_CONTAINER"
SAVED_REDIS_CONTAINER="$REDIS_CONTAINER"
SAVED_TIMEZONE="$TIMEZONE"
SAVED_SECRET_KEY="$SECRET_KEY"
SAVED_GENSLAVE_ENABLED="$GENSLAVE_ENABLED"
SAVED_GENSLAVE_API_URL="$GENSLAVE_API_URL"
SAVED_GENSLAVE_API_SECRET="$GENSLAVE_API_SECRET"
SAVED_GENSLAVE_IP="$GENSLAVE_IP"
SAVED_GENSLAVE_HOSTNAME="$GENSLAVE_HOSTNAME"
SAVED_AUTO_ARM_RELAY_ON_CONNECT="$AUTO_ARM_RELAY_ON_CONNECT"
SAVED_WEBHOOK_URL="$WEBHOOK_URL"
SAVED_WEBHOOK_SECRET="$WEBHOOK_SECRET"
SAVED_INSTALL_PORTAINER="$INSTALL_PORTAINER"
SAVED_INSTALL_CLOUDFLARE_TUNNEL="$INSTALL_CLOUDFLARE_TUNNEL"
SAVED_CLOUDFLARE_TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN"
SAVED_INSTALL_TAILSCALE="$INSTALL_TAILSCALE"
SAVED_TAILSCALE_AUTH_KEY="$TAILSCALE_AUTH_KEY"
SAVED_TAILSCALE_HOSTNAME="$TAILSCALE_HOSTNAME"
SAVED_MOCK_GPIO_MODE="$MOCK_GPIO_MODE"
SAVED_INSTALL_WIFI_WATCHDOG="$INSTALL_WIFI_WATCHDOG"
EOF
    chmod 600 "$STATE_FILE"
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        DOMAIN="${SAVED_DOMAIN:-}"
        DB_NAME="${SAVED_DB_NAME:-}"
        DB_USER="${SAVED_DB_USER:-}"
        DB_PASSWORD="${SAVED_DB_PASSWORD:-}"
        POSTGRES_CONTAINER="${SAVED_POSTGRES_CONTAINER:-}"
        GENMASTER_CONTAINER="${SAVED_GENMASTER_CONTAINER:-}"
        NGINX_CONTAINER="${SAVED_NGINX_CONTAINER:-}"
        REDIS_CONTAINER="${SAVED_REDIS_CONTAINER:-}"
        TIMEZONE="${SAVED_TIMEZONE:-}"
        SECRET_KEY="${SAVED_SECRET_KEY:-}"
        GENSLAVE_ENABLED="${SAVED_GENSLAVE_ENABLED:-true}"
        GENSLAVE_API_URL="${SAVED_GENSLAVE_API_URL:-}"
        GENSLAVE_API_SECRET="${SAVED_GENSLAVE_API_SECRET:-}"
        GENSLAVE_IP="${SAVED_GENSLAVE_IP:-}"
        GENSLAVE_HOSTNAME="${SAVED_GENSLAVE_HOSTNAME:-genslave}"
        AUTO_ARM_RELAY_ON_CONNECT="${SAVED_AUTO_ARM_RELAY_ON_CONNECT:-false}"
        WEBHOOK_URL="${SAVED_WEBHOOK_URL:-}"
        WEBHOOK_SECRET="${SAVED_WEBHOOK_SECRET:-}"
        INSTALL_PORTAINER="${SAVED_INSTALL_PORTAINER:-false}"
        INSTALL_CLOUDFLARE_TUNNEL="${SAVED_INSTALL_CLOUDFLARE_TUNNEL:-false}"
        CLOUDFLARE_TUNNEL_TOKEN="${SAVED_CLOUDFLARE_TUNNEL_TOKEN:-}"
        INSTALL_TAILSCALE="${SAVED_INSTALL_TAILSCALE:-false}"
        TAILSCALE_AUTH_KEY="${SAVED_TAILSCALE_AUTH_KEY:-}"
        TAILSCALE_HOSTNAME="${SAVED_TAILSCALE_HOSTNAME:-}"
        INSTALL_WIFI_WATCHDOG="${SAVED_INSTALL_WIFI_WATCHDOG:-false}"
        MOCK_GPIO_MODE="${SAVED_MOCK_GPIO_MODE:-false}"
        CURRENT_STEP="${SAVED_STEP_NUM:-0}"
        return 0
    fi
    return 1
}

check_resume() {
    if [ -f "$STATE_FILE" ] && load_state; then
        print_warning "Previous incomplete installation detected."
        echo ""
        echo -e "  ${WHITE}Last completed step:${NC} ${CYAN}${SAVED_STEP_NAME}${NC}"
        if [ -n "$DOMAIN" ]; then
            echo -e "  ${WHITE}Domain:${NC} ${CYAN}${DOMAIN}${NC}"
        fi
        echo ""
        echo -e "  ${WHITE}Options:${NC}"
        echo -e "    ${CYAN}1)${NC} Resume from where you left off"
        echo -e "    ${CYAN}2)${NC} Start fresh (clears saved progress)"
        echo ""

        local resume_choice=""
        while [[ ! "$resume_choice" =~ ^[12]$ ]]; do
            echo -ne "${WHITE}  Enter your choice [1-2]${NC}: "
            read resume_choice
        done

        if [ "$resume_choice" = "1" ]; then
            return 0
        else
            clear_state
            return 1
        fi
    fi
    return 1
}

clear_state() {
    rm -f "$STATE_FILE"
    CURRENT_STEP=0
}

# ═══════════════════════════════════════════════════════════════════════════════
# PRE-CONFIGURATION FILE LOADING
# ═══════════════════════════════════════════════════════════════════════════════

load_preconfig() {
    local config_file="$1"

    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        exit 1
    fi

    print_section "Loading Pre-Configuration"
    print_info "Reading: $config_file"

    source "$config_file"

    # Validate required fields
    if [ -z "$DOMAIN" ]; then
        print_error "DOMAIN is required"
        exit 1
    fi
    print_success "Domain: $DOMAIN"

    # Defaults
    DB_NAME="${DB_NAME:-$DEFAULT_DB_NAME}"
    DB_USER="${DB_USER:-$DEFAULT_DB_USER}"
    POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-$DEFAULT_POSTGRES_CONTAINER}"
    GENMASTER_CONTAINER="${GENMASTER_CONTAINER:-$DEFAULT_GENMASTER_CONTAINER}"
    NGINX_CONTAINER="${NGINX_CONTAINER:-$DEFAULT_NGINX_CONTAINER}"
    REDIS_CONTAINER="${REDIS_CONTAINER:-$DEFAULT_REDIS_CONTAINER}"
    TIMEZONE="${TIMEZONE:-America/Los_Angeles}"

    # Generate missing credentials
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
        AUTOGEN_DB_PASSWORD=true
        print_info "Auto-generated database password"
    fi

    if [ -z "$SECRET_KEY" ]; then
        SECRET_KEY=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 64)
        AUTOGEN_SECRET_KEY=true
        print_info "Auto-generated secret key"
    fi

    # GenSlave
    GENSLAVE_ENABLED="${GENSLAVE_ENABLED:-true}"
    if [ "$GENSLAVE_ENABLED" = "true" ] && [ -n "$GENSLAVE_API_URL" ]; then
        if [ -z "$GENSLAVE_API_SECRET" ]; then
            GENSLAVE_API_SECRET=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
            AUTOGEN_SLAVE_SECRET=true
        fi
        print_success "GenSlave: $GENSLAVE_API_URL"
    fi

    # Optional services
    if [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
        INSTALL_CLOUDFLARE_TUNNEL=true
        print_success "Cloudflare Tunnel: Enabled"
    fi

    if [ -n "$TAILSCALE_AUTH_KEY" ]; then
        INSTALL_TAILSCALE=true
        TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-genmaster}"
        print_success "Tailscale: Enabled"
    fi

    INSTALL_PORTAINER="${PORTAINER_ENABLED:-false}"

    if [ "$AUTO_CONFIRM" = "true" ]; then
        PRECONFIG_AUTO_CONFIRM=true
    else
        PRECONFIG_AUTO_CONFIRM=false
    fi

    print_success "Configuration loaded"
    PRECONFIG_MODE=true
}

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

detect_current_version() {
    if [ ! -f "${CONFIG_FILE}" ]; then
        echo "none"
        return
    fi

    if [ -f "${SCRIPT_DIR}/docker-compose.yaml" ]; then
        if grep -q "genmaster" "${SCRIPT_DIR}/docker-compose.yaml" 2>/dev/null; then
            echo "1.0"
        else
            echo "unknown"
        fi
    else
        echo "none"
    fi
}

handle_version_detection() {
    local current_version=$(detect_current_version)

    case $current_version in
        "1.0")
            echo ""
            echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
            echo -e "${YELLOW}║                     ${BOLD}⚡  EXISTING SETUP DETECTED  ⚡${NC}                       ${YELLOW}║${NC}"
            echo -e "${YELLOW}║             ${WHITE}Version 1.0 installation found in this directory${NC}              ${YELLOW}║${NC}"
            echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "  ${WHITE}What would you like to do?${NC}"
            echo ""
            echo -e "    ${CYAN}1)${NC} ${GREEN}Reconfigure${NC} existing installation"
            echo -e "    ${CYAN}2)${NC} Start ${RED}Fresh${NC} (will backup existing config)"
            echo -e "    ${CYAN}3)${NC} Exit"
            echo ""

            local choice=""
            while [[ ! "$choice" =~ ^[123]$ ]]; do
                echo -ne "${WHITE}  Enter your choice [1-3]${NC}: "
                read choice
            done

            case $choice in
                1) INSTALL_MODE="reconfigure" ;;
                2) backup_existing_config; INSTALL_MODE="fresh" ;;
                3) print_info "Exiting."; exit 0 ;;
            esac
            ;;
        "none")
            print_info "Fresh installation"
            INSTALL_MODE="fresh"
            ;;
        *)
            print_error "Unknown installation detected"
            if confirm_prompt "Attempt fresh installation?"; then
                INSTALL_MODE="fresh"
            else
                exit 1
            fi
            ;;
    esac
}

restore_dns_settings_from_provider() {
    # Restore DNS_CERTBOT_IMAGE and related settings based on DNS_PROVIDER
    # This is needed when loading config that only has DNS_PROVIDER saved
    local provider="${DNS_PROVIDER:-${DNS_PROVIDER_NAME:-}}"

    # Sync variable names (config uses DNS_PROVIDER, code uses DNS_PROVIDER_NAME)
    if [ -n "$DNS_PROVIDER" ] && [ -z "$DNS_PROVIDER_NAME" ]; then
        DNS_PROVIDER_NAME="$DNS_PROVIDER"
    fi

    # Set DNS_CERTBOT_IMAGE based on provider if not already set
    if [ -z "$DNS_CERTBOT_IMAGE" ] && [ -n "$DNS_PROVIDER_NAME" ]; then
        case $DNS_PROVIDER_NAME in
            cloudflare)
                DNS_CERTBOT_IMAGE="certbot/dns-cloudflare:latest"
                DNS_CREDENTIALS_FILE="cloudflare.ini"
                ;;
            route53)
                DNS_CERTBOT_IMAGE="certbot/dns-route53:latest"
                DNS_CREDENTIALS_FILE="route53.ini"
                ;;
            google)
                DNS_CERTBOT_IMAGE="certbot/dns-google:latest"
                DNS_CREDENTIALS_FILE="google.json"
                ;;
            digitalocean)
                DNS_CERTBOT_IMAGE="certbot/dns-digitalocean:latest"
                DNS_CREDENTIALS_FILE="digitalocean.ini"
                ;;
            manual|*)
                DNS_CERTBOT_IMAGE="certbot/certbot:latest"
                DNS_CREDENTIALS_FILE="credentials.ini"
                ;;
        esac
    fi
}

restore_optional_services_from_config() {
    # Restore INSTALL_* variables from *_ENABLED variables loaded from config
    # Config saves: CLOUDFLARE_TUNNEL_ENABLED, TAILSCALE_ENABLED, etc.
    # Code uses: INSTALL_CLOUDFLARE_TUNNEL, INSTALL_TAILSCALE, etc.

    # Cloudflare Tunnel
    if [ -n "$CLOUDFLARE_TUNNEL_ENABLED" ]; then
        INSTALL_CLOUDFLARE_TUNNEL="$CLOUDFLARE_TUNNEL_ENABLED"
    fi

    # Tailscale
    if [ -n "$TAILSCALE_ENABLED" ]; then
        INSTALL_TAILSCALE="$TAILSCALE_ENABLED"
    fi

    # Portainer
    if [ -n "$PORTAINER_ENABLED" ]; then
        INSTALL_PORTAINER="$PORTAINER_ENABLED"
    fi
}

backup_existing_config() {
    local backup_dir="${SCRIPT_DIR}/.backups/$(date +%Y%m%d_%H%M%S)"

    mkdir -p "$backup_dir"
    print_info "Backing up existing configuration..."

    # Backup all config files
    for file in .env docker-compose.yaml nginx/nginx.conf .genmaster_setup_config .genmaster_setup_state; do
        if [ -f "${SCRIPT_DIR}/${file}" ]; then
            local target_file=$(basename "$file")
            cp "${SCRIPT_DIR}/${file}" "${backup_dir}/${target_file}"
        fi
    done

    # Backup certbot credentials if they exist
    if [ -d "${SCRIPT_DIR}/certbot" ]; then
        for cred_file in "${SCRIPT_DIR}/certbot"/*.ini "${SCRIPT_DIR}/certbot"/*.json; do
            [ -f "$cred_file" ] && cp "$cred_file" "${backup_dir}/"
        done
    fi

    print_success "Backup complete: ${backup_dir}"
}

list_available_backups() {
    local backup_base="${SCRIPT_DIR}/.backups"

    if [ ! -d "$backup_base" ] || [ -z "$(ls -A $backup_base 2>/dev/null)" ]; then
        return 1
    fi

    AVAILABLE_BACKUPS=()
    while IFS= read -r backup_dir; do
        if [ -d "$backup_dir" ]; then
            local timestamp=$(basename "$backup_dir")
            local formatted_date=$(echo "$timestamp" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)_\([0-9]\{2\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3 \4:\5:\6/')
            local file_count=$(ls -1 "$backup_dir" 2>/dev/null | wc -l)
            AVAILABLE_BACKUPS+=("${timestamp}|${formatted_date}|${file_count} files")
        fi
    done < <(ls -dt ${backup_base}/*/ 2>/dev/null)

    if [ ${#AVAILABLE_BACKUPS[@]} -eq 0 ]; then
        return 1
    fi

    return 0
}

rollback_config() {
    print_section "Rollback Configuration"

    if ! list_available_backups; then
        print_error "No backups found in ${SCRIPT_DIR}/.backups/"
        echo ""
        print_info "Backups are created automatically before any reconfiguration."
        return 1
    fi

    echo -e "  ${WHITE}Available backups:${NC}"
    echo ""

    local i=1
    for backup_info in "${AVAILABLE_BACKUPS[@]}"; do
        local timestamp=$(echo "$backup_info" | cut -d'|' -f1)
        local formatted_date=$(echo "$backup_info" | cut -d'|' -f2)
        local file_count=$(echo "$backup_info" | cut -d'|' -f3)
        echo -e "    ${CYAN}${i})${NC} ${WHITE}${formatted_date}${NC} (${file_count})"
        i=$((i + 1))
    done
    echo -e "    ${CYAN}${i})${NC} Cancel - return to menu"
    echo ""

    local max_choice=$i
    local choice=""
    while [[ ! "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "$max_choice" ]; do
        echo -ne "${WHITE}  Select backup to restore [1-${max_choice}]${NC}: "
        read choice
    done

    if [ "$choice" -eq "$max_choice" ]; then
        print_info "Rollback cancelled"
        return 0
    fi

    local selected_index=$((choice - 1))
    local selected_backup=$(echo "${AVAILABLE_BACKUPS[$selected_index]}" | cut -d'|' -f1)
    local backup_dir="${SCRIPT_DIR}/.backups/${selected_backup}"

    echo ""
    echo -e "  ${YELLOW}${BOLD}WARNING: This will overwrite your current configuration!${NC}"
    echo ""
    echo -e "  ${WHITE}Files to be restored from ${CYAN}${selected_backup}${NC}:${NC}"
    ls -1 "$backup_dir" | while read file; do
        echo -e "    • ${file}"
    done
    echo ""

    if ! confirm_prompt "Are you sure you want to restore this backup?"; then
        print_info "Rollback cancelled"
        return 0
    fi

    # Create safety backup before rollback
    print_info "Creating safety backup of current state..."
    local safety_backup="${SCRIPT_DIR}/.backups/pre_rollback_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$safety_backup"
    for file in .env docker-compose.yaml .genmaster_setup_config .genmaster_setup_state; do
        [ -f "${SCRIPT_DIR}/${file}" ] && cp "${SCRIPT_DIR}/${file}" "${safety_backup}/"
    done
    [ -f "${SCRIPT_DIR}/nginx/nginx.conf" ] && cp "${SCRIPT_DIR}/nginx/nginx.conf" "${safety_backup}/nginx.conf"

    # Restore files from backup
    print_info "Restoring configuration files..."
    local restored=0
    for file in "$backup_dir"/*; do
        local filename=$(basename "$file")
        if [ "$filename" = "nginx.conf" ]; then
            mkdir -p "${SCRIPT_DIR}/nginx"
            cp "$file" "${SCRIPT_DIR}/nginx/nginx.conf"
        else
            cp "$file" "${SCRIPT_DIR}/${filename}"
        fi
        print_success "Restored ${filename}"
        restored=$((restored + 1))
    done

    echo ""
    print_success "Rollback complete! ${restored} items restored."
    echo ""
    echo -e "  ${WHITE}Safety backup saved to:${NC} ${CYAN}${safety_backup}${NC}"
    echo ""

    if confirm_prompt "Would you like to redeploy the stack with the restored configuration?"; then
        # Reload the restored config
        if [ -f "${SCRIPT_DIR}/.env" ]; then
            source "${SCRIPT_DIR}/.env" 2>/dev/null || true
            restore_dns_settings_from_provider
            restore_optional_services_from_config
        fi
        deploy_stack
    else
        print_info "Configuration restored. Run './setup.sh' and choose 'Reconfigure' then option 6 to redeploy."
    fi

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# DOCKER INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

check_and_install_docker() {
    print_section "Docker Check"

    # Detect platform
    local CURRENT_PLATFORM=""
    if [ "$(uname)" = "Darwin" ]; then
        CURRENT_PLATFORM="macos"
    elif grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null; then
        CURRENT_PLATFORM="wsl"
    else
        CURRENT_PLATFORM="linux"
    fi

    if command_exists docker; then
        local docker_version=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
        print_success "Docker installed (version $docker_version)"

        if docker info >/dev/null 2>&1; then
            print_success "Docker daemon running"
        else
            print_warning "Docker daemon not running"

            if [ "$CURRENT_PLATFORM" = "macos" ]; then
                print_error "Please start Docker Desktop on macOS"
                exit 1
            elif [ "$CURRENT_PLATFORM" = "wsl" ]; then
                print_error "Please start Docker Desktop on Windows"
                exit 1
            fi

            if confirm_prompt "Start Docker daemon?"; then
                run_privileged systemctl start docker
                run_privileged systemctl enable docker
                print_success "Docker daemon started and enabled"
            else
                print_error "Docker daemon required"
                exit 1
            fi
        fi
    else
        print_warning "Docker not installed"

        if [ "$CURRENT_PLATFORM" = "macos" ]; then
            print_error "Please install Docker Desktop for macOS: https://docs.docker.com/desktop/install/mac-install/"
            exit 1
        elif [ "$CURRENT_PLATFORM" = "wsl" ]; then
            print_error "Please install Docker Desktop for Windows: https://docs.docker.com/desktop/install/windows-install/"
            exit 1
        fi

        if confirm_prompt "Install Docker now?"; then
            install_docker_linux
        else
            print_error "Docker is required"
            exit 1
        fi
    fi

    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' | head -1)
        print_success "Docker Compose plugin ($compose_version)"
        USE_STANDALONE_COMPOSE=false
    elif command_exists docker-compose; then
        local compose_version=$(docker-compose version 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' | head -1)
        print_success "Docker Compose standalone ($compose_version)"
        USE_STANDALONE_COMPOSE=true
    else
        print_error "Docker Compose not installed"
        exit 1
    fi

    # Check sudo requirement
    if docker ps >/dev/null 2>&1; then
        DOCKER_SUDO=""
    else
        DOCKER_SUDO="sudo"
        print_info "Docker commands will use sudo"
    fi

    # Detect Docker socket group ID for container access
    if [ -S /var/run/docker.sock ]; then
        DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || stat -f '%g' /var/run/docker.sock 2>/dev/null || echo "999")
        print_success "Docker socket group ID: $DOCKER_GID"
    else
        DOCKER_GID="999"
        print_warning "Docker socket not found, using default GID 999"
    fi
}

install_docker_linux() {
    print_info "Installing Docker..."

    local distro="${DISTRO:-}"
    if [ -z "$distro" ]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            distro=$ID
        fi
    fi

    case $distro in
        ubuntu|debian|raspbian)
            run_privileged apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
            run_privileged apt-get update
            run_privileged apt-get install -y ca-certificates curl gnupg lsb-release
            run_privileged install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/$distro/gpg | run_privileged gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            run_privileged chmod a+r /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$distro $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | run_privileged tee /etc/apt/sources.list.d/docker.list > /dev/null
            run_privileged apt-get update
            run_privileged apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        *)
            print_error "Unsupported distribution: $distro"
            print_info "Install Docker manually: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac

    run_privileged systemctl start docker
    run_privileged systemctl enable docker

    if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
        run_privileged usermod -aG docker "$REAL_USER"
        print_warning "Added $REAL_USER to docker group. Log out and back in to apply."
    fi

    print_success "Docker installed!"
}

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

perform_system_checks() {
    print_section "System Requirements Check"

    local checks_failed=false

    # Detect platform for platform-specific checks
    local CHECK_PLATFORM=""
    if [ "$(uname)" = "Darwin" ]; then
        CHECK_PLATFORM="macos"
    else
        CHECK_PLATFORM="linux"
    fi

    # Memory check (in GB)
    local total_memory=""
    if [ "$CHECK_PLATFORM" = "macos" ]; then
        total_memory=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1024/1024/1024}')
    else
        total_memory=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}')
    fi
    if [ -n "$total_memory" ] && [ "$total_memory" -gt 0 ]; then
        if [ "$total_memory" -ge 1 ]; then
            print_success "Memory: ${total_memory}GB"
        else
            print_warning "Memory: ${total_memory}GB (1GB+ recommended)"
            checks_failed=true
        fi
    else
        # Fallback to MB for systems with less than 1GB
        local mem_total_mb=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print int($2/1024)}')
        if [ -n "$mem_total_mb" ]; then
            if [ "$mem_total_mb" -ge 512 ]; then
                print_success "Memory: ${mem_total_mb}MB"
            else
                print_warning "Memory: ${mem_total_mb}MB (512MB+ recommended)"
                checks_failed=true
            fi
        fi
    fi

    # Disk check (in GB)
    local disk_avail=""
    if [ "$CHECK_PLATFORM" = "macos" ]; then
        disk_avail=$(df -g "${SCRIPT_DIR}" 2>/dev/null | tail -1 | awk '{print $4}')
    else
        disk_avail=$(df -BG "${SCRIPT_DIR}" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d 'G')
    fi
    if [ -n "$disk_avail" ]; then
        if [ "$disk_avail" -ge 5 ]; then
            print_success "Disk: ${disk_avail}GB available"
        else
            print_warning "Disk: ${disk_avail}GB available (5GB+ recommended)"
            checks_failed=true
        fi
    fi

    # Port 443 availability check
    local port_in_use=false
    if command_exists ss; then
        if ss -tulpn 2>/dev/null | grep -q ':443 '; then
            port_in_use=true
        fi
    elif command_exists netstat; then
        if netstat -tulpn 2>/dev/null | grep -q ':443 '; then
            port_in_use=true
        fi
    fi
    if [ "$port_in_use" = true ]; then
        print_warning "Port 443: Already in use (may conflict with nginx)"
        checks_failed=true
    else
        print_success "Port 443: Available"
    fi

    # OpenSSL check
    if command_exists openssl; then
        print_success "OpenSSL: Available"
    else
        print_warning "OpenSSL: Not found (required for SSL certificates)"
        checks_failed=true
    fi

    # Curl check
    if command_exists curl; then
        print_success "Curl: Available"
    else
        print_warning "Curl: Not found (required for downloads)"
        checks_failed=true
    fi

    # Network connectivity
    if ping -c 1 -W 3 8.8.8.8 >/dev/null 2>&1; then
        print_success "Network: OK"
    else
        print_warning "Network: Cannot reach external servers"
        checks_failed=true
    fi

    # Docker Hub connectivity
    if curl -s --connect-timeout 5 https://hub.docker.com >/dev/null 2>&1; then
        print_success "Docker Hub: Reachable"
    else
        print_warning "Docker Hub: Cannot reach (may affect image pulls)"
        checks_failed=true
    fi

    echo ""

    # Ask to continue if checks failed
    if [ "$checks_failed" = true ]; then
        print_warning "Some system checks failed"
        if ! confirm_prompt "Continue anyway?"; then
            print_error "Setup cancelled"
            exit 1
        fi
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

configure_domain() {
    print_section "Domain Configuration"

    # In preconfig mode, domain is already set by load_preconfig
    if [ "$PRECONFIG_MODE" = "true" ] && [ -n "$DOMAIN" ]; then
        print_info "Using pre-configured domain: $DOMAIN"
        return
    fi

    echo -e "  ${GRAY}Enter the domain name where GenMaster will be accessible.${NC}"
    echo -e "  ${GRAY}Example: genmaster.yourdomain.com${NC}"
    echo ""

    prompt_with_default "Enter your GenMaster domain" "genmaster.example.com" "DOMAIN"

    # Validate domain format
    if [[ ! "$DOMAIN" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$ ]]; then
        print_warning "Domain format may be invalid: $DOMAIN"
        if ! confirm_prompt "Continue anyway?"; then
            configure_domain
            return
        fi
    fi

    validate_domain
}

validate_domain() {
    print_subsection
    echo -e "${WHITE}  Validating domain configuration...${NC}"
    echo ""

    # Get local IP addresses
    local local_ips=$(get_local_ips)
    local domain_ip=""
    local validation_passed=true

    # Show local IPs
    echo -e "  ${WHITE}This server's IP addresses:${NC}"
    for local_ip in $local_ips; do
        echo -e "    ${CYAN}${local_ip}${NC}"
    done
    echo ""

    # Try to resolve the domain
    print_info "Resolving $DOMAIN..."

    if command_exists dig; then
        domain_ip=$(dig +short "$DOMAIN" 2>/dev/null | head -1)
    elif command_exists nslookup; then
        domain_ip=$(nslookup "$DOMAIN" 2>/dev/null | grep -A1 "Name:" | grep "Address:" | awk '{print $2}' | head -1)
    elif command_exists host; then
        domain_ip=$(host "$DOMAIN" 2>/dev/null | grep "has address" | awk '{print $4}' | head -1)
    elif command_exists getent; then
        domain_ip=$(getent hosts "$DOMAIN" 2>/dev/null | awk '{print $1}' | head -1)
    fi

    if [ -z "$domain_ip" ]; then
        print_warning "Could not resolve $DOMAIN to an IP address"
        echo ""
        echo -e "  ${YELLOW}This could mean:${NC}"
        echo -e "    - The DNS record hasn't been created yet"
        echo -e "    - The DNS hasn't propagated yet"
        echo -e "    - The domain name is incorrect"
        echo ""
        validation_passed=false
    else
        print_success "Domain resolves to: $domain_ip"

        # Test connectivity to resolved IP
        print_info "Testing connectivity to $domain_ip..."
        if ping -c 1 -W 5 "$domain_ip" >/dev/null 2>&1; then
            print_success "Host $domain_ip is reachable"
        else
            print_warning "Cannot ping $domain_ip (may be blocked by firewall)"
        fi

        # Check if the resolved IP matches any local IP
        local ip_matches=false
        local matched_local_ip=""
        for local_ip in $local_ips; do
            if [ "$local_ip" = "$domain_ip" ]; then
                ip_matches=true
                matched_local_ip="$local_ip"
                break
            fi
        done

        if [ "$ip_matches" = true ]; then
            print_success "Domain IP matches this server ($matched_local_ip)"
        else
            print_warning "Domain IP ($domain_ip) does not match any local IP"
            echo ""
            echo -e "  ${YELLOW}IMPORTANT:${NC}"
            echo -e "  ${YELLOW}The domain $DOMAIN points to $domain_ip${NC}"
            echo -e "  ${YELLOW}but this server's IPs are different.${NC}"
            echo ""
            echo -e "  ${YELLOW}This may cause issues unless you are using:${NC}"
            echo -e "    - Cloudflare Tunnel (routes traffic through Cloudflare)"
            echo -e "    - Tailscale (uses Tailscale's private network)"
            echo -e "    - A reverse proxy or load balancer"
            echo ""
            validation_passed=false
        fi
    fi

    if [ "$validation_passed" = false ]; then
        echo ""
        if ! confirm_prompt "Continue with this domain configuration anyway?"; then
            configure_domain
            return
        fi
    fi

    print_success "Domain configuration complete: $DOMAIN"
}

configure_database() {
    print_section "Database Configuration"

    if [ "$PRECONFIG_MODE" = "true" ]; then
        print_info "Using database: $DB_NAME"
        return
    fi

    echo ""
    echo -e "  ${GRAY}Configure PostgreSQL settings. Press Enter for defaults.${NC}"
    echo ""

    prompt_with_default "Database name" "$DEFAULT_DB_NAME" "DB_NAME"
    prompt_with_default "Database user" "$DEFAULT_DB_USER" "DB_USER"

    if [ -z "$DB_PASSWORD" ]; then
        if confirm_prompt "Auto-generate database password?" "y"; then
            DB_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
            AUTOGEN_DB_PASSWORD=true
            print_success "Password generated"
        else
            while true; do
                echo -ne "${WHITE}  Password${NC}: "
                read -s DB_PASSWORD
                echo ""
                if [ ${#DB_PASSWORD} -ge 8 ]; then
                    break
                fi
                print_error "Password must be at least 8 characters"
            done
        fi
    fi

    print_success "Database configured"
}

configure_admin_user() {
    print_section "Admin User Configuration"

    if [ "$PRECONFIG_MODE" = "true" ] && [ -n "$ADMIN_PASSWORD" ]; then
        print_info "Admin user: $ADMIN_USERNAME"
        return
    fi

    echo ""
    echo -e "  ${GRAY}Configure the initial admin user for the web interface.${NC}"
    echo ""

    prompt_with_default "Admin username" "$ADMIN_USERNAME" "ADMIN_USERNAME"

    if [ -z "$ADMIN_PASSWORD" ]; then
        if confirm_prompt "Auto-generate admin password?" "n"; then
            ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 16)
            AUTOGEN_ADMIN_PASSWORD=true
            print_success "Admin password generated"
        else
            while true; do
                echo -ne "${WHITE}  Admin password${NC}: "
                read -s ADMIN_PASSWORD
                echo ""

                if [ ${#ADMIN_PASSWORD} -lt 8 ]; then
                    print_error "Password must be at least 8 characters"
                    continue
                fi

                echo -ne "${WHITE}  Confirm password${NC}: "
                read -s admin_pass_confirm
                echo ""

                if [ "$ADMIN_PASSWORD" != "$admin_pass_confirm" ]; then
                    print_error "Passwords do not match"
                    continue
                fi

                break
            done
        fi
    fi

    print_success "Admin user configured: $ADMIN_USERNAME"
}

configure_containers() {
    print_section "Container Names"

    POSTGRES_CONTAINER="$DEFAULT_POSTGRES_CONTAINER"
    GENMASTER_CONTAINER="$DEFAULT_GENMASTER_CONTAINER"
    NGINX_CONTAINER="$DEFAULT_NGINX_CONTAINER"
    REDIS_CONTAINER="$DEFAULT_REDIS_CONTAINER"

    print_info "Using default container names"
}

configure_build_method() {
    print_section "GenMaster Image Source"

    echo -e "  ${WHITE}Choose how to deploy the GenMaster application:${NC}"
    echo ""
    echo -e "    ${GREEN}1.${NC} Docker Hub image ${CYAN}(Recommended)${NC}"
    echo -e "       ${DIM}Pull pre-built image from rjsears/genmaster:latest${NC}"
    echo -e "       ${DIM}Faster deployment (~30 seconds), no build tools needed${NC}"
    echo ""
    echo -e "    ${WHITE}2.${NC} Build locally"
    echo -e "       ${DIM}Build from source code in this directory${NC}"
    echo -e "       ${DIM}Slower (~5-7 minutes), requires more resources${NC}"
    echo ""

    if [ "$PRECONFIG_MODE" = "true" ] && [ -n "$USE_DOCKER_HUB_IMAGE" ]; then
        if [ "$USE_DOCKER_HUB_IMAGE" = true ]; then
            print_info "Using pre-configured setting: Docker Hub image"
        else
            print_info "Using pre-configured setting: Build locally"
        fi
        return
    fi

    local choice
    echo -ne "  ${WHITE}Select option [1]: ${NC}"
    read choice

    case "$choice" in
        2)
            USE_DOCKER_HUB_IMAGE=false
            print_success "Will build GenMaster locally from source"
            ;;
        *)
            USE_DOCKER_HUB_IMAGE=true
            print_success "Will pull GenMaster from Docker Hub (${DOCKER_HUB_IMAGE})"
            ;;
    esac
}

configure_timezone() {
    print_section "Timezone Configuration"

    # In preconfig mode, timezone is already set by load_preconfig
    if [ "$PRECONFIG_MODE" = "true" ] && [ -n "$TIMEZONE" ]; then
        print_info "Using pre-configured timezone: $TIMEZONE"
        return
    fi

    local default_tz="America/Los_Angeles"
    local system_tz=""

    # Detect system timezone for reference
    if [ -f /etc/timezone ]; then
        system_tz=$(cat /etc/timezone)
    elif command_exists timedatectl; then
        system_tz=$(timedatectl show -p Timezone --value 2>/dev/null)
    fi

    if [ -n "$system_tz" ] && [ "$system_tz" != "$default_tz" ]; then
        echo -e "  ${WHITE}System timezone detected: ${CYAN}$system_tz${NC}"
        echo ""
    fi

    if confirm_prompt "Use $default_tz as the timezone?" "y"; then
        TIMEZONE="$default_tz"
    else
        local tz_suggestion="${system_tz:-$default_tz}"
        prompt_with_default "Timezone" "$tz_suggestion" "TIMEZONE"
    fi

    print_success "Timezone set to: $TIMEZONE"

    # Set the docker host's timezone to match
    if confirm_prompt "Set docker host timezone to match ($TIMEZONE)?" "y"; then
        set_host_timezone "$TIMEZONE"
    fi
}

set_host_timezone() {
    local timezone="$1"
    local tz_file="/usr/share/zoneinfo/$timezone"

    # Check if timezone file exists
    if [ ! -f "$tz_file" ]; then
        print_warning "Timezone file not found: $tz_file"
        print_warning "Host timezone will remain unchanged"
        return 1
    fi

    print_info "Setting host timezone to: $timezone"

    # Set timezone using timedatectl if available (preferred method)
    if command_exists timedatectl; then
        if run_privileged timedatectl set-timezone "$timezone" 2>/dev/null; then
            print_success "Host timezone updated using timedatectl"
            return 0
        else
            print_warning "timedatectl failed, trying alternative method..."
        fi
    fi

    # Fallback: symlink method
    if run_privileged ln -sf "$tz_file" /etc/localtime 2>/dev/null; then
        echo "$timezone" | run_privileged tee /etc/timezone > /dev/null 2>&1
        print_success "Host timezone updated via symlink"
        return 0
    fi

    print_warning "Could not set host timezone"
    return 1
}

generate_secret_key() {
    print_section "Application Secret Key"

    if [ -n "$SECRET_KEY" ]; then
        print_info "Secret key already set"
        return
    fi

    SECRET_KEY=$(openssl rand -base64 48 | tr -dc 'a-zA-Z0-9' | head -c 64)
    AUTOGEN_SECRET_KEY=true
    print_success "Secret key generated"
}

configure_genslave() {
    print_section "GenSlave Configuration"

    # In PRECONFIG_MODE, show existing config and API secret, then return
    if [ "$PRECONFIG_MODE" = "true" ]; then
        if [ "$GENSLAVE_ENABLED" = "true" ]; then
            print_info "GenSlave: $GENSLAVE_API_URL"
            # Always show the API secret so user can copy it
            if [ -n "$GENSLAVE_API_SECRET" ]; then
                echo ""
                echo -e "  ${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
                echo -e "  ${GREEN}║${NC}  ${WHITE}IMPORTANT: Copy this API secret for GenSlave setup!${NC}           ${GREEN}║${NC}"
                echo -e "  ${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
                echo -e "  ${GREEN}║${NC}                                                                ${GREEN}║${NC}"
                echo -e "  ${GREEN}║${NC}  ${CYAN}SLAVE_API_SECRET=${GENSLAVE_API_SECRET}${NC}  ${GREEN}║${NC}"
                echo -e "  ${GREEN}║${NC}                                                                ${GREEN}║${NC}"
                echo -e "  ${GREEN}║${NC}  ${GRAY}You will need this when running GenSlave setup.${NC}              ${GREEN}║${NC}"
                echo -e "  ${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
                echo ""
            fi
        else
            print_info "GenSlave: Disabled"
        fi
        return
    fi

    echo ""
    echo -e "  ${GRAY}GenSlave controls the generator relay on a Pi Zero 2W.${NC}"
    echo -e "  ${GRAY}It runs on a separate device and communicates with GenMaster via API.${NC}"
    echo ""

    if confirm_prompt "Enable GenSlave communication?" "y"; then
        GENSLAVE_ENABLED=true

        # Get GenSlave IP address
        echo ""
        echo -e "  ${WHITE}GenSlave Network Configuration${NC}"
        echo -e "  ${GRAY}Enter the IP address of your GenSlave Pi Zero 2W.${NC}"
        echo ""

        local input_ip=""

        echo -ne "${WHITE}  GenSlave IP address (e.g., 192.168.1.100)${NC}: "
        read input_ip

        if [ -n "$input_ip" ]; then
            # Save to global variables for .env and docker-compose
            GENSLAVE_IP="$input_ip"
            GENSLAVE_HOSTNAME="genslave"

            # Set default URL based on IP
            GENSLAVE_API_URL="http://${input_ip}:8001"
            print_info "GenSlave API URL set to: ${GENSLAVE_API_URL}"
        else
            print_warning "No IP provided - you'll need to set SLAVE_API_URL manually in .env"
        fi

        echo ""

        # Allow URL override if needed
        if [ -n "$GENSLAVE_API_URL" ]; then
            if confirm_prompt "Use ${GENSLAVE_API_URL} as the API URL?" "y"; then
                : # Keep the URL as-is
            else
                echo -ne "${WHITE}  Enter custom GenSlave API URL${NC}: "
                read custom_url
                if [ -n "$custom_url" ]; then
                    GENSLAVE_API_URL="$custom_url"
                fi
            fi
        fi

        # Generate API secret if not already set
        if [ -z "$GENSLAVE_API_SECRET" ]; then
            GENSLAVE_API_SECRET=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
            AUTOGEN_SLAVE_SECRET=true
        fi

        # Show the API secret prominently - user needs this for GenSlave setup
        echo ""
        echo -e "  ${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "  ${GREEN}║${NC}  ${WHITE}IMPORTANT: Copy this API secret for GenSlave setup!${NC}           ${GREEN}║${NC}"
        echo -e "  ${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
        echo -e "  ${GREEN}║${NC}                                                                ${GREEN}║${NC}"
        echo -e "  ${GREEN}║${NC}  ${CYAN}SLAVE_API_SECRET=${GENSLAVE_API_SECRET}${NC}  ${GREEN}║${NC}"
        echo -e "  ${GREEN}║${NC}                                                                ${GREEN}║${NC}"
        echo -e "  ${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "  ${YELLOW}If GenSlave is not yet configured:${NC}"
        echo -e "  ${WHITE}1.${NC} Copy the API secret above"
        echo -e "  ${WHITE}2.${NC} Run GenSlave setup on your Pi Zero 2W"
        echo -e "  ${WHITE}3.${NC} Enter this API secret when prompted during GenSlave setup"
        echo ""
        echo -e "  ${YELLOW}If GenSlave is already running and you changed the API key:${NC}"
        echo -e "  ${WHITE}1.${NC} Update API_SECRET in GenSlave's .env file"
        echo -e "  ${WHITE}2.${NC} Run: ${CYAN}docker-compose up -d --force-recreate genslave${NC}"
        echo ""
        echo -ne "  ${WHITE}Press Enter when GenSlave is configured and running to test the connection...${NC}"
        read -r
        echo ""

        # Test the connection
        print_info "Testing connection to GenSlave..."
        validate_genslave

        # Auto-Arm Configuration
        echo ""
        echo -e "  ${WHITE}Auto-Arm Configuration${NC}"
        echo -e "  ${GRAY}When enabled, the GenSlave relay will automatically be armed${NC}"
        echo -e "  ${GRAY}whenever communication is restored after a disconnection.${NC}"
        echo -e "  ${GRAY}This will NOT override a manual disarm from the UI.${NC}"
        echo ""

        if confirm_prompt "Enable auto-arm relay on connection restore?" "n"; then
            AUTO_ARM_RELAY_ON_CONNECT=true
            print_success "Auto-arm on connection restore enabled"
        else
            AUTO_ARM_RELAY_ON_CONNECT=false
            print_info "Auto-arm on connection restore disabled"
        fi

        print_success "GenSlave configured"
    else
        GENSLAVE_ENABLED=false
        AUTO_ARM_RELAY_ON_CONNECT=false
        print_info "GenSlave disabled (UI-only mode)"
    fi
}

validate_genslave() {
    print_subsection
    echo -e "${WHITE}  Validating GenSlave connection...${NC}"
    echo ""

    local validation_passed=true

    # Extract host from URL for connectivity test
    local genslave_host=$(echo "$GENSLAVE_API_URL" | sed -E 's|https?://||' | cut -d':' -f1 | cut -d'/' -f1)
    local genslave_port=$(echo "$GENSLAVE_API_URL" | sed -E 's|https?://[^:]+:?||' | cut -d'/' -f1)
    genslave_port="${genslave_port:-8001}"

    print_info "GenSlave host: $genslave_host"
    print_info "GenSlave port: $genslave_port"
    echo ""

    # Test DNS resolution / hostname
    print_info "Resolving $genslave_host..."
    local genslave_ip=""
    if command_exists dig; then
        genslave_ip=$(dig +short "$genslave_host" 2>/dev/null | head -1)
    elif command_exists getent; then
        genslave_ip=$(getent hosts "$genslave_host" 2>/dev/null | awk '{print $1}' | head -1)
    elif command_exists host; then
        genslave_ip=$(host "$genslave_host" 2>/dev/null | grep "has address" | awk '{print $4}' | head -1)
    fi

    # If no DNS resolution, maybe it's already an IP
    if [ -z "$genslave_ip" ]; then
        if [[ "$genslave_host" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            genslave_ip="$genslave_host"
            print_success "Using IP address directly: $genslave_ip"
        else
            print_warning "Could not resolve $genslave_host"
            validation_passed=false
        fi
    else
        print_success "Resolved to: $genslave_ip"
    fi

    # Test ping connectivity
    if [ -n "$genslave_ip" ]; then
        print_info "Testing connectivity to $genslave_ip..."
        if ping -c 1 -W 5 "$genslave_ip" >/dev/null 2>&1; then
            print_success "Host $genslave_ip is reachable"
        else
            print_warning "Cannot ping $genslave_ip (may be blocked by firewall)"
        fi
    fi

    # Test TCP port connectivity
    print_info "Testing port $genslave_port..."
    if command_exists nc; then
        if nc -z -w 5 "$genslave_host" "$genslave_port" 2>/dev/null; then
            print_success "Port $genslave_port is open"
        else
            print_warning "Port $genslave_port is not responding"
            validation_passed=false
        fi
    elif command_exists timeout; then
        if timeout 5 bash -c "echo >/dev/tcp/$genslave_host/$genslave_port" 2>/dev/null; then
            print_success "Port $genslave_port is open"
        else
            print_warning "Port $genslave_port is not responding"
            validation_passed=false
        fi
    fi

    # Test API health endpoint with API key (with retries)
    print_info "Testing GenSlave API health..."
    local health_url="${GENSLAVE_API_URL}/api/health"
    local health_response=""
    local max_attempts=3
    local retry_delay=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        health_response=$(curl -s --connect-timeout 10 --max-time 15 \
            -H "X-API-Key: ${GENSLAVE_API_SECRET}" \
            "$health_url" 2>/dev/null || true)

        if [ -n "$health_response" ]; then
            print_success "GenSlave API is responding"
            echo -e "    ${GRAY}Response: ${health_response:0:100}${NC}"
            break
        else
            if [ $attempt -lt $max_attempts ]; then
                print_warning "GenSlave not responding yet (attempt $attempt/$max_attempts)"
                echo -e "    ${GRAY}GenSlave may still be starting, retrying in ${retry_delay} seconds...${NC}"
                sleep $retry_delay
            else
                print_warning "GenSlave API is not responding at $health_url"
                validation_passed=false
            fi
        fi
        attempt=$((attempt + 1))
    done

    echo ""

    if [ "$validation_passed" = false ]; then
        print_warning "GenSlave validation had issues"
        echo ""
        echo -e "  ${YELLOW}Possible causes:${NC}"
        echo -e "    - GenSlave is not running yet"
        echo -e "    - Firewall blocking the connection"
        echo -e "    - Incorrect URL or port"
        echo -e "    - Network connectivity issues"
        echo ""
        if ! confirm_prompt "Continue with this GenSlave configuration anyway?"; then
            configure_genslave
            return
        fi
    else
        print_success "GenSlave validation passed!"
    fi
}

configure_webhooks() {
    print_section "Webhooks"

    if [ "$PRECONFIG_MODE" = "true" ]; then
        if [ -n "$WEBHOOK_URL" ]; then
            print_info "Webhook: $WEBHOOK_URL"
        else
            print_info "Webhooks: Not configured"
        fi
        return
    fi

    echo ""
    echo -e "  ${GRAY}Webhooks notify external services of generator events.${NC}"
    echo ""

    if confirm_prompt "Configure webhooks?" "n"; then
        echo -ne "${WHITE}  Webhook URL${NC}: "
        read WEBHOOK_URL

        if [ -n "$WEBHOOK_URL" ]; then
            WEBHOOK_SECRET=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
            print_success "Webhook configured"
        fi
    else
        print_info "Webhooks skipped"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# GENERATOR INFORMATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Global variables for generator info
GEN_INFO_MANUFACTURER=""
GEN_INFO_MODEL_NUMBER=""
GEN_INFO_SERIAL_NUMBER=""
GEN_INFO_FUEL_TYPE=""
GEN_INFO_LOAD_EXPECTED=""
GEN_INFO_FUEL_CONSUMPTION_50=""
GEN_INFO_FUEL_CONSUMPTION_100=""

configure_generator_info() {
    print_section "Generator Information"

    local gen_info_file="${SCRIPT_DIR}/setup/gen_info.json"

    # Check if pre-configured file exists
    if [ -f "$gen_info_file" ]; then
        print_info "Found generator info configuration file"

        # Parse JSON file using grep/sed (portable, no jq required)
        GEN_INFO_MANUFACTURER=$(grep -o '"manufacturer"[[:space:]]*:[[:space:]]*"[^"]*"' "$gen_info_file" | sed 's/.*: *"\([^"]*\)"/\1/')
        GEN_INFO_MODEL_NUMBER=$(grep -o '"model_number"[[:space:]]*:[[:space:]]*"[^"]*"' "$gen_info_file" | sed 's/.*: *"\([^"]*\)"/\1/')
        GEN_INFO_SERIAL_NUMBER=$(grep -o '"serial_number"[[:space:]]*:[[:space:]]*"[^"]*"' "$gen_info_file" | sed 's/.*: *"\([^"]*\)"/\1/')
        GEN_INFO_FUEL_TYPE=$(grep -o '"fuel_type"[[:space:]]*:[[:space:]]*"[^"]*"' "$gen_info_file" | sed 's/.*: *"\([^"]*\)"/\1/')
        GEN_INFO_LOAD_EXPECTED=$(grep -o '"load_expected"[[:space:]]*:[[:space:]]*[0-9]*' "$gen_info_file" | sed 's/.*: *//')
        GEN_INFO_FUEL_CONSUMPTION_50=$(grep -o '"fuel_consumption_50"[[:space:]]*:[[:space:]]*[0-9.]*' "$gen_info_file" | sed 's/.*: *//')
        GEN_INFO_FUEL_CONSUMPTION_100=$(grep -o '"fuel_consumption_100"[[:space:]]*:[[:space:]]*[0-9.]*' "$gen_info_file" | sed 's/.*: *//')

        echo ""
        echo -e "  ${WHITE}Generator Information from config file:${NC}"
        echo -e "    Manufacturer:        ${CYAN}${GEN_INFO_MANUFACTURER:-Not set}${NC}"
        echo -e "    Model Number:        ${CYAN}${GEN_INFO_MODEL_NUMBER:-Not set}${NC}"
        echo -e "    Serial Number:       ${CYAN}${GEN_INFO_SERIAL_NUMBER:-Not set}${NC}"
        echo -e "    Fuel Type:           ${CYAN}${GEN_INFO_FUEL_TYPE:-Not set}${NC}"
        echo -e "    Expected Load:       ${CYAN}${GEN_INFO_LOAD_EXPECTED:-Not set}%${NC}"
        echo -e "    Consumption @ 50%:   ${CYAN}${GEN_INFO_FUEL_CONSUMPTION_50:-Not set} gal/hr${NC}"
        echo -e "    Consumption @ 100%:  ${CYAN}${GEN_INFO_FUEL_CONSUMPTION_100:-Not set} gal/hr${NC}"
        echo ""

        if [ "$PRECONFIG_MODE" = "true" ]; then
            print_info "Using pre-configured generator information"
            return
        fi

        if confirm_prompt "Use this generator information?" "y"; then
            print_success "Generator information configured"
            return
        fi
    fi

    if [ "$PRECONFIG_MODE" = "true" ]; then
        print_info "Generator info: Not pre-configured (can be set in UI)"
        return
    fi

    echo ""
    echo -e "  ${GRAY}Enter your generator details for fuel tracking and identification.${NC}"
    echo -e "  ${GRAY}All fields are optional - you can configure them later in the UI.${NC}"
    echo ""

    if confirm_prompt "Configure generator information now?" "n"; then
        echo ""
        echo -ne "${WHITE}  Manufacturer (e.g., Generac)${NC}: "
        read GEN_INFO_MANUFACTURER

        echo -ne "${WHITE}  Model Number (e.g., 7043)${NC}: "
        read GEN_INFO_MODEL_NUMBER

        echo -ne "${WHITE}  Serial Number${NC}: "
        read GEN_INFO_SERIAL_NUMBER

        echo ""
        echo -e "  ${WHITE}Fuel Type:${NC}"
        echo -e "    ${CYAN}1)${NC} LPG (Propane)"
        echo -e "    ${CYAN}2)${NC} Natural Gas"
        echo -e "    ${CYAN}3)${NC} Diesel"
        echo ""

        local fuel_choice=""
        echo -ne "${WHITE}  Enter fuel type [1-3]${NC}: "
        read fuel_choice
        case "$fuel_choice" in
            1) GEN_INFO_FUEL_TYPE="lpg" ;;
            2) GEN_INFO_FUEL_TYPE="natural_gas" ;;
            3) GEN_INFO_FUEL_TYPE="diesel" ;;
            *) GEN_INFO_FUEL_TYPE="" ;;
        esac

        echo ""
        echo -e "  ${WHITE}Expected Load:${NC}"
        echo -e "    ${CYAN}1)${NC} 50%"
        echo -e "    ${CYAN}2)${NC} 100%"
        echo ""

        local load_choice=""
        echo -ne "${WHITE}  Enter expected load [1-2]${NC}: "
        read load_choice
        case "$load_choice" in
            1) GEN_INFO_LOAD_EXPECTED="50" ;;
            2) GEN_INFO_LOAD_EXPECTED="100" ;;
            *) GEN_INFO_LOAD_EXPECTED="" ;;
        esac

        echo ""
        echo -e "  ${GRAY}Enter fuel consumption rates from your generator specifications.${NC}"
        echo ""

        echo -ne "${WHITE}  Fuel consumption at 50% load (gal/hr)${NC}: "
        read GEN_INFO_FUEL_CONSUMPTION_50

        echo -ne "${WHITE}  Fuel consumption at 100% load (gal/hr)${NC}: "
        read GEN_INFO_FUEL_CONSUMPTION_100

        print_success "Generator information configured"
    else
        print_info "Generator info skipped (can be configured in UI)"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DNS PROVIDER CONFIGURATION (for Let's Encrypt SSL)
# ═══════════════════════════════════════════════════════════════════════════════

configure_dns_provider() {
    print_section "DNS Provider Configuration"

    if [ "$PRECONFIG_MODE" = "true" ]; then
        print_info "Using pre-configured DNS provider: $DNS_PROVIDER_NAME"
        return
    fi

    echo -e "  ${GRAY}Let's Encrypt uses DNS validation to issue SSL certificates.${NC}"
    echo -e "  ${GRAY}This requires API access to your DNS provider.${NC}"
    echo ""

    echo -e "  ${WHITE}Select your DNS provider:${NC}"
    echo -e "    ${CYAN}1)${NC} Cloudflare"
    echo -e "    ${CYAN}2)${NC} AWS Route 53"
    echo -e "    ${CYAN}3)${NC} Google Cloud DNS"
    echo -e "    ${CYAN}4)${NC} DigitalOcean"
    echo -e "    ${CYAN}5)${NC} Other (manual configuration)"
    echo ""

    local dns_choice=""
    while [[ ! "$dns_choice" =~ ^[1-5]$ ]]; do
        echo -ne "${WHITE}  Enter your choice [1-5]${NC}: "
        read dns_choice
    done

    case $dns_choice in
        1) configure_cloudflare_dns ;;
        2) configure_route53 ;;
        3) configure_google_dns ;;
        4) configure_digitalocean ;;
        5) configure_other_dns ;;
    esac
}

configure_cloudflare_dns() {
    DNS_PROVIDER_NAME="cloudflare"
    DNS_CERTBOT_IMAGE="certbot/dns-cloudflare:latest"
    DNS_CREDENTIALS_FILE="cloudflare.ini"

    print_subsection
    echo -e "${WHITE}  Cloudflare API Configuration${NC}"
    echo ""
    echo -e "  ${GRAY}You need a Cloudflare API token with Zone:DNS:Edit permission.${NC}"
    echo -e "  ${GRAY}Create one at: https://dash.cloudflare.com/profile/api-tokens${NC}"
    echo ""

    echo -ne "${WHITE}  Enter your Cloudflare API token${NC}: "
    read_masked_token
    CF_API_TOKEN="$MASKED_INPUT"

    if [ -z "$CF_API_TOKEN" ]; then
        print_error "API token is required for Cloudflare"
        exit 1
    fi

    print_success "Cloudflare credentials saved"

    mkdir -p "${SCRIPT_DIR}/certbot"
    cat > "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}" << EOF
dns_cloudflare_api_token = ${CF_API_TOKEN}
EOF

    chmod 600 "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}"

    DNS_CERTBOT_FLAGS="--dns-cloudflare --dns-cloudflare-credentials /etc/letsencrypt/${DNS_CREDENTIALS_FILE} --dns-cloudflare-propagation-seconds 60"
}

configure_route53() {
    DNS_PROVIDER_NAME="route53"
    DNS_CERTBOT_IMAGE="certbot/dns-route53:latest"
    DNS_CREDENTIALS_FILE="route53.ini"

    print_subsection
    echo -e "${WHITE}  AWS Route 53 Configuration${NC}"
    echo ""
    echo -e "  ${GRAY}You need AWS credentials with Route 53 permissions.${NC}"
    echo ""

    echo -ne "${WHITE}  Enter your AWS Access Key ID${NC}: "
    read_masked_token
    AWS_ACCESS_KEY_ID="$MASKED_INPUT"

    echo -ne "${WHITE}  Enter your AWS Secret Access Key${NC}: "
    read_masked_token
    AWS_SECRET_ACCESS_KEY="$MASKED_INPUT"

    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        print_error "Both AWS credentials are required"
        exit 1
    fi

    print_success "AWS credentials saved"

    mkdir -p "${SCRIPT_DIR}/certbot"
    cat > "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}" << EOF
[default]
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}
EOF

    chmod 600 "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}"

    DNS_CERTBOT_FLAGS="--dns-route53"
}

configure_google_dns() {
    DNS_PROVIDER_NAME="google"
    DNS_CERTBOT_IMAGE="certbot/dns-google:latest"
    DNS_CREDENTIALS_FILE="google.json"

    print_subsection
    echo -e "${WHITE}  Google Cloud DNS Configuration${NC}"
    echo ""
    echo -e "  ${GRAY}You need a service account JSON file with DNS permissions.${NC}"
    echo ""

    echo -ne "${WHITE}  Enter the path to your service account JSON file${NC}: "
    read GOOGLE_JSON_PATH

    if [ ! -f "$GOOGLE_JSON_PATH" ]; then
        print_error "File not found: $GOOGLE_JSON_PATH"
        exit 1
    fi

    mkdir -p "${SCRIPT_DIR}/certbot"
    cp "$GOOGLE_JSON_PATH" "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}"
    chmod 600 "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}"
    print_success "Google credentials saved"

    DNS_CERTBOT_FLAGS="--dns-google --dns-google-credentials /etc/letsencrypt/${DNS_CREDENTIALS_FILE} --dns-google-propagation-seconds 120"
}

configure_digitalocean() {
    DNS_PROVIDER_NAME="digitalocean"
    DNS_CERTBOT_IMAGE="certbot/dns-digitalocean:latest"
    DNS_CREDENTIALS_FILE="digitalocean.ini"

    print_subsection
    echo -e "${WHITE}  DigitalOcean DNS Configuration${NC}"
    echo ""
    echo -e "  ${GRAY}You need a DigitalOcean API token with DNS permissions.${NC}"
    echo ""

    echo -ne "${WHITE}  Enter your DigitalOcean API token${NC}: "
    read_masked_token
    DO_API_TOKEN="$MASKED_INPUT"

    if [ -z "$DO_API_TOKEN" ]; then
        print_error "API token is required"
        exit 1
    fi

    print_success "DigitalOcean credentials saved"

    mkdir -p "${SCRIPT_DIR}/certbot"
    cat > "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}" << EOF
dns_digitalocean_token = ${DO_API_TOKEN}
EOF

    chmod 600 "${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}"

    DNS_CERTBOT_FLAGS="--dns-digitalocean --dns-digitalocean-credentials /etc/letsencrypt/${DNS_CREDENTIALS_FILE} --dns-digitalocean-propagation-seconds 60"
}

configure_other_dns() {
    DNS_PROVIDER_NAME="manual"
    DNS_CERTBOT_IMAGE="certbot/certbot:latest"
    DNS_CREDENTIALS_FILE=""
    DNS_CERTBOT_FLAGS="--manual --preferred-challenges dns"

    print_warning "Manual DNS configuration selected"
    echo -e "  ${GRAY}You will need to manually add DNS TXT records when prompted.${NC}"
    echo -e "  ${GRAY}This requires interactive certificate generation.${NC}"
}

configure_email() {
    print_section "Let's Encrypt Email Configuration"

    if [ "$PRECONFIG_MODE" = "true" ] && [ -n "$LETSENCRYPT_EMAIL" ]; then
        print_info "Using pre-configured email: $LETSENCRYPT_EMAIL"
        return
    fi

    echo ""
    echo -e "  ${GRAY}Let's Encrypt requires a valid email for certificate expiration notices.${NC}"
    echo ""

    while true; do
        echo -ne "${WHITE}  Email address for Let's Encrypt${NC}: "
        read email_input

        if [ -z "$email_input" ]; then
            print_error "Email address is required"
            continue
        fi

        # Basic email format validation
        if [[ ! "$email_input" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
            print_error "Invalid email format. Please enter a valid email address."
            continue
        fi

        # Check for placeholder emails
        if [[ "$email_input" =~ (example\.com|yourdomain\.com|test\.com|domain\.com)$ ]]; then
            print_warning "This looks like a placeholder email address."
            if ! confirm_prompt "Are you sure you want to use '$email_input'?" "n"; then
                continue
            fi
        fi

        # Confirm email address
        echo -ne "${WHITE}  Confirm email address${NC}: "
        read email_confirm

        if [ "$email_input" != "$email_confirm" ]; then
            print_error "Email addresses do not match. Please try again."
            continue
        fi

        LETSENCRYPT_EMAIL="$email_input"
        print_success "Email set to: $LETSENCRYPT_EMAIL"
        break
    done
}

# ═══════════════════════════════════════════════════════════════════════════════
# OPTIONAL SERVICES CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

configure_optional_services() {
    print_section "Optional Services"

    if [ "$PRECONFIG_MODE" = "true" ]; then
        print_info "Using pre-configured services"
        return
    fi

    # Cloudflare Tunnel
    echo ""
    # Show existing configuration status
    if [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ] && [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
        print_info "Cloudflare Tunnel: Currently ENABLED"
        if confirm_prompt "Reconfigure Cloudflare Tunnel?" "n"; then
            print_subsection
            echo -e "${WHITE}  Cloudflare Tunnel Configuration${NC}"
            echo ""
            echo -e "  ${GRAY}Cloudflare Tunnel provides secure access to your GenMaster instance${NC}"
            echo -e "  ${GRAY}without exposing any ports to the public internet.${NC}"
            echo ""
            echo -e "  ${YELLOW}Leave blank to keep existing token${NC}"
            echo ""

            echo -ne "${WHITE}  Enter your Cloudflare Tunnel token${NC}: "
            read_masked_token
            # Only update if new value provided
            if [ -n "$MASKED_INPUT" ]; then
                CLOUDFLARE_TUNNEL_TOKEN="$MASKED_INPUT"
                print_success "Cloudflare Tunnel token updated"
            else
                print_info "Keeping existing token"
            fi
        fi
        # If they said no to reconfigure, existing values are preserved
    else
        if confirm_prompt "Configure Cloudflare Tunnel for secure external access?" "n"; then
            print_subsection
            echo -e "${WHITE}  Cloudflare Tunnel Configuration${NC}"
            echo ""
            echo -e "  ${GRAY}Cloudflare Tunnel provides secure access to your GenMaster instance${NC}"
            echo -e "  ${GRAY}without exposing any ports to the public internet.${NC}"
            echo ""
            echo -e "  ${GRAY}Requirements:${NC}"
            echo -e "    • Cloudflare account with your domain"
            echo -e "    • Cloudflare Tunnel token from Zero Trust dashboard"
            echo ""
            echo -e "  ${GRAY}Create a tunnel at: https://one.dash.cloudflare.com${NC}"
            echo -e "  ${GRAY}Navigate to: Networks → Tunnels → Create a tunnel${NC}"
            echo ""

            echo -ne "${WHITE}  Enter your Cloudflare Tunnel token${NC}: "
            read_masked_token
            CLOUDFLARE_TUNNEL_TOKEN="$MASKED_INPUT"

            if [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ]; then
                INSTALL_CLOUDFLARE_TUNNEL=true
                print_success "Cloudflare Tunnel configured"
            else
                print_warning "No token provided - Cloudflare Tunnel disabled"
                INSTALL_CLOUDFLARE_TUNNEL=false
            fi
        fi
    fi

    # Tailscale
    echo ""
    # Show existing configuration status
    if [ "$INSTALL_TAILSCALE" = true ] && [ -n "$TAILSCALE_AUTH_KEY" ]; then
        print_info "Tailscale: Currently ENABLED (hostname: ${TAILSCALE_HOSTNAME:-genmaster})"
        if confirm_prompt "Reconfigure Tailscale?" "n"; then
            print_subsection
            echo -e "${WHITE}  Tailscale Configuration${NC}"
            echo ""
            echo -e "  ${GRAY}Tailscale provides private access to your GenMaster instance${NC}"
            echo -e "  ${GRAY}over a secure mesh VPN network.${NC}"
            echo ""
            echo -e "  ${GRAY}Requirements:${NC}"
            echo -e "    • Tailscale account"
            echo -e "    • Auth key from: https://login.tailscale.com/admin/settings/keys${NC}"
            echo ""
            echo -e "  ${YELLOW}Leave blank to keep existing auth key${NC}"
            echo ""

            echo -ne "${WHITE}  Enter your Tailscale auth key${NC}: "
            read_masked_token
            # Only update if new value provided
            if [ -n "$MASKED_INPUT" ]; then
                TAILSCALE_AUTH_KEY="$MASKED_INPUT"
                print_success "Auth key updated"
            else
                print_info "Keeping existing auth key"
            fi

            # Hostname - show current default
            echo ""
            echo -ne "${WHITE}  Tailscale hostname [${TAILSCALE_HOSTNAME:-genmaster}]${NC}: "
            read ts_hostname
            if [ -n "$ts_hostname" ]; then
                TAILSCALE_HOSTNAME="$ts_hostname"
            fi

            print_success "Tailscale configured"
            echo ""
            print_info "Your GenMaster instance will be accessible at: ${TAILSCALE_HOSTNAME}.your-tailnet.ts.net"
        fi
        # If they said no to reconfigure, existing values are preserved (no else needed)
    else
        if confirm_prompt "Configure Tailscale for private VPN access?" "n"; then
            print_subsection
            echo -e "${WHITE}  Tailscale Configuration${NC}"
            echo ""
            echo -e "  ${GRAY}Tailscale provides private access to your GenMaster instance${NC}"
            echo -e "  ${GRAY}over a secure mesh VPN network.${NC}"
            echo ""
            echo -e "  ${GRAY}Requirements:${NC}"
            echo -e "    • Tailscale account"
            echo -e "    • Auth key from: https://login.tailscale.com/admin/settings/keys${NC}"
            echo ""

            echo -ne "${WHITE}  Enter your Tailscale auth key${NC}: "
            read_masked_token
            TAILSCALE_AUTH_KEY="$MASKED_INPUT"

            if [ -n "$TAILSCALE_AUTH_KEY" ]; then
                INSTALL_TAILSCALE=true
                print_success "Auth key accepted"

                # Optional hostname
                echo ""
                echo -ne "${WHITE}  Tailscale hostname [genmaster]${NC}: "
                read ts_hostname
                TAILSCALE_HOSTNAME=${ts_hostname:-genmaster}

                print_success "Tailscale configured"
                echo ""
                print_info "Your GenMaster instance will be accessible at: ${TAILSCALE_HOSTNAME}.your-tailnet.ts.net"
            else
                print_warning "No auth key provided - Tailscale disabled"
                INSTALL_TAILSCALE=false
            fi
        fi
    fi

    # Portainer
    echo ""
    if confirm_prompt "Enable Portainer for container management?" "n"; then
        print_subsection
        echo -e "${WHITE}  Portainer Configuration${NC}"
        echo ""
        echo -e "  ${GRAY}Portainer provides a web-based interface for managing${NC}"
        echo -e "  ${GRAY}Docker containers, images, and volumes.${NC}"
        echo ""
        INSTALL_PORTAINER=true
        print_success "Portainer enabled"
    fi

    # WiFi Watchdog
    echo ""
    if confirm_prompt "Install WiFi Watchdog for connectivity monitoring?" "y"; then
        print_subsection
        echo -e "${WHITE}  WiFi Watchdog Configuration${NC}"
        echo ""
        echo -e "  ${GRAY}WiFi Watchdog monitors connectivity and automatically recovers${NC}"
        echo -e "  ${GRAY}from WiFi failures with escalating recovery actions:${NC}"
        echo ""
        echo -e "    • Soft WiFi reset (1-3 failures)"
        echo -e "    • Hard WiFi reset (4-5 failures)"
        echo -e "    • System reboot (6+ failures, max once per hour)"
        echo ""
        INSTALL_WIFI_WATCHDOG=true
        print_success "WiFi Watchdog will be installed"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

show_configuration_summary() {
    print_header "Configuration Summary"

    echo -e "  ${WHITE}${BOLD}Domain & Network${NC}"
    echo -e "    Domain: ${CYAN}$DOMAIN${NC}"
    [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ] && echo -e "    Cloudflare Tunnel: ${GREEN}Enabled${NC}"
    [ "$INSTALL_TAILSCALE" = true ] && echo -e "    Tailscale: ${GREEN}Enabled${NC} ($TAILSCALE_HOSTNAME)"
    echo ""

    echo -e "  ${WHITE}${BOLD}Hardware Mode${NC}"
    if [ "$MOCK_GPIO_MODE" = true ]; then
        echo -e "    GPIO: ${YELLOW}MOCK (Testing/Development)${NC}"
    else
        echo -e "    GPIO: ${GREEN}REAL (Raspberry Pi)${NC}"
    fi
    echo ""

    echo -e "  ${WHITE}${BOLD}Database${NC}"
    echo -e "    Name: ${CYAN}$DB_NAME${NC}"
    echo -e "    User: ${CYAN}$DB_USER${NC}"
    [ "$AUTOGEN_DB_PASSWORD" = true ] && echo -e "    Password: ${YELLOW}(auto-generated)${NC}"
    echo ""

    echo -e "  ${WHITE}${BOLD}GenSlave${NC}"
    if [ "$GENSLAVE_ENABLED" = "true" ]; then
        echo -e "    Status: ${GREEN}Enabled${NC}"
        echo -e "    URL: ${CYAN}$GENSLAVE_API_URL${NC}"
    else
        echo -e "    Status: ${YELLOW}Disabled${NC}"
    fi
    echo ""

    echo -e "  ${WHITE}${BOLD}Application${NC}"
    echo -e "    Timezone: ${CYAN}$TIMEZONE${NC}"
    [ "$INSTALL_WIFI_WATCHDOG" = true ] && echo -e "    WiFi Watchdog: ${GREEN}Enabled${NC}"
    echo ""

    if confirm_prompt "Proceed with this configuration?"; then
        return 0
    else
        return 1
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# FILE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

generate_env_file() {
    print_info "Generating .env file..."

    # CRITICAL: Create backup of existing .env before ANY changes
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        local backup_file="${SCRIPT_DIR}/.env.backup.$(date +%Y%m%d_%H%M%S)"
        cp "${SCRIPT_DIR}/.env" "$backup_file"
        print_success "Backup created: $backup_file"

        # Load existing values as fallbacks (preserve what we have)
        local EXISTING_DOMAIN EXISTING_SECRET_KEY EXISTING_TIMEZONE EXISTING_DB_NAME
        local EXISTING_DB_USER EXISTING_DB_PASSWORD EXISTING_GENSLAVE_ENABLED
        local EXISTING_GENSLAVE_API_URL EXISTING_GENSLAVE_API_SECRET EXISTING_AUTO_ARM_RELAY_ON_CONNECT
        local EXISTING_WEBHOOK_URL
        local EXISTING_WEBHOOK_SECRET EXISTING_DNS_PROVIDER EXISTING_DNS_CERTBOT_IMAGE
        local EXISTING_DNS_CREDENTIALS_FILE EXISTING_LETSENCRYPT_EMAIL
        local EXISTING_CLOUDFLARE_TUNNEL_TOKEN EXISTING_TAILSCALE_AUTH_KEY
        local EXISTING_TAILSCALE_HOSTNAME EXISTING_TAILSCALE_ROUTES
        local EXISTING_GEN_INFO_MANUFACTURER EXISTING_GEN_INFO_MODEL_NUMBER
        local EXISTING_GEN_INFO_SERIAL_NUMBER EXISTING_GEN_INFO_FUEL_TYPE
        local EXISTING_GEN_INFO_LOAD_EXPECTED EXISTING_GEN_INFO_FUEL_CONSUMPTION_50
        local EXISTING_GEN_INFO_FUEL_CONSUMPTION_100

        # Source existing .env to get current values
        set +e  # Don't exit on error during source
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue
            # Remove any surrounding quotes from value
            value="${value%\"}"
            value="${value#\"}"
            value="${value%\'}"
            value="${value#\'}"
            case "$key" in
                DOMAIN) EXISTING_DOMAIN="$value" ;;
                SECRET_KEY) EXISTING_SECRET_KEY="$value" ;;
                TIMEZONE) EXISTING_TIMEZONE="$value" ;;
                DATABASE_NAME) EXISTING_DB_NAME="$value" ;;
                DATABASE_USER) EXISTING_DB_USER="$value" ;;
                DATABASE_PASSWORD) EXISTING_DB_PASSWORD="$value" ;;
                GENSLAVE_ENABLED) EXISTING_GENSLAVE_ENABLED="$value" ;;
                SLAVE_API_URL) EXISTING_GENSLAVE_API_URL="$value" ;;
                SLAVE_API_SECRET) EXISTING_GENSLAVE_API_SECRET="$value" ;;
                AUTO_ARM_RELAY_ON_CONNECT) EXISTING_AUTO_ARM_RELAY_ON_CONNECT="$value" ;;
                WEBHOOK_BASE_URL) EXISTING_WEBHOOK_URL="$value" ;;
                WEBHOOK_SECRET) EXISTING_WEBHOOK_SECRET="$value" ;;
                DNS_PROVIDER) EXISTING_DNS_PROVIDER="$value" ;;
                DNS_CERTBOT_IMAGE) EXISTING_DNS_CERTBOT_IMAGE="$value" ;;
                DNS_CREDENTIALS_FILE) EXISTING_DNS_CREDENTIALS_FILE="$value" ;;
                LETSENCRYPT_EMAIL) EXISTING_LETSENCRYPT_EMAIL="$value" ;;
                CLOUDFLARE_TUNNEL_TOKEN) EXISTING_CLOUDFLARE_TUNNEL_TOKEN="$value" ;;
                TAILSCALE_AUTH_KEY) EXISTING_TAILSCALE_AUTH_KEY="$value" ;;
                TAILSCALE_HOSTNAME) EXISTING_TAILSCALE_HOSTNAME="$value" ;;
                TAILSCALE_ROUTES) EXISTING_TAILSCALE_ROUTES="$value" ;;
                GEN_INFO_MANUFACTURER) EXISTING_GEN_INFO_MANUFACTURER="$value" ;;
                GEN_INFO_MODEL_NUMBER) EXISTING_GEN_INFO_MODEL_NUMBER="$value" ;;
                GEN_INFO_SERIAL_NUMBER) EXISTING_GEN_INFO_SERIAL_NUMBER="$value" ;;
                GEN_INFO_FUEL_TYPE) EXISTING_GEN_INFO_FUEL_TYPE="$value" ;;
                GEN_INFO_LOAD_EXPECTED) EXISTING_GEN_INFO_LOAD_EXPECTED="$value" ;;
                GEN_INFO_FUEL_CONSUMPTION_50) EXISTING_GEN_INFO_FUEL_CONSUMPTION_50="$value" ;;
                GEN_INFO_FUEL_CONSUMPTION_100) EXISTING_GEN_INFO_FUEL_CONSUMPTION_100="$value" ;;
            esac
        done < "${SCRIPT_DIR}/.env"
        set -e

        # Use existing values as fallbacks if current values are empty
        DOMAIN="${DOMAIN:-$EXISTING_DOMAIN}"
        SECRET_KEY="${SECRET_KEY:-$EXISTING_SECRET_KEY}"
        TIMEZONE="${TIMEZONE:-$EXISTING_TIMEZONE}"
        DB_NAME="${DB_NAME:-$EXISTING_DB_NAME}"
        DB_USER="${DB_USER:-$EXISTING_DB_USER}"
        DB_PASSWORD="${DB_PASSWORD:-$EXISTING_DB_PASSWORD}"
        GENSLAVE_ENABLED="${GENSLAVE_ENABLED:-$EXISTING_GENSLAVE_ENABLED}"
        GENSLAVE_API_URL="${GENSLAVE_API_URL:-$EXISTING_GENSLAVE_API_URL}"
        GENSLAVE_API_SECRET="${GENSLAVE_API_SECRET:-$EXISTING_GENSLAVE_API_SECRET}"
        AUTO_ARM_RELAY_ON_CONNECT="${AUTO_ARM_RELAY_ON_CONNECT:-$EXISTING_AUTO_ARM_RELAY_ON_CONNECT}"
        WEBHOOK_URL="${WEBHOOK_URL:-$EXISTING_WEBHOOK_URL}"
        WEBHOOK_SECRET="${WEBHOOK_SECRET:-$EXISTING_WEBHOOK_SECRET}"
        DNS_PROVIDER_NAME="${DNS_PROVIDER_NAME:-$EXISTING_DNS_PROVIDER}"
        DNS_CERTBOT_IMAGE="${DNS_CERTBOT_IMAGE:-$EXISTING_DNS_CERTBOT_IMAGE}"
        DNS_CREDENTIALS_FILE="${DNS_CREDENTIALS_FILE:-$EXISTING_DNS_CREDENTIALS_FILE}"
        LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-$EXISTING_LETSENCRYPT_EMAIL}"
        CLOUDFLARE_TUNNEL_TOKEN="${CLOUDFLARE_TUNNEL_TOKEN:-$EXISTING_CLOUDFLARE_TUNNEL_TOKEN}"
        TAILSCALE_AUTH_KEY="${TAILSCALE_AUTH_KEY:-$EXISTING_TAILSCALE_AUTH_KEY}"
        TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-$EXISTING_TAILSCALE_HOSTNAME}"
        TAILSCALE_ROUTES="${TAILSCALE_ROUTES:-$EXISTING_TAILSCALE_ROUTES}"

        # Preserve generator info if not reconfigured during this run
        GEN_INFO_MANUFACTURER="${GEN_INFO_MANUFACTURER:-$EXISTING_GEN_INFO_MANUFACTURER}"
        GEN_INFO_MODEL_NUMBER="${GEN_INFO_MODEL_NUMBER:-$EXISTING_GEN_INFO_MODEL_NUMBER}"
        GEN_INFO_SERIAL_NUMBER="${GEN_INFO_SERIAL_NUMBER:-$EXISTING_GEN_INFO_SERIAL_NUMBER}"
        GEN_INFO_FUEL_TYPE="${GEN_INFO_FUEL_TYPE:-$EXISTING_GEN_INFO_FUEL_TYPE}"
        GEN_INFO_LOAD_EXPECTED="${GEN_INFO_LOAD_EXPECTED:-$EXISTING_GEN_INFO_LOAD_EXPECTED}"
        GEN_INFO_FUEL_CONSUMPTION_50="${GEN_INFO_FUEL_CONSUMPTION_50:-$EXISTING_GEN_INFO_FUEL_CONSUMPTION_50}"
        GEN_INFO_FUEL_CONSUMPTION_100="${GEN_INFO_FUEL_CONSUMPTION_100:-$EXISTING_GEN_INFO_FUEL_CONSUMPTION_100}"

        # Re-check optional services based on preserved tokens
        [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ] && INSTALL_CLOUDFLARE_TUNNEL=true
        [ -n "$TAILSCALE_AUTH_KEY" ] && INSTALL_TAILSCALE=true
    fi

    # Determine environment mode based on hardware detection
    local app_env="production"
    if [ "$MOCK_GPIO_MODE" = true ]; then
        app_env="development"
    fi

    cat > "${SCRIPT_DIR}/.env" << EOF
# =============================================================================
# GenMaster Environment Configuration
# Generated: $(date -Iseconds)
# =============================================================================

# Domain Configuration
DOMAIN=${DOMAIN}

# Application Settings
APP_ENV=${app_env}
APP_DEBUG=$([ "$MOCK_GPIO_MODE" = true ] && echo "true" || echo "false")
SECRET_KEY=${SECRET_KEY}
TIMEZONE=${TIMEZONE}

# GPIO Mode (auto-detected based on hardware)
# true = Mock GPIO (testing/development on non-Pi systems)
# false = Real GPIO (production on Raspberry Pi)
MOCK_GPIO_MODE=${MOCK_GPIO_MODE}

# Database Configuration
DATABASE_HOST=db
DATABASE_PORT=5432
DATABASE_NAME=${DB_NAME}
DATABASE_USER=${DB_USER}
DATABASE_PASSWORD=${DB_PASSWORD}

# Admin User (created on first startup)
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# GenSlave Communication
GENSLAVE_ENABLED=${GENSLAVE_ENABLED}
SLAVE_API_URL=${GENSLAVE_API_URL}
SLAVE_API_SECRET=${GENSLAVE_API_SECRET}
GENSLAVE_IP=${GENSLAVE_IP}
GENSLAVE_HOSTNAME=${GENSLAVE_HOSTNAME:-genslave}
AUTO_ARM_RELAY_ON_CONNECT=${AUTO_ARM_RELAY_ON_CONNECT:-false}

# Generator Information (optional - can be configured via web UI)
# Set these values to pre-populate generator info on first startup
GEN_INFO_MANUFACTURER=${GEN_INFO_MANUFACTURER:-}
GEN_INFO_MODEL_NUMBER=${GEN_INFO_MODEL_NUMBER:-}
GEN_INFO_SERIAL_NUMBER=${GEN_INFO_SERIAL_NUMBER:-}
GEN_INFO_FUEL_TYPE=${GEN_INFO_FUEL_TYPE:-}
GEN_INFO_LOAD_EXPECTED=${GEN_INFO_LOAD_EXPECTED:-}
GEN_INFO_FUEL_CONSUMPTION_50=${GEN_INFO_FUEL_CONSUMPTION_50:-}
GEN_INFO_FUEL_CONSUMPTION_100=${GEN_INFO_FUEL_CONSUMPTION_100:-}

# Webhook Configuration
WEBHOOK_BASE_URL=${WEBHOOK_URL}
WEBHOOK_SECRET=${WEBHOOK_SECRET}
WEBHOOK_ENABLED=$([ -n "$WEBHOOK_URL" ] && echo "true" || echo "false")

# Heartbeat Settings
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# GPIO Configuration
GPIO_PIN_VICTRON=17

# SSL/Let's Encrypt Configuration
DNS_PROVIDER=${DNS_PROVIDER_NAME}
DNS_CERTBOT_IMAGE=${DNS_CERTBOT_IMAGE}
DNS_CREDENTIALS_FILE=${DNS_CREDENTIALS_FILE}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}

# Container Names
POSTGRES_CONTAINER=${POSTGRES_CONTAINER:-genmaster_db}
GENMASTER_CONTAINER=${GENMASTER_CONTAINER:-genmaster}
NGINX_CONTAINER=${NGINX_CONTAINER:-genmaster_nginx}
REDIS_CONTAINER=${REDIS_CONTAINER:-genmaster_redis}

# Docker Socket Access (for container management UI)
DOCKER_GID=${DOCKER_GID:-999}
EOF

    # Add Cloudflare Tunnel if enabled
    if [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ]; then
        cat >> "${SCRIPT_DIR}/.env" << EOF

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
EOF
    fi

    # Add Tailscale if enabled
    if [ "$INSTALL_TAILSCALE" = true ]; then
        # Preserve existing TAILSCALE_ROUTES or auto-detect
        local tailscale_routes="${TAILSCALE_ROUTES:-}"
        local primary_ip=$(get_local_ips | head -1)

        if [ -z "$tailscale_routes" ] && [ -n "$primary_ip" ]; then
            # No existing routes - auto-detect
            tailscale_routes="${primary_ip}/32"
            echo ""
            print_info "Docker host IP detected: ${primary_ip}"
            print_info "Tailscale route configured: ${tailscale_routes}"
            print_info "To expose your full subnet, change TAILSCALE_ROUTES in .env to ${primary_ip%.*}.0/24"
        elif [ -n "$tailscale_routes" ]; then
            print_info "Preserving existing Tailscale routes: ${tailscale_routes}"
        fi

        cat >> "${SCRIPT_DIR}/.env" << EOF

# Tailscale VPN
# Get auth key from: https://login.tailscale.com/admin/settings/keys
TAILSCALE_AUTH_KEY=${TAILSCALE_AUTH_KEY}
TAILSCALE_HOSTNAME=${TAILSCALE_HOSTNAME:-genmaster}
# Advertise routes in CIDR notation
# Single host: ${primary_ip:-192.168.1.10}/32 (Docker host only)
# Full subnet: ${primary_ip%.*:-192.168.1}.0/24 (entire local network)
TAILSCALE_ROUTES=${tailscale_routes}
EOF
    fi

    chmod 644 "${SCRIPT_DIR}/.env"
    print_success ".env generated"

    if [ "$MOCK_GPIO_MODE" = true ]; then
        print_info "Mock GPIO mode enabled in .env (APP_ENV=development)"
    fi
}

generate_docker_compose() {
    print_info "Generating docker-compose.yaml..."

    cat > "${SCRIPT_DIR}/docker-compose.yaml" << 'EOF'
# =============================================================================
# GenMaster Docker Compose Configuration
# =============================================================================

networks:
  genmaster-internal:
    driver: bridge
    internal: true
  genmaster-external:
    driver: bridge

volumes:
  genmaster_db_data:
  genmaster_redis_data:
  genmaster_logs:
  genmaster_data:
  nginx_logs:
  # SSL certificates (external, created by setup.sh)
  letsencrypt:
    external: true
  certbot_data:
  tailscale_state:
  portainer_data:

services:
  # ===========================================================================
  # PostgreSQL Database
  # ===========================================================================
  db:
    image: postgres:16-alpine
    container_name: ${POSTGRES_CONTAINER:-genmaster_db}
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-genmaster}
      POSTGRES_USER: ${DATABASE_USER:-genmaster}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - genmaster_db_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5432:5432"
    networks:
      - genmaster-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-genmaster}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # Redis Cache
  # ===========================================================================
  redis:
    image: redis:7-alpine
    container_name: ${REDIS_CONTAINER:-genmaster_redis}
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - genmaster_redis_data:/data
    ports:
      - "127.0.0.1:6379:6379"
    networks:
      - genmaster-internal
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # GenMaster Application
  # ===========================================================================
  # Uses Docker bridge networking for container-to-container communication.
  # Connects to database and Redis via service names (db, redis).
  genmaster:
EOF

    # Add either image: or build: based on configuration
    if [ "$USE_DOCKER_HUB_IMAGE" = true ]; then
        cat >> "${SCRIPT_DIR}/docker-compose.yaml" << EOF
    image: ${DOCKER_HUB_IMAGE}
EOF
    else
        cat >> "${SCRIPT_DIR}/docker-compose.yaml" << 'EOF'
    build:
      context: .
      dockerfile: Dockerfile
EOF
    fi

    # Continue with the rest of the genmaster service configuration
    cat >> "${SCRIPT_DIR}/docker-compose.yaml" << 'EOF'
    container_name: ${GENMASTER_CONTAINER:-genmaster}
    restart: unless-stopped
    privileged: true
    user: root
    networks:
      - genmaster-internal
      - genmaster-external
    environment:
      - APP_ENV=${APP_ENV:-production}
      - MOCK_GPIO_MODE=${MOCK_GPIO_MODE:-false}
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - DATABASE_NAME=${DATABASE_NAME:-genmaster}
      - DATABASE_USER=${DATABASE_USER:-genmaster}
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - GENSLAVE_ENABLED=${GENSLAVE_ENABLED:-true}
      - SLAVE_API_URL=${SLAVE_API_URL}
      - SLAVE_API_SECRET=${SLAVE_API_SECRET}
      - WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
      - WEBHOOK_ENABLED=${WEBHOOK_ENABLED:-false}
      - TZ=${TIMEZONE:-America/Los_Angeles}
      - GENSLAVE_IP=${GENSLAVE_IP:-}
      - GENSLAVE_HOSTNAME=${GENSLAVE_HOSTNAME:-genslave}
      - DOCKER_GID=${DOCKER_GID:-999}
      # Generator Info (optional - for pre-configuration via setup wizard)
      - GEN_INFO_MANUFACTURER=${GEN_INFO_MANUFACTURER:-}
      - GEN_INFO_MODEL_NUMBER=${GEN_INFO_MODEL_NUMBER:-}
      - GEN_INFO_SERIAL_NUMBER=${GEN_INFO_SERIAL_NUMBER:-}
      - GEN_INFO_FUEL_TYPE=${GEN_INFO_FUEL_TYPE:-}
      - GEN_INFO_LOAD_EXPECTED=${GEN_INFO_LOAD_EXPECTED:-}
      - GEN_INFO_FUEL_CONSUMPTION_50=${GEN_INFO_FUEL_CONSUMPTION_50:-}
      - GEN_INFO_FUEL_CONSUMPTION_100=${GEN_INFO_FUEL_CONSUMPTION_100:-}
    group_add:
      - "${DOCKER_GID:-999}"
    volumes:
      - genmaster_logs:/app/logs
      - genmaster_data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
      - ./nginx:/app/nginx
      - ./.env:/config/.env:rw
      - ../scripts:/app/scripts:ro
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ===========================================================================
  # Nginx Reverse Proxy
  # ===========================================================================
  # Reverse proxy for GenMaster application with SSL termination.
  nginx:
    image: nginx:alpine
    container_name: ${NGINX_CONTAINER:-genmaster_nginx}
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - letsencrypt:/etc/letsencrypt:ro
      - certbot_data:/var/www/certbot:ro
      - nginx_logs:/var/log/nginx
    networks:
      - genmaster-internal
      - genmaster-external
    depends_on:
      - genmaster

  # ===========================================================================
  # Certbot (Let's Encrypt SSL)
  # ===========================================================================
  certbot:
    image: ${DNS_CERTBOT_IMAGE:-certbot/certbot:latest}
    container_name: genmaster_certbot
    volumes:
      - letsencrypt:/etc/letsencrypt
      - certbot_data:/var/www/certbot
      - ./certbot/${DNS_CREDENTIALS_FILE:-cloudflare.ini}:/credentials.ini:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew \${DNS_CERTBOT_FLAGS:-} --deploy-hook 'docker exec genmaster_nginx nginx -s reload' || true; sleep 12h & wait $${!}; done;"
    networks:
      - genmaster-internal
EOF

    # Add Cloudflare Tunnel if enabled
    if [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ]; then
        cat >> "${SCRIPT_DIR}/docker-compose.yaml" << 'EOF'

  # ===========================================================================
  # Cloudflare Tunnel
  # ===========================================================================
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: genmaster_cloudflared
    restart: always
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - genmaster-external

EOF
    fi

    # Add Tailscale if enabled
    if [ "$INSTALL_TAILSCALE" = true ]; then
        cat >> "${SCRIPT_DIR}/docker-compose.yaml" << 'EOF'

  # ===========================================================================
  # Tailscale VPN
  # ===========================================================================
  # Provides private access via Tailscale network.
  # After startup, approve machine at: https://login.tailscale.com/admin/machines
  tailscale:
    image: tailscale/tailscale:latest
    container_name: genmaster_tailscale
    restart: always
    hostname: genmaster-tailscale
    network_mode: host
    environment:
      - TS_AUTHKEY=${TAILSCALE_AUTH_KEY}
      - TS_HOSTNAME=${TAILSCALE_HOSTNAME}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=false
      - TS_EXTRA_ARGS=--accept-routes
      - TS_ROUTES=${TAILSCALE_ROUTES}
      - TS_AUTH_ONCE=true
    volumes:
      - tailscale_state:/var/lib/tailscale
    cap_add:
      - NET_ADMIN
      - NET_RAW
    devices:
      - /dev/net/tun:/dev/net/tun

EOF
    fi

    # Add Portainer if enabled
    if [ "$INSTALL_PORTAINER" = true ]; then
        # Generate bcrypt hash of admin password for Portainer
        # Uses httpd:alpine image which has htpasswd built in
        print_info "Generating Portainer admin password hash..."
        PORTAINER_PASS_HASH=$(docker run --rm httpd:alpine htpasswd -nbB admin "${ADMIN_PASSWORD}" 2>/dev/null | cut -d: -f2)
        if [ -z "$PORTAINER_PASS_HASH" ]; then
            print_warning "Could not generate password hash - Portainer will prompt for password on first login"
            PORTAINER_COMMAND="--base-url /portainer"
        else
            # Escape $ for docker-compose YAML ($ becomes $$)
            PORTAINER_PASS_HASH_ESCAPED=$(echo "$PORTAINER_PASS_HASH" | sed 's/\$/\$\$/g')
            PORTAINER_COMMAND="--base-url /portainer --admin-password='${PORTAINER_PASS_HASH_ESCAPED}'"
        fi

        cat >> "${SCRIPT_DIR}/docker-compose.yaml" << EOF

  # ===========================================================================
  # Portainer Container Management
  # ===========================================================================
  portainer:
    image: portainer/portainer-ce:latest
    container_name: genmaster_portainer
    restart: unless-stopped
    command: ${PORTAINER_COMMAND}
    environment:
      - PORTAINER_CSRF_DISABLE=true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    networks:
      - genmaster-internal

EOF
    fi

    print_success "docker-compose.yaml generated"
}

generate_nginx_conf() {
    print_info "Generating nginx configuration..."

    # Verify DOMAIN is set
    if [ -z "${DOMAIN}" ]; then
        print_error "DOMAIN variable is not set - cannot generate nginx.conf"
        exit 1
    fi

    print_info "Configuring nginx for domain: ${DOMAIN}"

    mkdir -p "${SCRIPT_DIR}/nginx"
    mkdir -p "${SCRIPT_DIR}/nginx/ssl"

    # Build internal IP list
    local internal_ips=""
    for ip in $DEFAULT_INTERNAL_IP_RANGES; do
        internal_ips="${internal_ips}        $ip internal;\n"
    done

    # Remove any existing nginx.conf to ensure clean generation
    rm -f "${SCRIPT_DIR}/nginx/nginx.conf"

    cat > "${SCRIPT_DIR}/nginx/nginx.conf" << EOF
# =============================================================================
# GenMaster Nginx Configuration
# =============================================================================

worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # ==========================================================================
    # Real IP Configuration for Cloudflare Tunnel
    # ==========================================================================
    # Trust Docker/internal networks as proxies (cloudflared connects from here)
    # This allows nginx to extract the real client IP from X-Forwarded-For header
    set_real_ip_from 172.16.0.0/12;
    set_real_ip_from 10.0.0.0/8;
    set_real_ip_from 192.168.0.0/16;
    set_real_ip_from 100.64.0.0/10;
    set_real_ip_from 127.0.0.1;

    # Cloudflare sets X-Forwarded-For with the real client IP
    real_ip_header X-Forwarded-For;

    # Enable recursive lookup (use rightmost untrusted IP)
    real_ip_recursive on;

    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" access=\$access_level';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Rate limiting (uses real client IP after real_ip processing)
    limit_req_zone \$binary_remote_addr zone=api:10m rate=30r/s;

    # IP-based access control (uses real client IP after real_ip processing)
    geo \$access_level {
        default external;
$(echo -e "$internal_ips")
    }

    upstream genmaster {
        server genmaster:8000;
        keepalive 32;
    }

    server {
        listen 443 ssl;
        http2 on;
        server_name ${DOMAIN};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;

        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;

        location /api/ {
            if (\$access_level = "external") {
                return 403;
            }
            limit_req zone=api burst=50 nodelay;
            proxy_pass http://genmaster;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /ws/ {
            if (\$access_level = "external") {
                return 403;
            }
            proxy_pass http://genmaster;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400s;
        }

        location /healthz {
            if (\$access_level = "external") {
                return 403;
            }
            access_log off;
            return 200 "healthy\n";
        }

        location / {
            if (\$access_level = "external") {
                return 403;
            }
            proxy_pass http://genmaster;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }
EOF

    # Add Portainer if enabled
    if [ "$INSTALL_PORTAINER" = true ]; then
        cat >> "${SCRIPT_DIR}/nginx/nginx.conf" << 'EOF'

        # Portainer Container Management - INTERNAL ACCESS ONLY
        # Note: Portainer runs with --base-url /portainer, trailing slash strips /portainer/ prefix
        location /portainer/ {
            if ($access_level = "external") {
                return 403;
            }

            proxy_pass http://genmaster_portainer:9000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # Portainer WebSocket endpoint
        location /portainer/api/websocket/ {
            if ($access_level = "external") {
                return 403;
            }

            proxy_pass http://genmaster_portainer:9000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
EOF
    fi

    cat >> "${SCRIPT_DIR}/nginx/nginx.conf" << 'EOF'
    }
}
EOF

    # Verify nginx.conf was generated correctly
    if [ ! -f "${SCRIPT_DIR}/nginx/nginx.conf" ]; then
        print_error "Failed to create nginx.conf"
        exit 1
    fi

    # Verify domain was substituted (should NOT contain placeholder)
    if grep -q "YOUR_DOMAIN_HERE" "${SCRIPT_DIR}/nginx/nginx.conf"; then
        print_error "nginx.conf generation failed - domain not substituted"
        print_error "Expected domain: ${DOMAIN}"
        print_error "File still contains YOUR_DOMAIN_HERE placeholder"
        exit 1
    fi

    # Verify domain IS in the file
    if ! grep -q "server_name ${DOMAIN}" "${SCRIPT_DIR}/nginx/nginx.conf"; then
        print_error "nginx.conf generation failed - domain not found in config"
        print_error "Expected: server_name ${DOMAIN}"
        exit 1
    fi

    print_success "nginx.conf generated for ${DOMAIN}"
}

# =============================================================================
# SSL CERTIFICATE MANAGEMENT
# =============================================================================

create_letsencrypt_volume() {
    # Volume is external in docker-compose, so we create it manually with exact name
    if $DOCKER_SUDO docker volume inspect letsencrypt >/dev/null 2>&1; then
        print_info "Volume 'letsencrypt' already exists"
    else
        $DOCKER_SUDO docker volume create letsencrypt
        print_success "Volume 'letsencrypt' created"
    fi
}

obtain_ssl_certificate() {
    print_section "SSL Certificate"

    local cred_volume_opt=""
    local certbot_flags=""
    local domains_arg="-d $DOMAIN"

    # Setup credentials based on DNS provider
    case $DNS_PROVIDER_NAME in
        cloudflare)
            cred_volume_opt="-v ${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}:/credentials.ini:ro"
            certbot_flags="--dns-cloudflare --dns-cloudflare-credentials /credentials.ini --dns-cloudflare-propagation-seconds 60"
            ;;
        digitalocean)
            cred_volume_opt="-v ${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}:/credentials.ini:ro"
            certbot_flags="--dns-digitalocean --dns-digitalocean-credentials /credentials.ini --dns-digitalocean-propagation-seconds 60"
            ;;
        route53)
            cred_volume_opt="-v ${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}:/root/.aws/credentials:ro"
            certbot_flags="--dns-route53"
            ;;
        google)
            cred_volume_opt="-v ${SCRIPT_DIR}/certbot/${DNS_CREDENTIALS_FILE}:/credentials.json:ro"
            certbot_flags="--dns-google --dns-google-credentials /credentials.json --dns-google-propagation-seconds 120"
            ;;
        *)
            print_error "Unknown DNS provider: $DNS_PROVIDER_NAME"
            exit 1
            ;;
    esac

    # Check if certificate already exists in volume (external volume, no prefix)
    if $DOCKER_SUDO docker run --rm \
        -v letsencrypt:/etc/letsencrypt:ro \
        alpine \
        sh -c "test -f /etc/letsencrypt/live/${DOMAIN}/fullchain.pem" 2>/dev/null; then
        print_success "Valid SSL certificate already exists for ${DOMAIN}"
        return 0
    fi

    print_info "Obtaining SSL certificate for ${DOMAIN}..."

    # Create temp directory for initial cert
    mkdir -p "${SCRIPT_DIR}/letsencrypt-temp"

    # Run certbot to obtain certificate
    if ! $DOCKER_SUDO docker run --rm \
        -v "${SCRIPT_DIR}/letsencrypt-temp:/etc/letsencrypt" \
        $cred_volume_opt \
        $DNS_CERTBOT_IMAGE \
        certonly \
        $certbot_flags \
        $domains_arg \
        --agree-tos \
        --non-interactive \
        --email "$LETSENCRYPT_EMAIL"; then
        print_error "Failed to obtain SSL certificate"
        rm -rf "${SCRIPT_DIR}/letsencrypt-temp"
        exit 1
    fi

    print_success "SSL certificate obtained"

    # Verify certificate was created
    if [ ! -f "${SCRIPT_DIR}/letsencrypt-temp/live/${DOMAIN}/fullchain.pem" ]; then
        print_error "Certificate file not found in temp directory"
        ls -laR "${SCRIPT_DIR}/letsencrypt-temp/" 2>/dev/null || true
        rm -rf "${SCRIPT_DIR}/letsencrypt-temp"
        exit 1
    fi

    print_info "Certificate files found, copying to Docker volume..."

    # Copy certificates to docker volume with error checking (external volume, no prefix)
    if ! $DOCKER_SUDO docker run --rm \
        -v "${SCRIPT_DIR}/letsencrypt-temp:/source:ro" \
        -v letsencrypt:/etc/letsencrypt \
        alpine \
        sh -c "cp -rL /source/* /etc/letsencrypt/ && ls -la /etc/letsencrypt/live/${DOMAIN}/"; then
        print_error "Failed to copy certificates to Docker volume"
        rm -rf "${SCRIPT_DIR}/letsencrypt-temp"
        exit 1
    fi

    rm -rf "${SCRIPT_DIR}/letsencrypt-temp"
    print_success "Certificates copied to Docker volume"
}

# ═══════════════════════════════════════════════════════════════════════════════
# WIFI WATCHDOG INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

install_wifi_watchdog() {
    if [ "$INSTALL_WIFI_WATCHDOG" != true ]; then
        return 0
    fi

    print_section "Installing WiFi Watchdog"

    # Get the repository root (parent of genmaster directory)
    local repo_root
    repo_root=$(dirname "$SCRIPT_DIR")
    local watchdog_script="${repo_root}/scripts/wifi-watchdog.sh"
    local watchdog_service="${repo_root}/scripts/wifi-watchdog.service"

    # Check if scripts exist in repo
    if [ ! -f "$watchdog_script" ]; then
        print_error "WiFi watchdog script not found: $watchdog_script"
        print_info "Skipping WiFi watchdog installation"
        return 1
    fi

    if [ ! -f "$watchdog_service" ]; then
        print_error "WiFi watchdog service file not found: $watchdog_service"
        print_info "Skipping WiFi watchdog installation"
        return 1
    fi

    # Check if WiFi interface exists
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

    if [ -z "$wifi_iface" ]; then
        print_warning "No WiFi interface detected - WiFi watchdog may not function"
        if ! confirm_prompt "Install anyway?"; then
            print_info "Skipping WiFi watchdog installation"
            return 0
        fi
    else
        print_info "Detected WiFi interface: $wifi_iface"
    fi

    # Copy script to /usr/local/bin
    print_info "Installing watchdog script..."
    cp "$watchdog_script" /usr/local/bin/wifi-watchdog.sh
    chmod +x /usr/local/bin/wifi-watchdog.sh
    print_success "Installed /usr/local/bin/wifi-watchdog.sh"

    # Copy service file
    print_info "Installing systemd service..."
    cp "$watchdog_service" /etc/systemd/system/wifi-watchdog.service
    print_success "Installed /etc/systemd/system/wifi-watchdog.service"

    # Enable and start service
    systemctl daemon-reload
    systemctl enable wifi-watchdog
    systemctl start wifi-watchdog

    # Verify it's running
    if systemctl is-active --quiet wifi-watchdog; then
        print_success "WiFi Watchdog is running"
    else
        print_warning "WiFi Watchdog service may not have started properly"
        print_info "Check status with: systemctl status wifi-watchdog"
    fi

    return 0
}

# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOYMENT
# ═══════════════════════════════════════════════════════════════════════════════

deploy_stack() {
    print_section "Deploying GenMaster"

    local docker_compose_cmd="docker compose"
    [ "$USE_STANDALONE_COMPOSE" = true ] && docker_compose_cmd="docker-compose"
    [ -n "$DOCKER_SUDO" ] && docker_compose_cmd="$DOCKER_SUDO $docker_compose_cmd"

    cd "$SCRIPT_DIR"

    # Create letsencrypt volume (always needed)
    create_letsencrypt_volume

    # Only obtain SSL certificate for fresh installs - reconfigure keeps existing certs
    if [ "$INSTALL_MODE" != "reconfigure" ]; then
        obtain_ssl_certificate
    else
        print_info "Using existing SSL certificates"
    fi

    if [ "$USE_DOCKER_HUB_IMAGE" = true ]; then
        print_info "Pulling GenMaster image from Docker Hub..."
        $DOCKER_SUDO docker pull "${DOCKER_HUB_IMAGE}"
        print_info "Starting containers..."
        $docker_compose_cmd up -d
    else
        print_info "Building and starting containers..."
        $docker_compose_cmd up -d --build
    fi

    print_info "Waiting for services..."
    sleep 10

    # Health check
    local attempts=0
    while [ $attempts -lt 30 ]; do
        if $DOCKER_SUDO docker exec $GENMASTER_CONTAINER curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
            print_success "All services healthy!"
            break
        fi
        attempts=$((attempts + 1))
        printf "\r  ${GRAY}Waiting... (%d/30)${NC}" $attempts
        sleep 2
    done
    echo ""

    show_deployment_summary
}

show_deployment_summary() {
    print_header "Setup Complete!"

    echo -e "  ${WHITE}Your GenMaster instance is now running!${NC}"
    echo ""

    # Access URLs
    echo -e "  ${WHITE}${BOLD}Access URLs:${NC}"
    echo -e "    GenMaster:           ${CYAN}https://${DOMAIN}${NC}"
    [ "$INSTALL_PORTAINER" = true ] && echo -e "    Portainer:           ${CYAN}https://${DOMAIN}/portainer/${NC}"
    if [ "$INSTALL_TAILSCALE" = true ]; then
        echo -e "    Tailscale:           ${CYAN}https://${TAILSCALE_HOSTNAME}.your-tailnet.ts.net${NC}"
    fi
    echo ""

    # Database Credentials
    echo -e "  ${WHITE}${BOLD}Database Credentials:${NC}"
    echo -e "    Server:              ${CYAN}db${NC}"
    echo -e "    Username:            ${CYAN}${DB_USER}${NC}"
    echo -e "    Password:            ${CYAN}${DB_PASSWORD}${NC}"
    echo -e "    Database:            ${CYAN}${DB_NAME}${NC}"
    echo ""

    # GenSlave Configuration
    if [ "$GENSLAVE_ENABLED" = true ] && [ -n "$GENSLAVE_API_URL" ]; then
        echo -e "  ${WHITE}${BOLD}GenSlave Configuration:${NC}"
        echo -e "    API URL:             ${CYAN}${GENSLAVE_API_URL}${NC}"
        if [ -n "$GENSLAVE_API_SECRET" ]; then
            echo ""
            echo -e "  ${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
            echo -e "  ${GREEN}║${NC}  ${WHITE}IMPORTANT: Copy this API secret for GenSlave setup!${NC}           ${GREEN}║${NC}"
            echo -e "  ${GREEN}╠════════════════════════════════════════════════════════════════╣${NC}"
            echo -e "  ${GREEN}║${NC}                                                                ${GREEN}║${NC}"
            echo -e "  ${GREEN}║${NC}  ${CYAN}SLAVE_API_SECRET=${GENSLAVE_API_SECRET}${NC}  ${GREEN}║${NC}"
            echo -e "  ${GREEN}║${NC}                                                                ${GREEN}║${NC}"
            echo -e "  ${GREEN}║${NC}  ${GRAY}You will need this when running GenSlave setup.${NC}              ${GREEN}║${NC}"
            echo -e "  ${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
        fi
        echo ""
    fi

    # Network Access
    echo -e "  ${WHITE}${BOLD}Network Access:${NC}"
    [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ] && echo -e "    Cloudflare Tunnel:   ${GREEN}Active${NC}"
    [ "$INSTALL_TAILSCALE" = true ] && echo -e "    Tailscale:           ${GREEN}Active${NC} (${TAILSCALE_HOSTNAME})"
    echo ""

    # Tailscale Action Required
    if [ "$INSTALL_TAILSCALE" = true ]; then
        local ts_route_ip=$(get_local_ips | head -1)
        echo -e "  ${YELLOW}⚠ TAILSCALE ACTION REQUIRED:${NC}"
        echo -e "    Complete these steps to enable Tailscale access:"
        echo ""
        echo -e "    ${WHITE}Step 1: Approve the machine and route${NC}"
        echo -e "      • Visit: ${CYAN}https://login.tailscale.com/admin/machines${NC}"
        echo -e "      • Find your ${WHITE}${TAILSCALE_HOSTNAME}${NC} node"
        echo -e "      • Click '...' menu → 'Edit route settings'"
        echo -e "      • Approve the advertised route: ${WHITE}${ts_route_ip}/32${NC}"
        echo ""
        echo -e "    ${WHITE}Step 2: Enable HTTPS certificates${NC}"
        echo -e "      • Visit: ${CYAN}https://login.tailscale.com/admin/dns${NC}"
        echo -e "      • Enable ${WHITE}MagicDNS${NC} (if not already enabled)"
        echo -e "      • Enable ${WHITE}HTTPS Certificates${NC}"
        echo ""
        echo -e "    ${GRAY}NOTE: GenMaster will NOT be accessible via Tailscale HTTPS${NC}"
        echo -e "    ${GRAY}      until both steps are completed!${NC}"
        echo ""
        echo -e "    After setup, access via: ${CYAN}https://${TAILSCALE_HOSTNAME}.<your-tailnet>.ts.net${NC}"
        echo ""
    fi

    # Cloudflare Action Required
    if [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ]; then
        echo -e "  ${YELLOW}⚠ CLOUDFLARE ACTION REQUIRED:${NC}"
        echo -e "    You must add a Public Hostname in Zero Trust:"
        echo ""
        echo -e "    1. Visit: ${CYAN}https://one.dash.cloudflare.com${NC}"
        echo -e "    2. Networks > Tunnels > [Your Tunnel] > Configure > Public Hostname"
        echo -e "    3. Add Hostname: ${WHITE}${DOMAIN}${NC}"
        echo -e "    4. Service: HTTPS -> genmaster_nginx:443"
        echo -e "    5. Settings: Enable No TLS Verify"
        echo ""
    fi

    # GPIO Mode
    if [ "$MOCK_GPIO_MODE" = true ]; then
        echo -e "  ${YELLOW}ℹ Mock GPIO Mode Active${NC}"
        echo -e "    Running in development/test mode (no physical GPIO)"
        echo -e "    Dev API available at /api/dev/*"
        echo ""
    else
        echo -e "  ${GREEN}✓ Real GPIO Mode (Raspberry Pi)${NC}"
        echo ""
    fi

    # Useful Commands
    echo -e "  ${WHITE}${BOLD}Useful Commands:${NC}"
    echo -e "    ${GRAY}View logs:${NC}         docker compose logs -f"
    echo -e "    ${GRAY}Stop services:${NC}     docker compose down"
    echo -e "    ${GRAY}Start services:${NC}    docker compose up -d"
    echo -e "    ${GRAY}Restart:${NC}           docker compose restart"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LINE
# ═══════════════════════════════════════════════════════════════════════════════

show_help() {
    echo "GenMaster Setup Script v${SCRIPT_VERSION}"
    echo ""
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help              Show this help"
    echo "  --config <file>     Use pre-configuration file"
    echo "  --genslave          Validate GenSlave connection (run after GenSlave is set up)"
    echo "  --genslaveip        Update GenSlave URL/IP address"
    echo "  --version           Show version"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh                    Interactive setup"
    echo "  ./setup.sh --config my.conf   Use pre-configuration file"
    echo "  ./setup.sh --genslave         Test GenSlave connection"
    echo "  ./setup.sh --genslaveip       Update GenSlave URL"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    PRECONFIG_MODE=false
    PRECONFIG_AUTO_CONFIRM=false

    # CRITICAL: Backup existing .env IMMEDIATELY before doing ANYTHING
    # This protects against any code path that might corrupt the file
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        local backup_dir="${SCRIPT_DIR}/backups"
        local timestamp=$(date +%Y%m%d_%H%M%S)
        mkdir -p "$backup_dir"
        cp "${SCRIPT_DIR}/.env" "${backup_dir}/.env.startup_backup.${timestamp}"
        echo -e "${GREEN}  ✓${NC} Startup backup: ${backup_dir}/.env.startup_backup.${timestamp}"
    fi

    case "${1:-}" in
        --help|-h) show_help; exit 0 ;;
        --version|-v) echo "v${SCRIPT_VERSION}"; exit 0 ;;
        --config)
            [ -z "${2:-}" ] && { print_error "Usage: ./setup.sh --config <file>"; exit 1; }
            load_preconfig "$2"
            ;;
        --genslave)
            # Run GenSlave validation only
            echo ""
            print_section "GenSlave Connection Validation"

            # Load existing config if available
            if [ -f "$CONFIG_FILE" ]; then
                source "$CONFIG_FILE" 2>/dev/null
            fi
            if [ -f "${SCRIPT_DIR}/.env" ]; then
                # Extract GenSlave URL from .env file
                GENSLAVE_API_URL=$(grep "^SLAVE_API_URL=" "${SCRIPT_DIR}/.env" 2>/dev/null | cut -d'=' -f2-)
                GENSLAVE_API_SECRET=$(grep "^SLAVE_API_SECRET=" "${SCRIPT_DIR}/.env" 2>/dev/null | cut -d'=' -f2-)
            fi

            if [ -z "$GENSLAVE_API_URL" ]; then
                print_error "GenSlave URL not configured"
                echo ""
                echo -e "  ${GRAY}Run ./setup.sh to configure GenSlave first, or enter the URL now:${NC}"
                echo ""
                while true; do
                    echo -ne "${WHITE}  GenSlave API URL (e.g., http://genslave.local:8001)${NC}: "
                    read GENSLAVE_API_URL
                    if [ -n "$GENSLAVE_API_URL" ]; then
                        break
                    fi
                    print_error "URL is required"
                done
            else
                print_info "GenSlave URL: $GENSLAVE_API_URL"
            fi

            validate_genslave
            echo ""
            exit 0
            ;;
        --genslaveip)
            # Update GenSlave URL/IP
            echo ""
            print_section "Update GenSlave URL"

            # Check if .env file exists
            if [ ! -f "${SCRIPT_DIR}/.env" ]; then
                print_error "No .env file found. Run ./setup.sh first to configure GenMaster."
                exit 1
            fi

            # Show current URL
            local current_url=$(grep "^SLAVE_API_URL=" "${SCRIPT_DIR}/.env" 2>/dev/null | cut -d'=' -f2-)
            if [ -n "$current_url" ]; then
                print_info "Current GenSlave URL: $current_url"
            else
                print_warning "GenSlave URL not currently configured"
            fi
            echo ""

            # Get new URL
            while true; do
                echo -ne "${WHITE}  New GenSlave API URL (e.g., http://genslave.local:8001)${NC}: "
                read new_url
                if [ -n "$new_url" ]; then
                    # Validate URL format
                    if [[ ! "$new_url" =~ ^https?:// ]]; then
                        print_warning "URL should start with http:// or https://"
                        if ! confirm_prompt "Continue with this URL anyway?"; then
                            continue
                        fi
                    fi
                    break
                fi
                print_error "URL is required"
            done

            # Update .env file
            if grep -q "^SLAVE_API_URL=" "${SCRIPT_DIR}/.env" 2>/dev/null; then
                # Update existing line
                sed -i "s|^SLAVE_API_URL=.*|SLAVE_API_URL=${new_url}|" "${SCRIPT_DIR}/.env"
            else
                # Add new line
                echo "SLAVE_API_URL=${new_url}" >> "${SCRIPT_DIR}/.env"
            fi

            # Also update GENSLAVE_ENABLED if it was disabled
            if grep -q "^GENSLAVE_ENABLED=false" "${SCRIPT_DIR}/.env" 2>/dev/null; then
                sed -i "s|^GENSLAVE_ENABLED=false|GENSLAVE_ENABLED=true|" "${SCRIPT_DIR}/.env"
                print_info "GenSlave communication enabled"
            fi

            print_success "GenSlave URL updated to: $new_url"
            echo ""

            # Offer to run health checks
            GENSLAVE_API_URL="$new_url"
            if confirm_prompt "Run GenSlave health checks now?" "y"; then
                validate_genslave
            fi

            # Offer to restart containers
            echo ""
            if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "genmaster"; then
                if confirm_prompt "Restart GenMaster container to apply changes?"; then
                    print_info "Restarting GenMaster..."
                    cd "${SCRIPT_DIR}" && docker compose restart genmaster 2>/dev/null || docker-compose restart genmaster 2>/dev/null
                    print_success "GenMaster restarted"
                else
                    print_info "Remember to restart GenMaster for changes to take effect:"
                    echo -e "    ${CYAN}docker compose restart genmaster${NC}"
                fi
            fi

            echo ""
            exit 0
            ;;
    esac

    clear

    # Banner
    echo -e "${CYAN}"
    echo "╔═════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                     ║"
    echo "║   ██████╗ ███████╗███╗   ██╗███╗   ███╗ █████╗ ███████╗████████╗███████╗██████╗     ║"
    echo "║  ██╔════╝ ██╔════╝████╗  ██║████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝██╔══██╗    ║"
    echo "║  ██║  ███╗█████╗  ██╔██╗ ██║██╔████╔██║███████║███████╗   ██║   █████╗  ██████╔╝    ║"
    echo "║  ██║   ██║██╔══╝  ██║╚██╗██║██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝  ██╔══██╗    ║"
    echo "║  ╚██████╔╝███████╗██║ ╚████║██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗██║  ██║    ║"
    echo "║   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝    ║"
    echo "║                                                                                     ║"
    echo "║                          Interactive Setup v${SCRIPT_VERSION}                                   ║"
    echo "║                                                                                     ║"
    echo "╚═════════════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

  #  print_header "GenMaster Setup v${SCRIPT_VERSION}"

    # Auto-confirm mode
    if [ "$PRECONFIG_MODE" = "true" ] && [ "$PRECONFIG_AUTO_CONFIRM" = "true" ]; then
        print_info "Running in non-interactive mode"
        INSTALL_MODE="fresh"
    else
        # Check existing installation
        local detected_version=$(detect_current_version)
        if [ "$detected_version" = "1.0" ]; then
            handle_version_detection
        else
            echo -e "  ${GRAY}This script sets up GenMaster generator control with:${NC}"
            echo -e "    • FastAPI backend + Vue.js frontend"
            echo -e "    • PostgreSQL 16 + Redis"
            echo -e "    • Nginx reverse proxy (HTTPS)"
            echo ""
            echo -e "  ${GRAY}Optional:${NC}"
            echo -e "    • Cloudflare Tunnel, Tailscale, Portainer"
            echo ""

            if ! confirm_prompt "Ready to begin?"; then
                exit 0
            fi

            handle_version_detection
        fi
    fi

    # Skip checks for reconfigure
    if [ "$INSTALL_MODE" != "reconfigure" ]; then
        # Check if running in LXC container and show warning
        if is_lxc_container; then
            show_lxc_warning
        fi

        # Resume check
        if check_resume; then
            print_info "Resuming from saved state..."
        fi

        # Hardware detection (sets MOCK_GPIO_MODE)
        detect_hardware_mode

        # System prep
        print_section "System Preparation"
        detect_os
        [ -n "$DISTRO" ] && print_success "OS: $DISTRO ($DISTRO_FAMILY)"

        if confirm_prompt "Update system packages?" "n"; then
            update_system
        fi

        install_required_utilities
        check_and_install_docker
        perform_system_checks
    fi

    if [ "$INSTALL_MODE" = "reconfigure" ]; then
        # CRITICAL: Backup FIRST before touching anything
        backup_existing_config

        [ -f "$CONFIG_FILE" ] && source "$CONFIG_FILE" 2>/dev/null
        # Load existing .env values so we don't re-ask for everything
        if [ -f "${SCRIPT_DIR}/.env" ]; then
            print_info "Loading existing configuration from .env..."
            set -a
            source "${SCRIPT_DIR}/.env"
            set +a
            # Map .env variable names to internal setup.sh variable names
            DB_NAME="${DATABASE_NAME:-$DB_NAME}"
            DB_USER="${DATABASE_USER:-$DB_USER}"
            DB_PASSWORD="${DATABASE_PASSWORD:-$DB_PASSWORD}"
            DNS_PROVIDER_NAME="${DNS_PROVIDER:-$DNS_PROVIDER_NAME}"
            GENSLAVE_API_URL="${SLAVE_API_URL:-$GENSLAVE_API_URL}"
            GENSLAVE_API_SECRET="${SLAVE_API_SECRET:-$GENSLAVE_API_SECRET}"
            WEBHOOK_URL="${WEBHOOK_BASE_URL:-$WEBHOOK_URL}"
            SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"
            WEBHOOK_SECRET="${WEBHOOK_SECRET:-$(openssl rand -hex 32)}"
            # Set optional services flags based on existing config
            # Check both token presence and ENABLED flags from config file
            [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ] && INSTALL_CLOUDFLARE_TUNNEL=true
            [ "$CLOUDFLARE_ENABLED" = "true" ] && INSTALL_CLOUDFLARE_TUNNEL=true
            [ -n "$TAILSCALE_AUTH_KEY" ] && INSTALL_TAILSCALE=true
            [ "$TAILSCALE_ENABLED" = "true" ] && INSTALL_TAILSCALE=true

            # Debug: show what was loaded
            if [ -n "$TAILSCALE_AUTH_KEY" ] || [ "$TAILSCALE_ENABLED" = "true" ]; then
                print_info "Tailscale config detected (AUTH_KEY: ${TAILSCALE_AUTH_KEY:+set}, ENABLED: ${TAILSCALE_ENABLED:-not set})"
            fi
            if [ -n "$CLOUDFLARE_TUNNEL_TOKEN" ] || [ "$CLOUDFLARE_ENABLED" = "true" ]; then
                print_info "Cloudflare config detected (TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN:+set}, ENABLED: ${CLOUDFLARE_ENABLED:-not set})"
            fi
            # Check if portainer is in docker-compose
            grep -q "portainer:" "${SCRIPT_DIR}/docker-compose.yaml" 2>/dev/null && INSTALL_PORTAINER=true
            # Check WiFi watchdog status from config
            [ "$WIFI_WATCHDOG_ENABLED" = "true" ] && INSTALL_WIFI_WATCHDOG=true
            # Check if wifi-watchdog service is installed on host
            systemctl is-enabled wifi-watchdog 2>/dev/null && INSTALL_WIFI_WATCHDOG=true
            # Set DNS certbot flags based on provider
            case $DNS_PROVIDER_NAME in
                cloudflare)
                    DNS_CERTBOT_IMAGE="certbot/dns-cloudflare:latest"
                    DNS_CERTBOT_FLAGS="--dns-cloudflare --dns-cloudflare-credentials /etc/letsencrypt/${DNS_CREDENTIALS_FILE} --dns-cloudflare-propagation-seconds 60"
                    ;;
                digitalocean)
                    DNS_CERTBOT_IMAGE="certbot/dns-digitalocean:latest"
                    DNS_CERTBOT_FLAGS="--dns-digitalocean --dns-digitalocean-credentials /etc/letsencrypt/${DNS_CREDENTIALS_FILE} --dns-digitalocean-propagation-seconds 60"
                    ;;
                route53)
                    DNS_CERTBOT_IMAGE="certbot/dns-route53:latest"
                    DNS_CERTBOT_FLAGS="--dns-route53"
                    ;;
                google)
                    DNS_CERTBOT_IMAGE="certbot/dns-google:latest"
                    DNS_CERTBOT_FLAGS="--dns-google --dns-google-credentials /etc/letsencrypt/${DNS_CREDENTIALS_FILE} --dns-google-propagation-seconds 120"
                    ;;
            esac
            print_success "Loaded existing configuration"
        fi
        detect_hardware_mode

        print_section "Reconfigure Options"
        echo -e "    ${CYAN}1)${NC} Domain"
        echo -e "    ${CYAN}2)${NC} Database"
        echo -e "    ${CYAN}3)${NC} GenSlave"
        echo -e "    ${CYAN}4)${NC} Optional services"
        echo -e "    ${CYAN}5)${NC} Regenerate configs"
        echo -e "    ${CYAN}6)${NC} Full reconfiguration"
        echo -e "    ${CYAN}7)${NC} ${YELLOW}Rollback to previous configuration${NC}"
        echo -e "    ${CYAN}0)${NC} Exit"
        echo ""

        local choice=""
        while [[ ! "$choice" =~ ^[0-7]$ ]]; do
            echo -ne "${WHITE}  Choice [0-7]${NC}: "
            read choice
        done

        case $choice in
            1) configure_domain ;;
            2) configure_database ;;
            3) configure_genslave ;;
            4) configure_optional_services ;;
            5) ;;
            6) INSTALL_MODE="fresh" ;;
            7) rollback_config; exit 0 ;;
            0) exit 0 ;;
        esac

        if [ "$INSTALL_MODE" = "reconfigure" ]; then
            generate_env_file
            generate_docker_compose
            generate_nginx_conf
            print_success "Configuration regenerated!"
            if confirm_prompt "Redeploy now?"; then
                deploy_stack
            fi
            # Install/update WiFi watchdog if enabled
            if [ "$INSTALL_WIFI_WATCHDOG" = true ]; then
                install_wifi_watchdog
            fi
            exit 0
        fi
    fi

    if [ "$INSTALL_MODE" = "fresh" ]; then
        [ "$CURRENT_STEP" -lt 1 ] && { configure_domain; save_state "Domain" 1; }
        [ "$CURRENT_STEP" -lt 2 ] && { configure_dns_provider; save_state "DNS Provider" 2; }
        [ "$CURRENT_STEP" -lt 3 ] && { configure_email; save_state "Email" 3; }
        [ "$CURRENT_STEP" -lt 4 ] && { configure_database; save_state "Database" 4; }
        [ "$CURRENT_STEP" -lt 5 ] && { configure_containers; save_state "Containers" 5; }
        [ "$CURRENT_STEP" -lt 6 ] && { configure_build_method; save_state "Build Method" 6; }
        [ "$CURRENT_STEP" -lt 7 ] && { configure_timezone; save_state "Timezone" 7; }
        [ "$CURRENT_STEP" -lt 8 ] && { generate_secret_key; save_state "Secret Key" 8; }
        [ "$CURRENT_STEP" -lt 9 ] && { configure_genslave; save_state "GenSlave" 9; }
        [ "$CURRENT_STEP" -lt 10 ] && { configure_webhooks; save_state "Webhooks" 10; }
        [ "$CURRENT_STEP" -lt 11 ] && { configure_generator_info; save_state "Generator Info" 11; }
        [ "$CURRENT_STEP" -lt 12 ] && { configure_optional_services; save_state "Services" 12; }

        if ! show_configuration_summary; then
            print_error "Cancelled"
            exit 1
        fi

        print_section "Generating Configuration"
        generate_env_file
        generate_docker_compose
        generate_nginx_conf

        # Save setup config
        cat > "${CONFIG_FILE}" << EOF
DOMAIN=${DOMAIN}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
TIMEZONE=${TIMEZONE}
GENSLAVE_ENABLED=${GENSLAVE_ENABLED}
MOCK_GPIO_MODE=${MOCK_GPIO_MODE}
PORTAINER_ENABLED=${INSTALL_PORTAINER}
CLOUDFLARE_ENABLED=${INSTALL_CLOUDFLARE_TUNNEL}
TAILSCALE_ENABLED=${INSTALL_TAILSCALE}
WIFI_WATCHDOG_ENABLED=${INSTALL_WIFI_WATCHDOG}
USE_DOCKER_HUB_IMAGE=${USE_DOCKER_HUB_IMAGE}
EOF
        chmod 600 "${CONFIG_FILE}"

        print_success "Configuration complete!"

        if confirm_prompt "Deploy now?"; then
            deploy_stack
            # Install WiFi watchdog (runs on host, not in container)
            install_wifi_watchdog
        else
            print_info "Run 'docker compose up -d' when ready."
            # Still install WiFi watchdog even if not deploying containers
            if [ "$INSTALL_WIFI_WATCHDOG" = true ]; then
                install_wifi_watchdog
            fi
        fi
    fi

    clear_state
}

main "$@"
