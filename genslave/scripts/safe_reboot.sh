#!/bin/bash
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/scripts/safe_reboot.sh
#
# Safe reboot script for GenSlave Pi Zero
# Only reboots if the generator is NOT running
#
# Usage: Add to crontab for periodic maintenance reboots
#   Example: 0 4 * * * /opt/genslave/scripts/safe_reboot.sh >> /var/log/genslave_reboot.log 2>&1
#
# Part of the "RPi Generator Control" suite
# Richard J. Sears - richardjsears@protonmail.com
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

# Configuration
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

# Check if generator is running by querying GenSlave API
check_generator_status() {
    local retry=0

    while [ $retry -lt $MAX_RETRIES ]; do
        # Query the health endpoint which includes relay_state
        response=$(curl -s --max-time 10 "$GENSLAVE_API" 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$response" ]; then
            # Extract relay_state from JSON response
            # relay_state: true means generator is running
            relay_state=$(echo "$response" | grep -o '"relay_state":[^,}]*' | cut -d':' -f2 | tr -d ' ')

            if [ "$relay_state" = "true" ]; then
                log "Generator is RUNNING (relay_state=true) - reboot NOT safe"
                return 1
            elif [ "$relay_state" = "false" ]; then
                log "Generator is STOPPED (relay_state=false) - reboot is safe"
                return 0
            else
                log_error "Could not parse relay_state from response: $response"
            fi
        else
            log_error "Failed to query GenSlave API (attempt $((retry + 1))/$MAX_RETRIES)"
        fi

        retry=$((retry + 1))
        if [ $retry -lt $MAX_RETRIES ]; then
            sleep $RETRY_DELAY
        fi
    done

    log_error "Failed to get generator status after $MAX_RETRIES attempts - aborting reboot for safety"
    return 1
}

# Gracefully stop the genslave container
stop_genslave() {
    log "Stopping genslave container gracefully..."

    if ! cd "$COMPOSE_DIR"; then
        log_error "Failed to cd to $COMPOSE_DIR"
        return 1
    fi

    # Stop with a reasonable timeout for graceful shutdown
    if docker compose stop -t 30 genslave; then
        log "GenSlave container stopped successfully"
        return 0
    else
        log_error "Failed to stop genslave container"
        return 1
    fi
}

# Main execution
main() {
    log "=========================================="
    log "Safe reboot check initiated"
    log "=========================================="

    # Check if we can safely reboot
    if ! check_generator_status; then
        log "Reboot aborted - generator is running or status unknown"
        exit 1
    fi

    # Generator is not running - safe to reboot
    log "Proceeding with safe reboot sequence..."

    # Stop the container gracefully
    if ! stop_genslave; then
        log_error "Failed to stop container - aborting reboot"
        exit 1
    fi

    # Brief pause to ensure clean shutdown
    sleep 2

    log "Initiating system reboot..."

    # Sync filesystems before reboot
    sync

    # Reboot the system
    /sbin/reboot
}

# Run main function
main "$@"
