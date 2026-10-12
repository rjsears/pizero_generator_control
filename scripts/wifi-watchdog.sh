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
#   1 failure:     Log only (grace period, no action)
#   2-4 failures:  Soft WiFi reset (nmcli or wpa_cli)
#   5-6 failures:  Hard WiFi reset (ip link down/up)
#   7+ failures:   Long-outage mode. The connectivity check still runs every
#                  cycle, but recovery actions run only once every
#                  WATCHDOG_RECOVERY_INTERVAL seconds (default 300): a reboot
#                  is tried first (only after a 10 min minimum outage, at most
#                  once per hour, relay guard permitting); if it is not
#                  allowed, a recovery sequence runs instead (soft reset, then
#                  hard reset, then network service restart, stopping as soon
#                  as the gateway answers)
# (Shown with the defaults; the grace period and the number of soft and
# hard resets are configurable via the WATCHDOG_* environment variables.)
#
# Safety features:
#   - Only checks gateway (local network), not internet
#   - If gateway is reachable but internet is down, no action taken
#   - Reboot cooldown prevents reboot loops (checked against both the saved
#     wall-clock time and system uptime, since a Pi without an RTC may not
#     have a correct clock while the network is down)
#   - Minimum outage: no reboot until connectivity has been failing
#     continuously for WATCHDOG_MIN_OUTAGE_BEFORE_REBOOT seconds (default
#     600), measured with /proc/uptime (monotonic, no RTC needed)
#   - SSID visibility logging: before a reboot, a fresh WiFi scan records
#     whether a configured network is visible (access point down vs. Pi
#     stuck). The result is logged for diagnosis, not used as a gate
#   - Recovery actions are throttled in long-outage mode to one sequence
#     per WATCHDOG_RECOVERY_INTERVAL seconds, so the interface is not
#     bounced every check interval during a long access point outage
#   - Optional reboot guard: if WATCHDOG_REBOOT_GUARD_URL is set, the reboot
#     is refused unless that URL reports "relay_state": false (GenSlave
#     must never reboot while the generator relay is energized)
#   - State persists across script restarts and reboots (stored on disk)
#   - Failure counter resets on startup so a fresh boot restarts the
#     escalation from soft resets
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
PING_COUNT="${WATCHDOG_PING_COUNT:-3}"                   # Number of pings per check
GRACE_FAILURES="${WATCHDOG_GRACE_FAILURES:-1}"           # Failed checks tolerated before any recovery action
MAX_SOFT_RESETS="${WATCHDOG_MAX_SOFT_RESETS:-3}"         # Soft resets before escalating
MAX_HARD_RESETS="${WATCHDOG_MAX_HARD_RESETS:-2}"         # Hard resets before reboot
REBOOT_COOLDOWN="${WATCHDOG_REBOOT_COOLDOWN:-3600}"      # Min seconds between reboots
STATE_FILE="${WATCHDOG_STATE_FILE:-/var/lib/wifi-watchdog/state}"      # Persistent (not tmpfs)
REBOOT_GUARD_URL="${WATCHDOG_REBOOT_GUARD_URL:-}"        # Optional: refuse reboot unless relay_state is false
MIN_OUTAGE_BEFORE_REBOOT="${WATCHDOG_MIN_OUTAGE_BEFORE_REBOOT:-600}"   # Seconds of continuous failure before a reboot is considered
RECOVERY_INTERVAL="${WATCHDOG_RECOVERY_INTERVAL:-300}"   # Seconds between recovery actions in long-outage mode
LOG_TAG="wifi-watchdog"

# State tracking (loaded from file if exists)
CONSECUTIVE_FAILURES=0
LAST_REBOOT_TIME=0
OUTAGE_START=0             # Uptime (s) when the current outage began, 0 = none (not persisted)
LAST_RECOVERY_ACTION=0     # Uptime (s) of the last recovery action, 0 = none (not persisted)
QUIET_CYCLES=0             # Long-outage cycles without an action, for log throttling (not persisted)

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
    mkdir -p "$(dirname "$STATE_FILE")"
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
        sleep 20
        return 0
    fi

    # Try wpa_cli (common on PiZero/minimal systems)
    if command -v wpa_cli &>/dev/null; then
        log_info "Using wpa_cli for soft reset"
        wpa_cli -i "$iface" reassociate 2>/dev/null || true
        sleep 20
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

get_uptime_seconds() {
    # Integer seconds since boot (independent of wall-clock time)
    local uptime
    uptime=$(cut -d' ' -f1 /proc/uptime 2>/dev/null | cut -d'.' -f1)
    if [[ ! "$uptime" =~ ^[0-9]+$ ]]; then
        uptime=0
    fi
    echo "$uptime"
}

check_reboot_guard() {
    # Returns 0 only if no guard is configured or the guard URL reports
    # relay_state false. Any other result (relay energized, request failed,
    # unparseable response) is treated as unsafe.
    if [[ -z "$REBOOT_GUARD_URL" ]]; then
        return 0
    fi

    local response
    local relay_state
    if ! response=$(curl -s --max-time 10 "$REBOOT_GUARD_URL" 2>/dev/null) || [[ -z "$response" ]]; then
        log_error "Reboot guard check failed (no response from $REBOOT_GUARD_URL), refusing to reboot"
        return 1
    fi

    relay_state=$(echo "$response" | grep -o '"relay_state":[^,}]*' | cut -d':' -f2 | tr -d ' ')
    if [[ "$relay_state" == "true" ]]; then
        log_error "Reboot guard: generator relay is energized, refusing to reboot"
        return 1
    elif [[ "$relay_state" == "false" ]]; then
        log_info "Reboot guard: generator relay is off, reboot allowed"
        return 0
    fi

    log_error "Reboot guard: could not determine relay_state from $REBOOT_GUARD_URL, refusing to reboot"
    return 1
}

log_ap_visibility() {
    # Informational only: always returns 0 and never blocks a reboot.
    # Runs a fresh scan and logs whether a configured SSID is visible, so
    # the journal shows whether the access point was down (no configured
    # network visible) or the Pi was stuck (network visible, or the scan
    # itself failed, which suggests a wedged WiFi chip).
    if ! command -v nmcli &>/dev/null; then
        log_info "Scan skipped (nmcli not available)"
        return 0
    fi

    # Collect the SSIDs of all configured WiFi connections.
    # nmcli -g escapes ':' inside values as '\:', and a connection name may
    # contain ':', so split on the last ':' (TYPE never contains one).
    local -a configured=()
    local line name type ssid
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        type="${line##*:}"
        name="${line%:*}"
        name="${name//\\:/:}"
        if [[ "$type" == "802-11-wireless" ]]; then
            ssid=$(nmcli -g 802-11-wireless.ssid connection show "$name" 2>/dev/null)
            ssid="${ssid//\\:/:}"
            if [[ -n "$ssid" ]]; then
                configured+=("$ssid")
            fi
        fi
    done < <(nmcli -g NAME,TYPE connection show 2>/dev/null)

    if [[ ${#configured[@]} -eq 0 ]]; then
        log_warn "Scan: no configured WiFi networks to compare against"
        return 0
    fi

    # Fresh scan of visible networks
    local iface
    iface=$(get_wifi_interface)
    local scan_output
    local scan_status
    scan_output=$(timeout 45 nmcli -g SSID device wifi list ifname "$iface" --rescan yes 2>/dev/null)
    scan_status=$?
    if [[ $scan_status -ne 0 ]]; then
        log_error "WiFi scan failed (status $scan_status); WiFi chip may be wedged"
        return 0
    fi

    local seen=0
    local scanned want
    while IFS= read -r scanned; do
        [[ -z "$scanned" ]] && continue
        ((seen++)) || true
        scanned="${scanned//\\:/:}"
        for want in "${configured[@]}"; do
            if [[ "$scanned" == "$want" ]]; then
                log_info "Scan: configured network '$want' is visible; Pi is failing to connect to a working access point"
                return 0
            fi
        done
    done <<< "$scan_output"

    log_warn "Scan: configured network not visible ($seen networks seen); access point appears down; rebooting anyway per policy"
    return 0
}

do_reboot() {
    local current_time
    current_time=$(date +%s)

    # Check reboot cooldown (wall-clock, persisted across reboots)
    local time_since_last=$((current_time - LAST_REBOOT_TIME))
    if [[ $time_since_last -lt $REBOOT_COOLDOWN ]]; then
        local remaining=$((REBOOT_COOLDOWN - time_since_last))
        log_warn "Reboot cooldown active. $remaining seconds remaining. Skipping reboot."
        return 1
    fi

    # Check reboot cooldown (uptime, independent of wall-clock time)
    local uptime
    uptime=$(get_uptime_seconds)
    if [[ $uptime -lt $REBOOT_COOLDOWN ]]; then
        local remaining_uptime=$((REBOOT_COOLDOWN - uptime))
        log_warn "System uptime ${uptime}s is below reboot cooldown. $remaining_uptime seconds remaining. Skipping reboot."
        return 1
    fi

    # Require a minimum continuous outage (uptime-based, monotonic)
    local outage=$(( $(get_uptime_seconds) - OUTAGE_START ))
    if [[ $OUTAGE_START -eq 0 ]] || [[ $outage -lt $MIN_OUTAGE_BEFORE_REBOOT ]]; then
        local remaining_outage=$MIN_OUTAGE_BEFORE_REBOOT
        if [[ $OUTAGE_START -ne 0 ]]; then
            remaining_outage=$((MIN_OUTAGE_BEFORE_REBOOT - outage))
        fi
        log_warn "Outage below minimum before reboot (${MIN_OUTAGE_BEFORE_REBOOT}s). $remaining_outage seconds remaining. Skipping reboot."
        return 1
    fi

    # Record whether the access point is visible (diagnostic only, not a gate)
    log_ap_visibility || true

    # Never reboot while the generator relay is (or may be) energized
    if ! check_reboot_guard; then
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

run_recovery_sequence() {
    # One full long-outage recovery action: soft reset, then hard reset,
    # then network service restart, stopping as soon as the gateway answers.
    # The next cycle's check reports the final outcome.
    LAST_RECOVERY_ACTION=$(get_uptime_seconds)

    reset_wifi_soft
    if check_gateway_reachable; then
        log_info "Recovery sequence: gateway reachable, recovered after soft reset"
        return 0
    fi

    reset_wifi_hard
    if check_gateway_reachable; then
        log_info "Recovery sequence: gateway reachable, recovered after hard reset"
        return 0
    fi

    restart_network_service
    return 0
}

# =============================================================================
# Main Recovery Logic
# =============================================================================
attempt_recovery() {
    local total_soft_hard=$((MAX_SOFT_RESETS + MAX_HARD_RESETS))
    # Failures counted past the grace period drive the escalation ladder
    local effective=$((CONSECUTIVE_FAILURES - GRACE_FAILURES))

    if [[ $effective -le 0 ]]; then
        log_warn "Within grace period ($CONSECUTIVE_FAILURES of $GRACE_FAILURES failed checks); no action yet"
        return 0
    fi

    if [[ $effective -le $MAX_SOFT_RESETS ]]; then
        # Soft reset phase
        log_info "Recovery phase 1: soft reset (attempt $effective of $MAX_SOFT_RESETS)"
        LAST_RECOVERY_ACTION=$(get_uptime_seconds)
        reset_wifi_soft

    elif [[ $effective -le $total_soft_hard ]]; then
        # Hard reset phase
        local hard_attempt=$((effective - MAX_SOFT_RESETS))
        log_info "Recovery phase 2: hard reset (attempt $hard_attempt of $MAX_HARD_RESETS)"
        LAST_RECOVERY_ACTION=$(get_uptime_seconds)
        reset_wifi_hard

        # Also try restarting network service on last hard reset
        if [[ $hard_attempt -ge $MAX_HARD_RESETS ]]; then
            restart_network_service
        fi

    else
        # Long-outage mode: the check keeps running every cycle, but recovery
        # actions (reboot attempt or recovery sequence) are throttled to one
        # per RECOVERY_INTERVAL
        local now
        now=$(get_uptime_seconds)
        local since=$((now - LAST_RECOVERY_ACTION))
        local outage=0
        if [[ $OUTAGE_START -ne 0 ]]; then
            outage=$((now - OUTAGE_START))
        fi

        if [[ $since -lt $RECOVERY_INTERVAL ]]; then
            # Quiet cycle: log the first and then every 10th
            ((QUIET_CYCLES++)) || true
            if [[ $((QUIET_CYCLES % 10)) -eq 1 ]]; then
                log_info "Long-outage mode: outage ${outage}s, next recovery action in $((RECOVERY_INTERVAL - since))s"
            fi
            return 0
        fi

        log_error "Recovery phase 3 (long-outage mode): outage ${outage}s after $CONSECUTIVE_FAILURES failures; recovery action due"
        if ! do_reboot; then
            log_warn "Reboot not performed; running recovery sequence"
            run_recovery_sequence
        fi
    fi
}

# =============================================================================
# Main Loop
# =============================================================================
should_log_failure() {
    # Log every failed check during the ladder, then the first and every
    # 10th check in long-outage mode (limits journal growth)
    local past=$((CONSECUTIVE_FAILURES - GRACE_FAILURES - MAX_SOFT_RESETS - MAX_HARD_RESETS))
    [[ $past -le 0 ]] || [[ $((past % 10)) -eq 1 ]]
}

main() {
    local iface
    iface=$(get_wifi_interface)

    log_info "=========================================="
    log_info "WiFi Watchdog starting"
    log_info "=========================================="
    log_info "WiFi interface: ${iface:-not found}"
    log_info "Check interval: ${CHECK_INTERVAL}s"
    log_info "Pings per check: $PING_COUNT"
    log_info "Grace period: $GRACE_FAILURES failed check(s)"
    log_info "Soft resets before escalating: $MAX_SOFT_RESETS"
    log_info "Hard resets before reboot: $MAX_HARD_RESETS"
    log_info "Reboot cooldown: ${REBOOT_COOLDOWN}s"
    log_info "State file: $STATE_FILE"
    log_info "Reboot guard URL: ${REBOOT_GUARD_URL:-not configured}"
    log_info "Minimum outage before reboot: ${MIN_OUTAGE_BEFORE_REBOOT}s"
    log_info "Recovery interval (long-outage mode): ${RECOVERY_INTERVAL}s"
    log_info "SSID visibility: logged at each reboot decision (not a gate)"
    log_info "=========================================="

    if [[ -z "$iface" ]]; then
        log_error "No WiFi interface detected. Is this a WiFi-enabled device?"
        log_error "Exiting."
        exit 1
    fi

    load_state

    # Restart the escalation ladder on every start (keep LAST_REBOOT_TIME)
    if [[ $CONSECUTIVE_FAILURES -gt 0 ]]; then
        log_info "Previous run recorded $CONSECUTIVE_FAILURES failure(s); resetting counter to 0"
    fi
    CONSECUTIVE_FAILURES=0
    save_state

    while true; do
        # First check if WiFi is even connected
        if ! check_wifi_connected; then
            ((CONSECUTIVE_FAILURES++)) || true
            if should_log_failure; then
                log_warn "WiFi interface has no IP address (consecutive failures: $CONSECUTIVE_FAILURES)"
            fi
            if [[ $OUTAGE_START -eq 0 ]]; then
                OUTAGE_START=$(get_uptime_seconds)
            fi
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
            fi
            OUTAGE_START=0
            LAST_RECOVERY_ACTION=0
            QUIET_CYCLES=0
        else
            # Failure
            ((CONSECUTIVE_FAILURES++)) || true
            if [[ $OUTAGE_START -eq 0 ]]; then
                OUTAGE_START=$(get_uptime_seconds)
            fi
            if should_log_failure; then
                log_warn "Gateway unreachable (consecutive failures: $CONSECUTIVE_FAILURES)"
            fi
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
