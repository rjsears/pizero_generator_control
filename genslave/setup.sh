#!/bin/bash
#
# GenSlave Setup Script
# Generator Control System - Slave Controller Installation
#
# This script provides a lightweight native installation for GenSlave on Pi Zero 2W.
# It installs Python dependencies and configures systemd for auto-start.
#
# Key features:
# - Native Python installation (no Docker to save RAM)
# - SQLite database (file-based, zero overhead)
# - Systemd service management
# - Tailscale VPN configuration
# - Hardware validation for Automation Hat Mini
#
# Usage:
#   Interactive:  ./setup.sh
#   Preconfig:    ./setup.sh --preconfig /path/to/preconfig.conf
#
# Author: rjsears
# License: MIT

set -o pipefail

# =============================================================================
# Script Configuration
# =============================================================================
SCRIPT_VERSION="1.0.0"
SCRIPT_NAME="GenSlave Setup"
INSTALL_DIR="/opt/genslave"
CONFIG_FILE="${INSTALL_DIR}/.env"
STATE_FILE="${INSTALL_DIR}/.setup_state"
LOG_FILE="/var/log/genslave-setup.log"

# Python version
PYTHON_VERSION="3.11"

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
DEBUG_MODE=false

# Installation state
STATE_SYSTEM_PREPARED=false
STATE_PYTHON_INSTALLED=false
STATE_HARDWARE_VALIDATED=false
STATE_TAILSCALE_CONFIGURED=false
STATE_ENV_CONFIGURED=false
STATE_SERVICE_INSTALLED=false

# Configuration values
ENABLE_TAILSCALE=false
TAILSCALE_AUTHKEY=""
TAILSCALE_HOSTNAME="genslave"
API_SECRET=""
MASTER_API_URL=""
WEBHOOK_BASE_URL=""
WEBHOOK_SECRET=""

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

log_info() { log "INFO" "$*"; }
log_warn() { log "WARN" "$*"; }
log_error() { log "ERROR" "$*"; }

print_header() {
    clear
    echo -e "${CYAN}"
    echo "╔═════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                 ║"
    echo "║   ██████╗ ███████╗███╗   ██╗███████╗██╗      █████╗ ██╗   ██╗███████╗           ║"
    echo "║  ██╔════╝ ██╔════╝████╗  ██║██╔════╝██║     ██╔══██╗██║   ██║██╔════╝           ║"
    echo "║  ██║  ███╗█████╗  ██╔██╗ ██║███████╗██║     ███████║██║   ██║█████╗             ║"
    echo "║  ██║   ██║██╔══╝  ██║╚██╗██║╚════██║██║     ██╔══██║╚██╗ ██╔╝██╔══╝             ║"
    echo "║  ╚██████╔╝███████╗██║ ╚████║███████║███████╗██║  ██║ ╚████╔╝ ███████╗           ║"
    echo "║   ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝           ║"
    echo "║                                                                                 ║"
    echo "║                   Generator Control System - Slave Setup                        ║"
    echo "║                              Version ${SCRIPT_VERSION}                                  ║"
    echo "║                                                                                 ║"
    echo "╚═════════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
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

print_step() {
    local step_num="$1"
    local step_desc="$2"
    echo -e "  ${CYAN}[${step_num}]${NC} ${step_desc}"
}

print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "  ${RED}✗${NC} $1"; }
print_info() { echo -e "  ${BLUE}ℹ${NC} $1"; }

confirm() {
    local prompt="$1"
    local default="${2:-n}"
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

prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local display_default=""
    if [ -n "$default" ]; then
        display_default=" [${default}]"
    fi
    echo -en "  ${MAGENTA}?${NC} ${prompt}${display_default}: "
    read -r input
    input=${input:-$default}
    eval "$var_name=\"$input\""
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

prompt_secret() {
    local prompt="$1"
    local var_name="$2"
    local allow_empty="${3:-false}"
    while true; do
        echo -en "  ${MAGENTA}?${NC} ${prompt}: "
        read_masked_token
        local input="$MASKED_INPUT"
        if [ -z "$input" ] && [ "$allow_empty" = "false" ]; then
            print_error "This field cannot be empty"
            continue
        fi
        eval "$var_name=\"$input\""
        return 0
    done
}

generate_secret() {
    local length="${1:-32}"
    openssl rand -hex "$length"
}

command_exists() {
    command -v "$1" &> /dev/null
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        echo -e "  ${YELLOW}Please run: sudo $0${NC}"
        exit 1
    fi
}

# =============================================================================
# State Management
# =============================================================================

save_state() {
    cat > "$STATE_FILE" << EOF
# GenSlave Setup State - DO NOT EDIT MANUALLY
STATE_SYSTEM_PREPARED=${STATE_SYSTEM_PREPARED}
STATE_PYTHON_INSTALLED=${STATE_PYTHON_INSTALLED}
STATE_HARDWARE_VALIDATED=${STATE_HARDWARE_VALIDATED}
STATE_TAILSCALE_CONFIGURED=${STATE_TAILSCALE_CONFIGURED}
STATE_ENV_CONFIGURED=${STATE_ENV_CONFIGURED}
STATE_SERVICE_INSTALLED=${STATE_SERVICE_INSTALLED}
ENABLE_TAILSCALE=${ENABLE_TAILSCALE}
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME}"
MASTER_API_URL="${MASTER_API_URL}"
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
    fi

    # Check Raspberry Pi
    print_step "2" "Checking hardware..."
    if [ -f /proc/device-tree/model ]; then
        local model=$(cat /proc/device-tree/model | tr -d '\0')
        print_success "Hardware: $model"
    else
        print_warning "Could not detect hardware model"
    fi

    # Check memory
    print_step "3" "Checking available memory..."
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    local avail_mem=$(free -m | awk 'NR==2{print $7}')
    print_success "Total: ${total_mem}MB, Available: ${avail_mem}MB"

    if [ "$total_mem" -lt 400 ]; then
        print_warning "Low memory detected. GenSlave is optimized for Pi Zero 2W (512MB)"
    fi

    # Update package lists
    print_step "4" "Updating package lists..."
    apt-get update -qq
    print_success "Package lists updated"

    # Install system dependencies
    print_step "5" "Installing system dependencies..."
    apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        libgpiod2 \
        i2c-tools \
        curl \
        jq \
        openssl \
        > /dev/null 2>&1
    print_success "System dependencies installed"

    # Enable required interfaces
    print_step "6" "Enabling hardware interfaces..."

    # Enable I2C
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
        print_info "I2C enabled (reboot required)"
    fi

    # Enable SPI
    if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
        echo "dtparam=spi=on" >> /boot/config.txt
        print_info "SPI enabled (reboot required)"
    fi

    print_success "Hardware interfaces configured"

    # Create installation directory
    print_step "7" "Creating installation directories..."
    mkdir -p "$INSTALL_DIR"/{app,data,logs,backups}
    chown -R pi:pi "$INSTALL_DIR"
    print_success "Created $INSTALL_DIR"

    STATE_SYSTEM_PREPARED=true
    save_state
    print_success "System preparation complete"
}

# =============================================================================
# Python Environment Setup
# =============================================================================

install_python_environment() {
    print_section "Python Environment Setup"

    print_step "1" "Creating Python virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    print_success "Virtual environment created"

    print_step "2" "Upgrading pip..."
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip setuptools wheel > /dev/null 2>&1
    print_success "Pip upgraded"

    print_step "3" "Creating requirements.txt..."
    cat > "$INSTALL_DIR/requirements.txt" << 'EOF'
# GenSlave Requirements
# Core Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database (SQLite - no external server needed)
sqlalchemy>=2.0.0
aiosqlite>=0.19.0

# Data Validation
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Hardware Control (Automation Hat Mini)
automationhat>=0.4.0
RPi.GPIO>=0.7.0
spidev>=3.5

# LCD Display
Pillow>=10.0.0
ST7735>=0.0.4

# HTTP Client (for webhooks)
httpx>=0.26.0

# System Monitoring
psutil>=5.9.0

# Configuration
python-dotenv>=1.0.0
EOF
    print_success "Requirements file created"

    print_step "4" "Installing Python dependencies..."
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" > /dev/null 2>&1
    print_success "Python dependencies installed"

    STATE_PYTHON_INSTALLED=true
    save_state
}

# =============================================================================
# Hardware Validation
# =============================================================================

validate_hardware() {
    print_section "Hardware Validation"

    print_step "1" "Checking I2C bus..."
    if i2cdetect -y 1 &> /dev/null; then
        print_success "I2C bus is accessible"
    else
        print_warning "I2C bus not accessible (may need reboot)"
    fi

    print_step "2" "Checking SPI..."
    if [ -e /dev/spidev0.0 ]; then
        print_success "SPI device found"
    else
        print_warning "SPI device not found (may need reboot)"
    fi

    print_step "3" "Checking GPIO access..."
    if [ -e /dev/gpiomem ]; then
        print_success "GPIO memory accessible"
    else
        print_warning "GPIO memory not accessible"
    fi

    print_step "4" "Testing Automation Hat Mini..."
    local hat_result
    hat_result=$("$INSTALL_DIR/venv/bin/python3" << 'PYEOF' 2>&1
try:
    import automationhat
    if automationhat.is_automation_hat() or automationhat.is_automation_hat_mini():
        print("SUCCESS:Automation Hat Mini detected")
    else:
        print("WARNING:Automation Hat library loaded but no hat detected")
except ImportError as e:
    print(f"ERROR:Module not found - {e}")
except Exception as e:
    print(f"ERROR:{e}")
PYEOF
)

    if [[ "$hat_result" == SUCCESS:* ]]; then
        print_success "${hat_result#SUCCESS:}"
    elif [[ "$hat_result" == WARNING:* ]]; then
        print_warning "${hat_result#WARNING:}"
    else
        print_error "${hat_result#ERROR:}"
        print_warning "GenSlave may not function correctly without Automation Hat Mini"
    fi

    STATE_HARDWARE_VALIDATED=true
    save_state
}

# =============================================================================
# Tailscale Configuration
# =============================================================================

configure_tailscale() {
    print_section "Tailscale VPN Configuration"

    echo ""
    echo -e "  ${GRAY}Tailscale provides private access to your GenSlave instance${NC}"
    echo -e "  ${GRAY}over a secure mesh VPN network for communication with GenMaster.${NC}"
    echo ""

    if ! confirm "Configure Tailscale for private VPN access?"; then
        ENABLE_TAILSCALE=false
        STATE_TAILSCALE_CONFIGURED=true
        save_state
        return 0
    fi

    ENABLE_TAILSCALE=true

    print_subsection
    echo -e "${WHITE}  Tailscale Configuration${NC}"
    echo ""
    echo -e "  ${GRAY}Requirements:${NC}"
    echo -e "    • Tailscale account"
    echo -e "    • Auth key from: https://login.tailscale.com/admin/settings/keys${NC}"
    echo ""

    print_step "1" "Installing Tailscale..."
    if ! command_exists tailscale; then
        curl -fsSL https://tailscale.com/install.sh | sh
    fi
    print_success "Tailscale installed"

    echo ""
    echo -ne "${WHITE}  Enter your Tailscale auth key${NC}: "
    read_masked_token
    TAILSCALE_AUTHKEY="$MASKED_INPUT"

    if [ -z "$TAILSCALE_AUTHKEY" ]; then
        print_warning "No auth key provided - Tailscale disabled"
        ENABLE_TAILSCALE=false
        STATE_TAILSCALE_CONFIGURED=true
        save_state
        return 0
    fi

    print_success "Auth key accepted"

    echo ""
    echo -ne "${WHITE}  Tailscale hostname [genslave]${NC}: "
    read ts_hostname
    TAILSCALE_HOSTNAME=${ts_hostname:-genslave}

    print_step "2" "Authenticating with Tailscale..."
    tailscale up --authkey="$TAILSCALE_AUTHKEY" --hostname="$TAILSCALE_HOSTNAME"
    print_success "Tailscale authenticated"

    print_step "3" "Verifying Tailscale connection..."
    if tailscale status &> /dev/null; then
        local ts_ip=$(tailscale ip -4)
        print_success "Tailscale IP: $ts_ip"
        echo ""
        print_info "Your GenSlave instance will be accessible at: ${TAILSCALE_HOSTNAME}.your-tailnet.ts.net"
    else
        print_warning "Tailscale may not be fully connected yet"
    fi

    STATE_TAILSCALE_CONFIGURED=true
    save_state
}

# =============================================================================
# Environment Configuration
# =============================================================================

configure_environment() {
    print_section "Environment Configuration"

    print_step "1" "Gathering GenMaster connection details..."

    if [ "$ENABLE_TAILSCALE" = true ]; then
        prompt_input "GenMaster API URL (Tailscale hostname)" "http://genmaster:8000" MASTER_API_URL
    else
        prompt_input "GenMaster API URL" "" MASTER_API_URL
    fi

    print_step "2" "Configuring API secret..."
    echo ""
    echo "  This secret must match the SLAVE_API_SECRET configured on GenMaster."
    echo ""
    prompt_secret "Enter API Secret (from GenMaster)" API_SECRET

    print_step "3" "Configuring webhooks (optional)..."
    if confirm "Would you like to configure webhook notifications?"; then
        prompt_input "Webhook URL" "" WEBHOOK_BASE_URL
        prompt_secret "Webhook Secret" WEBHOOK_SECRET true
    fi

    print_step "4" "Creating environment configuration..."

    cat > "$CONFIG_FILE" << EOF
# GenSlave Environment Configuration
# Generated by setup.sh on $(date)

APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=$(generate_secret 32)

# Database (SQLite)
DATABASE_PATH=${INSTALL_DIR}/data/genslave.db

# API Authentication (must match GenMaster)
API_SECRET=${API_SECRET}

# Heartbeat settings
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# Webhooks
WEBHOOK_BASE_URL=${WEBHOOK_BASE_URL}
WEBHOOK_SECRET=${WEBHOOK_SECRET}

# GenMaster reference
MASTER_API_URL=${MASTER_API_URL}

# LCD Display
LCD_ENABLED=true
LCD_BRIGHTNESS=100

# Logging
LOG_PATH=${INSTALL_DIR}/logs/genslave.log
LOG_LEVEL=INFO
EOF

    chmod 600 "$CONFIG_FILE"
    chown pi:pi "$CONFIG_FILE"
    print_success "Environment configuration created"

    STATE_ENV_CONFIGURED=true
    save_state
}

# =============================================================================
# Service Installation
# =============================================================================

install_service() {
    print_section "Systemd Service Installation"

    print_step "1" "Creating systemd service file..."

    cat > /etc/systemd/system/genslave.service << EOF
[Unit]
Description=GenSlave Generator Controller
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=${INSTALL_DIR}/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Resource limits for Pi Zero 2W
MemoryMax=200M
MemoryHigh=150M

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${INSTALL_DIR}/data ${INSTALL_DIR}/logs

# GPIO access
SupplementaryGroups=gpio i2c spi

# Logging
StandardOutput=append:${INSTALL_DIR}/logs/genslave.log
StandardError=append:${INSTALL_DIR}/logs/genslave.log

[Install]
WantedBy=multi-user.target
EOF

    print_success "Service file created"

    print_step "2" "Creating log rotation configuration..."

    cat > /etc/logrotate.d/genslave << EOF
${INSTALL_DIR}/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 pi pi
    postrotate
        systemctl restart genslave > /dev/null 2>&1 || true
    endscript
}
EOF

    print_success "Log rotation configured"

    print_step "3" "Reloading systemd..."
    systemctl daemon-reload
    print_success "Systemd reloaded"

    print_step "4" "Enabling service..."
    systemctl enable genslave
    print_success "Service enabled"

    STATE_SERVICE_INSTALLED=true
    save_state

    echo ""
    print_warning "The GenSlave application code must be deployed to ${INSTALL_DIR}/app/"
    print_warning "before the service can be started."
}

# =============================================================================
# Helper Scripts
# =============================================================================

create_helper_scripts() {
    print_section "Creating Helper Scripts"

    print_step "1" "Creating health check script..."

    cat > "$INSTALL_DIR/health-check.sh" << 'EOF'
#!/bin/bash
# GenSlave Health Check

echo "=== GenSlave Health Check ==="

# Check service status
if systemctl is-active --quiet genslave; then
    echo "✓ Service: running"
else
    echo "✗ Service: not running"
    exit 1
fi

# Check API health
if curl -s http://localhost:8000/api/health | grep -q "healthy"; then
    echo "✓ API: healthy"
else
    echo "✗ API: not responding"
fi

# Check database
if [ -f /opt/genslave/data/genslave.db ]; then
    DB_SIZE=$(du -h /opt/genslave/data/genslave.db | cut -f1)
    echo "✓ Database: $DB_SIZE"
else
    echo "✗ Database: missing"
fi

# Check memory
MEM_USED=$(free -m | awk 'NR==2{printf "%.0f%%", $3*100/$2}')
echo "• Memory: $MEM_USED"

# Check Tailscale
if tailscale status &>/dev/null; then
    echo "✓ Tailscale: connected"
else
    echo "• Tailscale: not connected"
fi

echo "=== Health Check Complete ==="
EOF

    chmod +x "$INSTALL_DIR/health-check.sh"
    print_success "Health check script created"

    print_step "2" "Creating backup script..."

    cat > "$INSTALL_DIR/backup.sh" << 'EOF'
#!/bin/bash
# GenSlave Backup Script

BACKUP_DIR="/opt/genslave/backups"
mkdir -p "$BACKUP_DIR"

# Backup database
cp /opt/genslave/data/genslave.db "$BACKUP_DIR/genslave-$(date +%Y%m%d-%H%M%S).db"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/genslave-*.db | tail -n +8 | xargs -r rm

echo "Backup complete"
EOF

    chmod +x "$INSTALL_DIR/backup.sh"
    print_success "Backup script created"

    # Add backup to crontab
    (crontab -l 2>/dev/null | grep -v "$INSTALL_DIR/backup.sh"; echo "0 2 * * * $INSTALL_DIR/backup.sh") | crontab -
    print_success "Daily backup scheduled"
}

# =============================================================================
# Final Summary
# =============================================================================

print_summary() {
    print_section "Installation Complete!"

    echo "  GenSlave has been successfully installed."
    echo ""
    echo -e "  ${BOLD}Installation Location:${NC}"
    echo "  Application:      $INSTALL_DIR/app/"
    echo "  Configuration:    $CONFIG_FILE"
    echo "  Database:         $INSTALL_DIR/data/genslave.db"
    echo "  Logs:             $INSTALL_DIR/logs/"
    echo ""

    echo -e "  ${BOLD}Service Management:${NC}"
    echo "  Start:            sudo systemctl start genslave"
    echo "  Stop:             sudo systemctl stop genslave"
    echo "  Status:           sudo systemctl status genslave"
    echo "  Logs:             tail -f $INSTALL_DIR/logs/genslave.log"
    echo ""

    if [ "$ENABLE_TAILSCALE" = true ]; then
        local ts_ip=$(tailscale ip -4 2>/dev/null)
        echo -e "  ${BOLD}Tailscale:${NC}"
        echo "  IP Address:       $ts_ip"
        echo "  Hostname:         $TAILSCALE_HOSTNAME"
        echo ""
    fi

    echo -e "  ${BOLD}${YELLOW}Next Steps:${NC}"
    echo "  1. Deploy the GenSlave application code to $INSTALL_DIR/app/"
    echo "  2. Start the service: sudo systemctl start genslave"
    echo "  3. Verify GenMaster can communicate with GenSlave"
    echo ""

    if grep -q "reboot" /var/run/reboot-required 2>/dev/null || [ -f /var/run/reboot-required ]; then
        echo -e "  ${BOLD}${RED}REBOOT REQUIRED:${NC}"
        echo "  Please reboot to enable hardware interfaces:"
        echo "  sudo reboot"
        echo ""
    fi

    log_info "Installation completed successfully"
}

# =============================================================================
# Main Function
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --preconfig)
                PRECONFIG_FILE="$2"
                source "$PRECONFIG_FILE"
                shift 2
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --help|-h)
                echo "GenSlave Setup Script"
                echo ""
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --preconfig FILE    Use preconfig file"
                echo "  --debug             Enable debug mode"
                echo "  --help              Show this help message"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Initialize
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    log_info "GenSlave setup started"

    check_root
    print_header

    # Load previous state if exists
    if load_state; then
        print_info "Found previous installation state"
        if ! confirm "Would you like to resume the previous installation?"; then
            rm -f "$STATE_FILE"
            STATE_SYSTEM_PREPARED=false
            STATE_PYTHON_INSTALLED=false
            STATE_HARDWARE_VALIDATED=false
            STATE_TAILSCALE_CONFIGURED=false
            STATE_ENV_CONFIGURED=false
            STATE_SERVICE_INSTALLED=false
        fi
    fi

    # Run installation steps
    [ "$STATE_SYSTEM_PREPARED" != true ] && prepare_system || print_info "System already prepared"
    [ "$STATE_PYTHON_INSTALLED" != true ] && install_python_environment || print_info "Python already installed"
    [ "$STATE_HARDWARE_VALIDATED" != true ] && validate_hardware || print_info "Hardware already validated"
    [ "$STATE_TAILSCALE_CONFIGURED" != true ] && configure_tailscale || print_info "Tailscale already configured"
    [ "$STATE_ENV_CONFIGURED" != true ] && configure_environment || print_info "Environment already configured"
    [ "$STATE_SERVICE_INSTALLED" != true ] && install_service || print_info "Service already installed"

    create_helper_scripts
    print_summary

    log_info "GenSlave setup completed"
}

main "$@"
