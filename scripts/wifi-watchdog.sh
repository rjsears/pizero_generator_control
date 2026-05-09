#!/bin/bash
# =============================================================================
# WiFi Watchdog - Monitors connectivity and recovers from WiFi failures
# =============================================================================
# Part of the RPi Generator Control suite
# https://github.com/rjsears/pizero_generator_control
#
# This script monitors connectivity to the default gateway and attempts
# escalating recovery actions if connectivity is lost. Designed to run on
# both GenMaster (Pi5) and GenSlave (PiZero 2W).
#
# Recovery sequence:
#   1-3 failures:  Soft WiFi reset (nmcli or wpa_cli)
#   4-5 failures:  Hard WiFi reset (ip link down/up)
#   6+ failures:   Reboot (max once per hour)
#
# Safety features:
#   - Only checks gateway (local network), not internet
#   - If gateway is reachable but internet is down, no action taken
#   - Reboot cooldown prevents reboot loops
#   - State persists across script restarts
#
# Installation:
#   sudo cp wifi-watchdog.sh /usr/local/bin/
#   sudo chmod +x /usr/local/bin/wifi-watchdog.sh
#   sudo cp wifi-watchdog.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now wifi-watchdog
#
# =============================================================================

set -uo pipefail

# =============================================================================
# Configuration
# =============================================================================
CHECK_INTERVAL="${WATCHDOG_CHECK_INTERVAL:-30}"          # Seconds between checks
PING_TIMEOUT="${WATCHDOG_PING_TIMEOUT:-5}"               # Ping timeout in seconds
PING_COUNT="${WATCHDOG_PING_COUNT:-2}"                   # Number of pings per check
MAX_SOFT_RESETS="${WATCHDOG_MAX_SOFT_RESETS:-3}"         # Soft resets before escalating
MAX_HARD_RESETS="${WATCHDOG_MAX_HARD_RESETS:-2}"         # Hard resets before reboot
REBOOT_COOLDOWN="${WATCHDOG_REBOOT_COOLDOWN:-3600}"      # Min seconds between reboots
STATE_FILE="/var/run/wifi-watchdog.state"
LOG_TAG="wifi-watchdog"

# State tracking (loaded from file if exists)
CONSECUTIVE_FAILURES=0
LAST_REBOOT_TIME=0

# =============================================================================
# Logging
# =============================================================================
log_info() {
    logger -t "$LOG_TAG" -p daemon.info "$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_warn() {
    logger -t "$LOG_TAG" -p daemon.warning "$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1"
}

log_error() {
    logger -t "$LOG_TAG" -p daemon.err "$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
}

# =============================================================================
# State Management
# =============================================================================
load_state() {
    if [[ -f "$STATE_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$STATE_FILE" 2>/dev/null || true
    fi
}

save_state() {
    cat > "$STATE_FILE" << EOF
CONSECUTIVE_FAILURES=$CONSECUTIVE_FAILURES
LAST_REBOOT_TIME=$LAST_REBOOT_TIME
EOF
    chmod 600 "$STATE_FILE"
}

# =============================================================================
# Network Detection
# =============================================================================
get_default_gateway() {
    # Get the default gateway from routing table
    ip route 2>/dev/null | grep -E '^default' | awk '{print $3}' | head -1
}

get_wifi_interface() {
    # Find the wireless interface
    local iface=""

    # Try iw first (most reliable)
    if command -v iw &>/dev/null; then
        iface=$(iw dev 2>/dev/null | grep Interface | awk '{print $2}' | head -1)
    fi

    # Fallback: check /sys/class/net for wireless interfaces
    if [[ -z "$iface" ]]; then
        for i in /sys/class/net/*/wireless; do
            if [[ -d "$i" ]]; then
                iface=$(basename "$(dirname "$i")")
                break
            fi
        done
    fi

    # Last resort: common interface names
    if [[ -z "$iface" ]]; then
        for i in wlan0 wlan1 wlp2s0 wlp3s0; do
            if [[ -d "/sys/class/net/$i" ]]; then
                iface="$i"
                break
            fi
        done
    fi

    echo "$iface"
}

check_wifi_connected() {
    local iface
    iface=$(get_wifi_interface)

    if [[ -z "$iface" ]]; then
        return 1
    fi

    # Check if interface is up and has an IP
    if ip addr show "$iface" 2>/dev/null | grep -q 'inet '; then
        return 0
    fi
    return 1
}

check_gateway_reachable() {
    local gateway
    gateway=$(get_default_gateway)

    if [[ -z "$gateway" ]]; then
        log_warn "No default gateway found"
        return 1
    fi

    if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$gateway" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# =============================================================================
# Recovery Actions
# =============================================================================
reset_wifi_soft() {
    log_info "Attempting soft WiFi reset"
    local iface
    iface=$(get_wifi_interface)

    # Try NetworkManager first (common on Pi5/desktop)
    if command -v nmcli &>/dev/null; then
        log_info "Using nmcli for soft reset"
        nmcli radio wifi off 2>/dev/null || true
        sleep 3
        nmcli radio wifi on 2>/dev/null || true
        sleep 10
        return 0
    fi

    # Try wpa_cli (common on PiZero/minimal systems)
    if command -v wpa_cli &>/dev/null; then
        log_info "Using wpa_cli for soft reset"
        wpa_cli -i "$iface" reassociate 2>/dev/null || true
        sleep 10
        return 0
    fi

    log_warn "No soft reset method available (nmcli/wpa_cli not found)"
    return 1
}

reset_wifi_hard() {
    local iface
    iface=$(get_wifi_interface)

    if [[ -z "$iface" ]]; then
        log_error "No WiFi interface found for hard reset"
        return 1
    fi

    log_info "Attempting hard WiFi reset (ip link down/up on $iface)"

    ip link set "$iface" down 2>/dev/null || true
    sleep 3
    ip link set "$iface" up 2>/dev/null || true
    sleep 10

    # Trigger reconnection based on available tools
    if command -v nmcli &>/dev/null; then
        sleep 5
        nmcli device connect "$iface" 2>/dev/null || true
    elif command -v wpa_cli &>/dev/null; then
        sleep 5
        wpa_cli -i "$iface" reconnect 2>/dev/null || true
    fi

    sleep 10
    return 0
}

restart_network_service() {
    log_info "Restarting network service"

    # Try various network services
    if systemctl is-active --quiet NetworkManager 2>/dev/null; then
        systemctl restart NetworkManager
        sleep 20
        return 0
    fi

    if systemctl is-active --quiet dhcpcd 2>/dev/null; then
        systemctl restart dhcpcd
        sleep 15
        return 0
    fi

    if systemctl is-active --quiet networking 2>/dev/null; then
        systemctl restart networking
        sleep 15
        return 0
    fi

    if systemctl is-active --quiet wpa_supplicant 2>/dev/null; then
        systemctl restart wpa_supplicant
        sleep 15
        return 0
    fi

    log_warn "No known network service found to restart"
    return 1
}

do_reboot() {
    local current_time
    current_time=$(date +%s)

    # Check reboot cooldown
    local time_since_last=$((current_time - LAST_REBOOT_TIME))
    if [[ $time_since_last -lt $REBOOT_COOLDOWN ]]; then
        local remaining=$((REBOOT_COOLDOWN - time_since_last))
        log_warn "Reboot cooldown active. $remaining seconds remaining. Skipping reboot."
        return 1
    fi

    log_error "All recovery attempts failed. Rebooting system in 10 seconds..."
    LAST_REBOOT_TIME=$current_time
    save_state

    # Give time for log messages to flush
    sleep 10

    # Sync filesystems before reboot
    sync

    # Reboot
    /sbin/reboot
}

# =============================================================================
# Main Recovery Logic
# =============================================================================
attempt_recovery() {
    local total_soft_hard=$((MAX_SOFT_RESETS + MAX_HARD_RESETS))

    if [[ $CONSECUTIVE_FAILURES -le $MAX_SOFT_RESETS ]]; then
        # Soft reset phase
        log_info "Recovery phase 1: soft reset (attempt $CONSECUTIVE_FAILURES of $MAX_SOFT_RESETS)"
        reset_wifi_soft

    elif [[ $CONSECUTIVE_FAILURES -le $total_soft_hard ]]; then
        # Hard reset phase
        local hard_attempt=$((CONSECUTIVE_FAILURES - MAX_SOFT_RESETS))
        log_info "Recovery phase 2: hard reset (attempt $hard_attempt of $MAX_HARD_RESETS)"
        reset_wifi_hard

        # Also try restarting network service on last hard reset
        if [[ $hard_attempt -ge $MAX_HARD_RESETS ]]; then
            restart_network_service
        fi

    else
        # Reboot phase
        log_error "Recovery phase 3: all resets exhausted after $CONSECUTIVE_FAILURES failures"
        do_reboot
    fi
}

# =============================================================================
# Main Loop
# =============================================================================
main() {
    local iface
    iface=$(get_wifi_interface)

    log_info "=========================================="
    log_info "WiFi Watchdog starting"
    log_info "=========================================="
    log_info "WiFi interface: ${iface:-not found}"
    log_info "Check interval: ${CHECK_INTERVAL}s"
    log_info "Soft resets before escalating: $MAX_SOFT_RESETS"
    log_info "Hard resets before reboot: $MAX_HARD_RESETS"
    log_info "Reboot cooldown: ${REBOOT_COOLDOWN}s"
    log_info "=========================================="

    if [[ -z "$iface" ]]; then
        log_error "No WiFi interface detected. Is this a WiFi-enabled device?"
        log_error "Exiting."
        exit 1
    fi

    load_state

    if [[ $CONSECUTIVE_FAILURES -gt 0 ]]; then
        log_info "Resuming with $CONSECUTIVE_FAILURES previous failures"
    fi

    while true; do
        # First check if WiFi is even connected
        if ! check_wifi_connected; then
            log_warn "WiFi interface has no IP address"
            ((CONSECUTIVE_FAILURES++)) || true
            save_state
            attempt_recovery
            sleep "$CHECK_INTERVAL"
            continue
        fi

        # Check gateway reachability
        if check_gateway_reachable; then
            # Success - reset counter
            if [[ $CONSECUTIVE_FAILURES -gt 0 ]]; then
                log_info "Connectivity restored after $CONSECUTIVE_FAILURES failure(s)"
                CONSECUTIVE_FAILURES=0
                save_state
            fi
        else
            # Failure
            ((CONSECUTIVE_FAILURES++)) || true
            log_warn "Gateway unreachable (consecutive failures: $CONSECUTIVE_FAILURES)"
            save_state
            attempt_recovery
        fi

        sleep "$CHECK_INTERVAL"
    done
}

# =============================================================================
# Entry Point
# =============================================================================
# Must run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

# Handle signals for clean shutdown
trap 'log_info "WiFi Watchdog stopping"; exit 0' SIGTERM SIGINT

# Run main loop
main "$@"
