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

# GenSlave configuration
GENSLAVE_ENABLED=true
GENSLAVE_API_URL=""
GENSLAVE_API_SECRET=""

# Mock GPIO mode (auto-detected based on hardware)
MOCK_GPIO_MODE=false

# Auto-generated credential tracking (for display at end of setup)
AUTOGEN_DB_PASSWORD=false
AUTOGEN_SECRET_KEY=false
AUTOGEN_SLAVE_SECRET=false

# Internal IP ranges that get full access (space-separated CIDR blocks)
DEFAULT_INTERNAL_IP_RANGES="127.0.0.1/32 100.64.0.0/10 172.16.0.0/12 10.0.0.0/8 192.168.0.0/16"
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
SAVED_WEBHOOK_URL="$WEBHOOK_URL"
SAVED_WEBHOOK_SECRET="$WEBHOOK_SECRET"
SAVED_INSTALL_PORTAINER="$INSTALL_PORTAINER"
SAVED_INSTALL_CLOUDFLARE_TUNNEL="$INSTALL_CLOUDFLARE_TUNNEL"
SAVED_CLOUDFLARE_TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN"
SAVED_INSTALL_TAILSCALE="$INSTALL_TAILSCALE"
SAVED_TAILSCALE_AUTH_KEY="$TAILSCALE_AUTH_KEY"
SAVED_TAILSCALE_HOSTNAME="$TAILSCALE_HOSTNAME"
SAVED_MOCK_GPIO_MODE="$MOCK_GPIO_MODE"
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
        WEBHOOK_URL="${SAVED_WEBHOOK_URL:-}"
        WEBHOOK_SECRET="${SAVED_WEBHOOK_SECRET:-}"
        INSTALL_PORTAINER="${SAVED_INSTALL_PORTAINER:-false}"
        INSTALL_CLOUDFLARE_TUNNEL="${SAVED_INSTALL_CLOUDFLARE_TUNNEL:-false}"
        CLOUDFLARE_TUNNEL_TOKEN="${SAVED_CLOUDFLARE_TUNNEL_TOKEN:-}"
        INSTALL_TAILSCALE="${SAVED_INSTALL_TAILSCALE:-false}"
        TAILSCALE_AUTH_KEY="${SAVED_TAILSCALE_AUTH_KEY:-}"
        TAILSCALE_HOSTNAME="${SAVED_TAILSCALE_HOSTNAME:-}"
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
    TIMEZONE="${TIMEZONE:-America/Phoenix}"

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

    if [ -f "${SCRIPT_DIR}/docker-compose.yml" ]; then
        if grep -q "genmaster" "${SCRIPT_DIR}/docker-compose.yml" 2>/dev/null; then
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

backup_existing_config() {
    local backup_dir="${SCRIPT_DIR}/backups"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    mkdir -p "$backup_dir"
    print_info "Backing up existing configuration..."

    [ -f "${SCRIPT_DIR}/.env" ] && cp "${SCRIPT_DIR}/.env" "${backup_dir}/.env.${timestamp}"
    [ -f "${SCRIPT_DIR}/docker-compose.yml" ] && cp "${SCRIPT_DIR}/docker-compose.yml" "${backup_dir}/docker-compose.yml.${timestamp}"
    [ -f "${SCRIPT_DIR}/nginx/nginx.conf" ] && cp "${SCRIPT_DIR}/nginx/nginx.conf" "${backup_dir}/nginx.conf.${timestamp}"

    print_success "Backup complete: ${backup_dir}"
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

configure_containers() {
    print_section "Container Names"

    POSTGRES_CONTAINER="$DEFAULT_POSTGRES_CONTAINER"
    GENMASTER_CONTAINER="$DEFAULT_GENMASTER_CONTAINER"
    NGINX_CONTAINER="$DEFAULT_NGINX_CONTAINER"
    REDIS_CONTAINER="$DEFAULT_REDIS_CONTAINER"

    print_info "Using default container names"
}

configure_timezone() {
    print_section "Timezone Configuration"

    # In preconfig mode, timezone is already set by load_preconfig
    if [ "$PRECONFIG_MODE" = "true" ] && [ -n "$TIMEZONE" ]; then
        print_info "Using pre-configured timezone: $TIMEZONE"
        return
    fi

    local default_tz="America/Phoenix"
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

    if [ "$PRECONFIG_MODE" = "true" ]; then
        if [ "$GENSLAVE_ENABLED" = "true" ]; then
            print_info "GenSlave: $GENSLAVE_API_URL"
        else
            print_info "GenSlave: Disabled"
        fi
        return
    fi

    echo ""
    echo -e "  ${GRAY}GenSlave controls the generator relay on a Pi Zero 2W.${NC}"
    echo ""

    if confirm_prompt "Enable GenSlave communication?" "y"; then
        GENSLAVE_ENABLED=true

        while true; do
            echo -ne "${WHITE}  GenSlave API URL (e.g., http://genslave.local:8001)${NC}: "
            read GENSLAVE_API_URL

            if [ -n "$GENSLAVE_API_URL" ]; then
                break
            fi
            print_error "URL is required"
        done

        if [ -z "$GENSLAVE_API_SECRET" ]; then
            GENSLAVE_API_SECRET=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
            AUTOGEN_SLAVE_SECRET=true
        fi

        print_success "GenSlave configured"
    else
        GENSLAVE_ENABLED=false
        print_info "GenSlave disabled (UI-only mode)"
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

configure_optional_services() {
    print_section "Optional Services"

    if [ "$PRECONFIG_MODE" = "true" ]; then
        print_info "Using pre-configured services"
        return
    fi

    # Cloudflare Tunnel
    print_subsection
    echo -e "  ${WHITE}${BOLD}Cloudflare Tunnel${NC}"
    echo -e "  ${GRAY}Secure HTTPS access without exposing ports.${NC}"
    echo ""

    if confirm_prompt "Enable Cloudflare Tunnel?" "n"; then
        INSTALL_CLOUDFLARE_TUNNEL=true
        echo -ne "${WHITE}  Tunnel token${NC}: "
        read CLOUDFLARE_TUNNEL_TOKEN
        print_success "Cloudflare Tunnel enabled"
    fi

    # Tailscale
    print_subsection
    echo -e "  ${WHITE}${BOLD}Tailscale VPN${NC}"
    echo -e "  ${GRAY}Private mesh VPN for secure remote access.${NC}"
    echo ""

    if confirm_prompt "Enable Tailscale?" "n"; then
        INSTALL_TAILSCALE=true
        echo -ne "${WHITE}  Auth key${NC}: "
        read TAILSCALE_AUTH_KEY
        prompt_with_default "Hostname" "genmaster" "TAILSCALE_HOSTNAME"
        print_success "Tailscale enabled"
    fi

    # Portainer
    print_subsection
    echo -e "  ${WHITE}${BOLD}Portainer${NC}"
    echo -e "  ${GRAY}Web-based container management.${NC}"
    echo ""

    if confirm_prompt "Enable Portainer?" "n"; then
        INSTALL_PORTAINER=true
        print_success "Portainer enabled"
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

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379

# GenSlave Communication
GENSLAVE_ENABLED=${GENSLAVE_ENABLED}
SLAVE_API_URL=${GENSLAVE_API_URL}
SLAVE_API_SECRET=${GENSLAVE_API_SECRET}

# Webhook Configuration
WEBHOOK_BASE_URL=${WEBHOOK_URL}
WEBHOOK_SECRET=${WEBHOOK_SECRET}
WEBHOOK_ENABLED=$([ -n "$WEBHOOK_URL" ] && echo "true" || echo "false")

# Heartbeat Settings
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# GPIO Configuration
GPIO_PIN_VICTRON=17
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
        cat >> "${SCRIPT_DIR}/.env" << EOF

# Tailscale VPN
TAILSCALE_AUTHKEY=${TAILSCALE_AUTH_KEY}
TAILSCALE_HOSTNAME=${TAILSCALE_HOSTNAME}
EOF
    fi

    chmod 600 "${SCRIPT_DIR}/.env"
    print_success ".env generated"

    if [ "$MOCK_GPIO_MODE" = true ]; then
        print_info "Mock GPIO mode enabled in .env (APP_ENV=development)"
    fi
}

generate_docker_compose() {
    print_info "Generating docker-compose.yml..."

    cat > "${SCRIPT_DIR}/docker-compose.yml" << 'EOF'
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
  genmaster:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ${GENMASTER_CONTAINER:-genmaster}
    restart: unless-stopped
    environment:
      - APP_ENV=${APP_ENV:-production}
      - MOCK_GPIO_MODE=${MOCK_GPIO_MODE:-false}
      - DATABASE_URL=postgresql+asyncpg://${DATABASE_USER:-genmaster}:${DATABASE_PASSWORD}@db:5432/${DATABASE_NAME:-genmaster}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - GENSLAVE_ENABLED=${GENSLAVE_ENABLED:-true}
      - SLAVE_API_URL=${SLAVE_API_URL}
      - SLAVE_API_SECRET=${SLAVE_API_SECRET}
      - WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL}
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
      - WEBHOOK_ENABLED=${WEBHOOK_ENABLED:-false}
      - TZ=${TIMEZONE:-America/Phoenix}
    volumes:
      - genmaster_logs:/app/logs
      - genmaster_data:/app/data
    networks:
      - genmaster-internal
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
  nginx:
    image: nginx:alpine
    container_name: ${NGINX_CONTAINER:-genmaster_nginx}
    restart: unless-stopped
    ports:
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - nginx_logs:/var/log/nginx
    networks:
      - genmaster-internal
      - genmaster-external
    depends_on:
      - genmaster
EOF

    # Add Cloudflare Tunnel if enabled
    if [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ]; then
        cat >> "${SCRIPT_DIR}/docker-compose.yml" << 'EOF'

  # ===========================================================================
  # Cloudflare Tunnel
  # ===========================================================================
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: genmaster_cloudflared
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - genmaster-external
    profiles:
      - cloudflare
EOF
    fi

    # Add Tailscale if enabled
    if [ "$INSTALL_TAILSCALE" = true ]; then
        cat >> "${SCRIPT_DIR}/docker-compose.yml" << 'EOF'

  # ===========================================================================
  # Tailscale VPN
  # ===========================================================================
  tailscale:
    image: tailscale/tailscale:latest
    container_name: genmaster_tailscale
    restart: unless-stopped
    hostname: ${TAILSCALE_HOSTNAME:-genmaster}
    environment:
      - TS_AUTHKEY=${TAILSCALE_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=true
    volumes:
      - tailscale_state:/var/lib/tailscale
    cap_add:
      - NET_ADMIN
      - SYS_MODULE
    networks:
      - genmaster-external
    profiles:
      - tailscale

volumes:
  tailscale_state:
EOF
    fi

    # Add Portainer if enabled
    if [ "$INSTALL_PORTAINER" = true ]; then
        cat >> "${SCRIPT_DIR}/docker-compose.yml" << 'EOF'

  # ===========================================================================
  # Portainer Container Management
  # ===========================================================================
  portainer:
    image: portainer/portainer-ce:latest
    container_name: genmaster_portainer
    restart: unless-stopped
    command: --base-url /portainer
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer_data:/data
    networks:
      - genmaster-internal
    profiles:
      - portainer

volumes:
  portainer_data:
EOF
    fi

    print_success "docker-compose.yml generated"
}

generate_nginx_conf() {
    print_info "Generating nginx configuration..."

    mkdir -p "${SCRIPT_DIR}/nginx"
    mkdir -p "${SCRIPT_DIR}/nginx/ssl"

    # Build internal IP list
    local internal_ips=""
    for ip in $DEFAULT_INTERNAL_IP_RANGES; do
        internal_ips="${internal_ips}        $ip internal;\n"
    done

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

    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=30r/s;

    # IP-based access control
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

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;

        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "SAMEORIGIN" always;

        location /api/ {
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
            proxy_pass http://genmaster;
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400s;
        }

        location / {
            proxy_pass http://genmaster;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /healthz {
            access_log off;
            return 200 "healthy\n";
        }
EOF

    # Add Portainer if enabled
    if [ "$INSTALL_PORTAINER" = true ]; then
        cat >> "${SCRIPT_DIR}/nginx/nginx.conf" << 'EOF'

        location /portainer/ {
            if ($access_level = "external") {
                return 403;
            }
            proxy_pass http://genmaster_portainer:9000/;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }
EOF
    fi

    cat >> "${SCRIPT_DIR}/nginx/nginx.conf" << 'EOF'
    }
}
EOF

    print_success "nginx.conf generated"

    # Generate self-signed SSL cert
    if [ ! -f "${SCRIPT_DIR}/nginx/ssl/cert.pem" ]; then
        print_info "Generating self-signed SSL certificate..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "${SCRIPT_DIR}/nginx/ssl/key.pem" \
            -out "${SCRIPT_DIR}/nginx/ssl/cert.pem" \
            -subj "/CN=${DOMAIN}" 2>/dev/null
        chmod 600 "${SCRIPT_DIR}/nginx/ssl/key.pem"
        print_success "SSL certificate generated"
    fi
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

    local profiles=""
    [ "$INSTALL_CLOUDFLARE_TUNNEL" = true ] && profiles="$profiles --profile cloudflare"
    [ "$INSTALL_TAILSCALE" = true ] && profiles="$profiles --profile tailscale"
    [ "$INSTALL_PORTAINER" = true ] && profiles="$profiles --profile portainer"

    print_info "Building and starting containers..."
    $docker_compose_cmd $profiles up -d --build

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
    print_header "Deployment Complete!"

    echo -e "  ${WHITE}${BOLD}Access GenMaster:${NC}"
    echo -e "    URL: ${CYAN}https://${DOMAIN}${NC}"
    [ "$INSTALL_TAILSCALE" = true ] && echo -e "    Tailscale: ${CYAN}https://${TAILSCALE_HOSTNAME}${NC}"
    echo ""

    if [ "$AUTOGEN_DB_PASSWORD" = true ] || [ "$AUTOGEN_SLAVE_SECRET" = true ]; then
        echo -e "  ${WHITE}${BOLD}Auto-Generated Credentials:${NC}"
        echo -e "  ${YELLOW}⚠ Save these - they won't be shown again!${NC}"
        echo ""
        [ "$AUTOGEN_DB_PASSWORD" = true ] && echo -e "    Database Password: ${CYAN}$DB_PASSWORD${NC}"
        [ "$AUTOGEN_SLAVE_SECRET" = true ] && echo -e "    GenSlave Secret: ${CYAN}$GENSLAVE_API_SECRET${NC}"
        echo ""
    fi

    echo -e "  ${WHITE}${BOLD}Commands:${NC}"
    echo -e "    Logs:    ${CYAN}docker compose logs -f${NC}"
    echo -e "    Stop:    ${CYAN}docker compose down${NC}"
    echo -e "    Restart: ${CYAN}docker compose restart${NC}"
    echo ""

    if [ "$MOCK_GPIO_MODE" = true ]; then
        echo -e "  ${YELLOW}ℹ Mock GPIO Mode Active${NC}"
        echo -e "    Dev API available at /api/dev/*"
        echo -e "    Test: ${CYAN}curl -X POST http://localhost:8000/api/dev/gpio/victron-signal -H 'Content-Type: application/json' -d '{\"active\": true}'${NC}"
    else
        echo -e "  ${GREEN}✓ Real GPIO Mode (Raspberry Pi)${NC}"
    fi
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
    echo "  --version           Show version"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    PRECONFIG_MODE=false
    PRECONFIG_AUTO_CONFIRM=false

    case "${1:-}" in
        --help|-h) show_help; exit 0 ;;
        --version|-v) echo "v${SCRIPT_VERSION}"; exit 0 ;;
        --config)
            [ -z "${2:-}" ] && { print_error "Usage: ./setup.sh --config <file>"; exit 1; }
            load_preconfig "$2"
            ;;
    esac

    clear

    # Banner
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                           ║"
    echo "║   ██████╗ ███████╗███╗   ██╗███╗   ███╗ █████╗ ███████╗████████╗███████╗  ║"
    echo "║  ██╔════╝ ██╔════╝████╗  ██║████╗ ████║██╔══██╗██╔════╝╚══██╔══╝██╔════╝  ║"
    echo "║  ██║  ███╗█████╗  ██╔██╗ ██║██╔████╔██║███████║███████╗   ██║   █████╗    ║"
    echo "║  ██║   ██║██╔══╝  ██║╚██╗██║██║╚██╔╝██║██╔══██║╚════██║   ██║   ██╔══╝    ║"
    echo "║  ╚██████╔╝███████╗██║ ╚████║██║ ╚═╝ ██║██║  ██║███████║   ██║   ███████╗  ║"
    echo "║   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝  ║"
    echo "║                                                                           ║"
    echo "║                     Interactive Setup v${SCRIPT_VERSION}                          ║"
    echo "║                                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    print_header "GenMaster Setup v${SCRIPT_VERSION}"

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
        [ -f "$CONFIG_FILE" ] && source "$CONFIG_FILE" 2>/dev/null
        detect_hardware_mode

        print_section "Reconfigure Options"
        echo -e "    ${CYAN}1)${NC} Domain"
        echo -e "    ${CYAN}2)${NC} Database"
        echo -e "    ${CYAN}3)${NC} GenSlave"
        echo -e "    ${CYAN}4)${NC} Optional services"
        echo -e "    ${CYAN}5)${NC} Regenerate configs"
        echo -e "    ${CYAN}6)${NC} Full reconfiguration"
        echo -e "    ${CYAN}0)${NC} Exit"
        echo ""

        local choice=""
        while [[ ! "$choice" =~ ^[0-6]$ ]]; do
            echo -ne "${WHITE}  Choice [0-6]${NC}: "
            read choice
        done

        case $choice in
            1) configure_domain ;;
            2) configure_database ;;
            3) configure_genslave ;;
            4) configure_optional_services ;;
            5) ;;
            6) INSTALL_MODE="fresh" ;;
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
            exit 0
        fi
    fi

    if [ "$INSTALL_MODE" = "fresh" ]; then
        [ "$CURRENT_STEP" -lt 1 ] && { configure_domain; save_state "Domain" 1; }
        [ "$CURRENT_STEP" -lt 2 ] && { configure_database; save_state "Database" 2; }
        [ "$CURRENT_STEP" -lt 3 ] && { configure_containers; save_state "Containers" 3; }
        [ "$CURRENT_STEP" -lt 4 ] && { configure_timezone; save_state "Timezone" 4; }
        [ "$CURRENT_STEP" -lt 5 ] && { generate_secret_key; save_state "Secret Key" 5; }
        [ "$CURRENT_STEP" -lt 6 ] && { configure_genslave; save_state "GenSlave" 6; }
        [ "$CURRENT_STEP" -lt 7 ] && { configure_webhooks; save_state "Webhooks" 7; }
        [ "$CURRENT_STEP" -lt 8 ] && { configure_optional_services; save_state "Services" 8; }

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
EOF
        chmod 600 "${CONFIG_FILE}"

        print_success "Configuration complete!"

        if confirm_prompt "Deploy now?"; then
            deploy_stack
        else
            print_info "Run 'docker compose up -d' when ready."
        fi
    fi

    clear_state
}

main "$@"
