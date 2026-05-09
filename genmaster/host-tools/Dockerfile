# =============================================================================
# Host Tools Sidecar Container
# =============================================================================
# A lightweight persistent container with network tools pre-installed.
# Used for accessing host network info (WiFi, etc.) via docker exec.
# Much faster than spinning up a new container for each command.
# =============================================================================

FROM alpine:3.19

# Install all required tools upfront (no runtime package downloads).
# docker-cli + docker-cli-compose let this sidecar recreate other containers,
# notably genmaster itself — which can't recreate its own container from
# inside (the API process gets killed mid-handler when stop is called).
RUN apk add --no-cache \
    wireless-tools \
    iproute2 \
    networkmanager \
    util-linux \
    bash \
    docker-cli \
    docker-cli-compose \
    && rm -rf /var/cache/apk/*

# Keep container running - it just waits for exec commands
CMD ["sleep", "infinity"]
