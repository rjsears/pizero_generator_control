# =============================================================================
# Host Tools Sidecar Container
# =============================================================================
# A lightweight persistent container with network tools pre-installed.
# Used for accessing host network info (WiFi, etc.) via docker exec.
# Much faster than spinning up a new container for each command.
# =============================================================================

FROM alpine:3.19

# Install all required tools upfront (no runtime package downloads)
RUN apk add --no-cache \
    wireless-tools \
    iproute2 \
    networkmanager \
    util-linux \
    bash \
    && rm -rf /var/cache/apk/*

# Keep container running - it just waits for exec commands
CMD ["sleep", "infinity"]
