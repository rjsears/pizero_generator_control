#!/bin/bash
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# GenMaster Bootstrap Installer
# Version 1.0.0 - January 16th, 2026
#
# Quick installation script for GenMaster
# Can be run directly via curl:
#   curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genmaster/install.sh | sudo bash
#
# Or download and run:
#   wget -O install.sh https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genmaster/install.sh
#   chmod +x install.sh
#   sudo ./install.sh
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

# Configuration
REPO_URL="https://github.com/rjsears/pizero_generator_control.git"
REPO_BRANCH="main"
INSTALL_DIR="/opt/genmaster"
TEMP_DIR="/tmp/genmaster-install"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# Helper Functions
# =============================================================================

print_banner() {
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
    echo "║                     Bootstrap Installer v1.0.0                     ║"
    echo "║                                                                    ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

command_exists() {
    command -v "$1" &> /dev/null
}

# =============================================================================
# Pre-flight Checks
# =============================================================================

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root"
        echo "Please run: sudo $0"
        exit 1
    fi
}

check_os() {
    if [ ! -f /etc/os-release ]; then
        log_error "Unsupported operating system"
        exit 1
    fi

    . /etc/os-release

    case "$ID" in
        debian|ubuntu|raspbian)
            log_info "Detected: $PRETTY_NAME"
            ;;
        *)
            log_warn "Untested OS: $PRETTY_NAME - proceeding anyway"
            ;;
    esac
}

check_architecture() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            log_info "Architecture: x86_64 (amd64)"
            ;;
        aarch64|arm64)
            log_info "Architecture: ARM64"
            ;;
        armv7l|armhf)
            log_info "Architecture: ARMv7 (32-bit)"
            ;;
        *)
            log_error "Unsupported architecture: $arch"
            exit 1
            ;;
    esac
}

check_internet() {
    log_info "Checking internet connectivity..."
    if ping -c 1 -W 5 8.8.8.8 &> /dev/null || ping -c 1 -W 5 1.1.1.1 &> /dev/null; then
        log_info "Internet connection OK"
        return 0
    fi
    log_error "No internet connection"
    exit 1
}

# =============================================================================
# Installation
# =============================================================================

install_git() {
    if command_exists git; then
        log_info "Git is already installed"
        return 0
    fi

    log_info "Installing git..."
    apt-get update -qq
    apt-get install -y -qq git
    log_info "Git installed successfully"
}

install_dependencies() {
    log_info "Installing bootstrap dependencies..."
    apt-get update -qq
    apt-get install -y -qq curl wget ca-certificates
    log_info "Dependencies installed"
}

clone_repository() {
    log_info "Cloning GenMaster repository..."

    # Clean up any existing temp directory
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"

    # Clone the repository
    if git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$TEMP_DIR" 2>/dev/null; then
        log_info "Repository cloned successfully"
    else
        log_error "Failed to clone repository"
        log_info "Trying alternative download method..."

        # Fallback: download tarball
        local tarball_url="https://github.com/rjsears/pizero_generator_control/archive/refs/heads/${REPO_BRANCH}.tar.gz"
        if curl -fsSL "$tarball_url" | tar xz -C "$TEMP_DIR" --strip-components=1; then
            log_info "Downloaded via tarball"
        else
            log_error "Failed to download repository"
            exit 1
        fi
    fi
}

run_setup() {
    local setup_script="$TEMP_DIR/genmaster/setup.sh"

    if [ ! -f "$setup_script" ]; then
        log_error "Setup script not found: $setup_script"
        exit 1
    fi

    log_info "Making setup script executable..."
    chmod +x "$setup_script"

    log_info "Starting GenMaster setup..."
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════"
    echo ""

    # Run the setup script, passing through any arguments
    "$setup_script" "$@"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

# =============================================================================
# Main
# =============================================================================

main() {
    print_banner

    log_info "GenMaster Bootstrap Installer"
    log_info "=============================="
    echo ""

    # Pre-flight checks
    check_root
    check_os
    check_architecture
    check_internet

    echo ""

    # Install dependencies
    install_dependencies
    install_git

    echo ""

    # Clone and run setup
    clone_repository
    run_setup "$@"

    # Cleanup
    cleanup

    log_info "Bootstrap complete!"
}

# Run main function with all arguments
main "$@"
