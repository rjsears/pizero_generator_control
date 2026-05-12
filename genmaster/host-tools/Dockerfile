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
    networkmanager-cli \
    util-linux \
    util-linux-misc \
    bash \
    docker-cli \
    docker-cli-compose \
    && rm -rf /var/cache/apk/*

# Verify every critical binary GenMaster's backend depends on is present.
# Without these, runtime endpoints fail silently with "sh: <tool>: not found"
# and the operator has to chase the symptom across containers and Dockerfiles.
# Fail the BUILD instead if a future package change ever drops one of these.
# The loop reports each binary individually so the CI log shows exactly
# which one is missing instead of short-circuiting on the first failure.
RUN set -e \
    && echo "=== Verifying critical binaries ===" \
    && missing="" \
    && for cmd in nmcli ip iwgetid nsenter bash docker; do \
        if path=$(which "$cmd" 2>/dev/null); then \
            echo "OK: $cmd -> $path"; \
        else \
            echo "MISSING: $cmd"; \
            missing="$missing $cmd"; \
        fi; \
    done \
    && if docker compose version > /dev/null 2>&1; then \
        echo "OK: docker compose"; \
    else \
        echo "MISSING: docker compose"; \
        missing="$missing docker-compose"; \
    fi \
    && if [ -n "$missing" ]; then \
        echo "BUILD FAILED: missing binaries:$missing"; \
        exit 1; \
    fi \
    && echo "OK: all critical binaries present in host-tools image"

# Keep container running - it just waits for exec commands
CMD ["sleep", "infinity"]
