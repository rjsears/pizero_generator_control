# GenSlave Docker Rebuild for Raspberry Pi Zero 2W

## Overview

This document contains all instructions needed to rebuild the GenSlave Docker image for **Raspberry Pi Zero 2W** (arm/v7 architecture) and deploy it.

**Current state**: The image is built for Pi Zero W (arm/v6). The Pi Zero 2W uses arm/v7 which allows for faster builds and more pre-built wheels.

## Architecture Differences

| Device | Architecture | Platform Flag |
|--------|-------------|---------------|
| Pi Zero W (original) | ARMv6 | `linux/arm/v6` |
| Pi Zero 2W | ARMv7 | `linux/arm/v7` |

The Pi Zero 2W is significantly more powerful and has better package support.

---

## Step 1: Update the Build Script

Edit `genslave/build.sh` and change the platform from arm/v6 to arm/v7:

**File**: `genslave/build.sh`

**Change line 21 from**:
```bash
PLATFORM="linux/arm/v6"
```

**To**:
```bash
PLATFORM="linux/arm/v7"
```

---

## Step 2: Update the Dockerfile (Optional Optimization)

The current Dockerfile uses `debian:bookworm-slim` base image with system Python to avoid numpy compilation issues on arm/v6. This works fine on arm/v7 too, but arm/v7 has better wheel support.

**Current Dockerfile** (`genslave/Dockerfile`) - No changes required, but here's what it does:
- Uses `debian:bookworm-slim` as base (system Python)
- Installs numpy, PIL, spidev, smbus via apt (pre-compiled)
- Installs FastAPI, uvicorn, pydantic 1.x via pip
- Installs automationhat, RPi.GPIO via pip
- Uses `--break-system-packages` flag for pip

**Optional**: For arm/v7, you could switch back to `python:3.11-slim-bookworm` base image since pydantic 2.x has pre-built wheels for arm/v7. But the current Dockerfile works fine.

---

## Step 3: Run the Build

From your Mac (or any machine with Docker):

```bash
cd "/Users/rsears/Google Drive/PycharmProjects/pizero_generator_control/genslave"
./build.sh
```

The build will:
1. Cross-compile for arm/v7
2. Push to Docker Hub as `rjsears/pizero_generator_control:genslave`

**Expected build time**: ~2-5 minutes (faster than arm/v6)

---

## Step 4: Prepare the Pi Zero 2W

### 4.1 Flash the SD Card

1. Use Raspberry Pi Imager
2. Select: **Raspberry Pi OS Lite (64-bit)** or **Raspberry Pi OS Lite (32-bit)**
   - 32-bit recommended for compatibility with existing setup
3. Configure in Imager settings (gear icon):
   - Hostname: `GenSlave` (or your preferred name)
   - Enable SSH with password authentication
   - Set username: `pi` (or your preferred)
   - Set password
   - Configure WiFi (SSID and password)
   - Set locale/timezone

### 4.2 Boot and Connect

1. Insert SD card into Pi Zero 2W
2. Power on
3. Wait ~2 minutes for first boot
4. SSH in: `ssh pi@genslave.local` (or use IP address)

---

## Step 5: Run the Setup Script

The setup script is self-contained and does everything:

```bash
curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genslave/setup-docker.sh -o setup-docker.sh && chmod +x setup-docker.sh && sudo ./setup-docker.sh
```

**Note**: If the repo is private, SCP the script instead:
```bash
# From your Mac:
scp "/Users/rsears/Google Drive/PycharmProjects/pizero_generator_control/genslave/setup-docker.sh" pi@genslave.local:~/

# Then on the Pi:
chmod +x setup-docker.sh
sudo ./setup-docker.sh
```

### What the Setup Script Does:
1. Updates system packages
2. Installs Docker from Debian repos (`docker.io` package)
3. Installs docker-compose
4. Installs Tailscale (prompts for auth key)
5. Creates `/opt/genslave/` directory structure
6. Writes `docker-compose.yaml`
7. Pulls the Docker image from Docker Hub
8. Creates systemd service for auto-start
9. Starts the container

---

## Step 6: Verify Deployment

After setup completes:

```bash
# Check container is running
docker-compose -f /opt/genslave/docker-compose.yaml ps

# Check logs
docker-compose -f /opt/genslave/docker-compose.yaml logs -f

# Test the API
curl http://localhost:8001/health
```

---

## Step 7: Hardware Setup

Connect the Automation Hat Mini to the Pi Zero 2W GPIO header. The display and relays should work automatically.

Test relay control:
```bash
curl http://localhost:8001/relay/1/on
curl http://localhost:8001/relay/1/off
```

---

## Troubleshooting

### "exec format error"
The image was built for wrong architecture. Rebuild with correct platform flag.

### Container won't start
Check logs: `docker-compose logs`

### Display not working
Ensure SPI is enabled:
```bash
sudo raspi-config
# Interface Options -> SPI -> Enable
sudo reboot
```

### GPIO permission denied
The container runs as root by default. If you see permission errors, ensure the docker-compose.yaml has:
```yaml
privileged: true
```

### Tailscale not connecting
```bash
sudo tailscale status
sudo tailscale up --authkey=YOUR_KEY
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `genslave/Dockerfile` | Docker image definition |
| `genslave/build.sh` | Build script (run on Mac) |
| `genslave/setup-docker.sh` | Pi setup script (run on Pi) |
| `genslave/docker-compose.yaml` | Container configuration |
| `genslave/requirements.txt` | Python dependencies |
| `genslave/app/` | Application source code |

---

## Quick Reference Commands

**Rebuild image (on Mac)**:
```bash
cd "/Users/rsears/Google Drive/PycharmProjects/pizero_generator_control/genslave"
./build.sh
```

**Update Pi to latest image**:
```bash
docker pull rjsears/pizero_generator_control:genslave
docker-compose -f /opt/genslave/docker-compose.yaml up -d
```

**View logs**:
```bash
docker-compose -f /opt/genslave/docker-compose.yaml logs -f
```

**Restart container**:
```bash
docker-compose -f /opt/genslave/docker-compose.yaml restart
```

**Stop container**:
```bash
docker-compose -f /opt/genslave/docker-compose.yaml down
```

---

## Summary of Changes for Pi Zero 2W

1. **build.sh line 21**: Change `PLATFORM="linux/arm/v6"` to `PLATFORM="linux/arm/v7"`
2. Run `./build.sh` to rebuild and push
3. On Pi Zero 2W: Run setup script or `docker pull` to get new image

That's it. The Dockerfile and setup script work unchanged.
