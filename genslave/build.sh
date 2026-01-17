#!/bin/bash
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# GenSlave Docker Build Script
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Cross-compiles GenSlave for Pi Zero (arm/v6) and pushes to Docker Hub
# Run this on your Mac or any x86/arm64 machine with Docker
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

set -e

# Configuration
IMAGE_NAME="rjsears/pizero_generator_control"
IMAGE_TAG="genslave"
PLATFORM="linux/arm/v7"
BUILDER_NAME="genslave-builder"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           GenSlave Docker Build Script                    ║"
echo "║         Cross-compile for Raspberry Pi Zero               ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if logged into Docker Hub
# Note: Docker Desktop uses credential helpers, so we check the config file
echo -e "${YELLOW}Checking Docker Hub login...${NC}"
DOCKER_CONFIG="$HOME/.docker/config.json"
if [[ -f "$DOCKER_CONFIG" ]]; then
    # Check for auths entry or credsStore (credential helper like macOS Keychain)
    if grep -q '"https://index.docker.io/v1/"' "$DOCKER_CONFIG" || grep -q '"credsStore"' "$DOCKER_CONFIG"; then
        echo -e "${GREEN}Docker Hub credentials found${NC}"
    else
        echo -e "${RED}Not logged into Docker Hub. Please run: docker login${NC}"
        exit 1
    fi
else
    echo -e "${RED}Docker config not found. Please run: docker login${NC}"
    exit 1
fi

# Check if buildx is available
echo -e "${YELLOW}Checking Docker buildx...${NC}"
if ! docker buildx version &>/dev/null; then
    echo -e "${RED}Docker buildx not available. Please update Docker.${NC}"
    exit 1
fi
echo -e "${GREEN}Docker buildx available${NC}"

# Create or use existing builder with multi-arch support
echo -e "${YELLOW}Setting up buildx builder...${NC}"
if ! docker buildx inspect "$BUILDER_NAME" &>/dev/null; then
    echo "Creating new builder: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --bootstrap
fi
docker buildx use "$BUILDER_NAME"
echo -e "${GREEN}Builder ready: $BUILDER_NAME${NC}"

# Build and push
echo ""
echo -e "${YELLOW}Building for platform: ${PLATFORM}${NC}"
echo -e "${YELLOW}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo ""

# Parse command line arguments
PUSH_FLAG="--push"
LOAD_FLAG=""
if [[ "$1" == "--local" ]]; then
    echo -e "${YELLOW}Local build only (not pushing to Docker Hub)${NC}"
    PUSH_FLAG=""
    LOAD_FLAG="--load"
fi

# Build the image
docker buildx build \
    --platform "$PLATFORM" \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --tag "${IMAGE_NAME}:genslave-latest" \
    $PUSH_FLAG \
    $LOAD_FLAG \
    --progress=plain \
    .

BUILD_STATUS=$?

if [ $BUILD_STATUS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                    Build Successful!                      ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Image: ${BLUE}${IMAGE_NAME}:${IMAGE_TAG}${NC}"
    echo ""
    echo -e "${YELLOW}To deploy on Pi Zero:${NC}"
    echo "  1. SSH to Pi Zero"
    echo "  2. docker pull ${IMAGE_NAME}:${IMAGE_TAG}"
    echo "  3. docker compose up -d"
    echo ""
else
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                     Build Failed!                         ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
