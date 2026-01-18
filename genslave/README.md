# GenSlave - Generator Relay Control for Raspberry Pi

## Overview

GenSlave is the remote relay control component of the RPi Generator Control suite. It runs on a Raspberry Pi Zero (W or 2W) with a Pimoroni Automation Hat Mini, providing:

- **Relay Control**: Triggers generator start/stop via relay closure
- **Failsafe Monitoring**: Automatically stops generator if communication with GenMaster is lost
- **LCD Display**: Shows system status (GenMaster link, generator state, CPU temp, IP address)
- **REST API**: Full control and monitoring via authenticated HTTP endpoints

GenSlave is designed to be deployed as a Docker container on a headless Raspberry Pi, communicating with GenMaster over your local network or Tailscale VPN.

---

## Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Authentication](#api-authentication)
- [API Endpoints](#api-endpoints)
- [LCD Display](#lcd-display)
- [Failsafe System](#failsafe-system)
- [Managing a Headless Pi](#managing-a-headless-pi)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Hardware Requirements

### Required
- **Raspberry Pi Zero W** or **Raspberry Pi Zero 2W**
- **Pimoroni Automation Hat Mini** - Provides relay, LCD display, and GPIO
- **MicroSD Card** - 8GB minimum, 16GB+ recommended
- **Power Supply** - 5V 2.5A minimum
- **WiFi Network** - For communication with GenMaster

### Recommended
- **Case** - To protect the Pi and HAT
- **Tailscale** - For secure remote access

---

## Installation

### Quick Install (Recommended)

1. **Flash Raspberry Pi OS Lite** to your SD card using Raspberry Pi Imager
   - Enable SSH
   - Configure WiFi
   - Set hostname (e.g., `genslave`)

2. **Boot the Pi and SSH in**:
   ```bash
   ssh pi@genslave.local
   ```

3. **Run the setup script**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/rjsears/pizero_generator_control/main/genslave/setup-docker.sh -o setup-docker.sh
   chmod +x setup-docker.sh
   sudo ./setup-docker.sh
   ```

   If the repository is private, SCP the script instead:
   ```bash
   # From your local machine:
   scp setup-docker.sh pi@genslave.local:~/

   # Then on the Pi:
   chmod +x setup-docker.sh
   sudo ./setup-docker.sh
   ```

4. **Configure the API secret** (see [Configuration](#configuration))

### What the Setup Script Does

1. Updates system packages
2. Installs Docker and docker-compose from Debian repositories
3. Installs and configures Tailscale (optional, prompts for auth key)
4. Creates `/opt/genslave/` directory structure
5. Writes `docker-compose.yaml` and `.env` files
6. Pulls the GenSlave Docker image from Docker Hub
7. Creates a systemd service for auto-start on boot
8. Starts the GenSlave container

---

## Configuration

### Environment Variables

All configuration is done via environment variables in `/opt/genslave/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GENSLAVE_API_SECRET` | **Required**. Shared secret for API authentication. Must match GenMaster's `SLAVE_API_SECRET` | (empty) |
| `HOST` | IP address to bind to | `0.0.0.0` |
| `PORT` | API port | `8001` |
| `LOG_LEVEL` | Logging verbosity: DEBUG, INFO, WARNING, ERROR | `INFO` |
| `FAILSAFE_TIMEOUT_SECONDS` | Seconds without heartbeat before failsafe triggers | `30` |
| `MOCK_HAT_MODE` | Set to `true` to run without hardware (testing) | `false` |
| `WEBHOOK_URL` | Backup notification URL if GenMaster is unreachable | (empty) |
| `WEBHOOK_SECRET` | Secret for webhook HMAC signature | (empty) |

### Setting the API Secret

The `GENSLAVE_API_SECRET` must match the `SLAVE_API_SECRET` configured on GenMaster. This shared secret authenticates all API requests.

**To set or change the API secret:**

```bash
# SSH into the Pi
ssh pi@genslave.local

# Edit the environment file
sudo nano /opt/genslave/.env

# Add or update the line:
GENSLAVE_API_SECRET=your-secret-from-genmaster

# Save and exit (Ctrl+X, Y, Enter)

# Restart the container to apply changes
cd /opt/genslave
sudo docker-compose up -d
```

**To verify the secret is set:**
```bash
# This should return 401 Unauthorized (no API key)
curl http://localhost:8001/api/health

# This should return 200 OK (with correct API key)
curl -H "X-API-Key: your-secret-from-genmaster" http://localhost:8001/api/health
```

---

## API Authentication

All `/api/*` endpoints require authentication via the `X-API-Key` header.

### Request Format
```bash
curl -H "X-API-Key: your-api-secret" http://genslave:8001/api/health
```

### Authentication Responses

| Status Code | Meaning |
|-------------|---------|
| `200 OK` | Request authenticated and processed |
| `401 Unauthorized` | Missing `X-API-Key` header |
| `403 Forbidden` | Invalid API key |

### Public Endpoints

The root endpoint `/` does not require authentication and can be used for basic connectivity checks:

```bash
curl http://genslave:8001/
```

---

## API Endpoints

### Health & Monitoring

#### `GET /` - Service Info (Public)
Basic service information. No authentication required.

**Response:**
```json
{
  "service": "GenSlave",
  "version": "1.0.0",
  "status": "running",
  "armed": false,
  "relay_state": false
}
```

#### `GET /api/health` - Health Check
Detailed health status for monitoring systems.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "relay_state": false,
  "failsafe_active": false,
  "armed": false,
  "mock_mode": false
}
```

**Status Values:**
- `healthy` - All systems normal
- `degraded` - Failsafe triggered or hardware issue
- `unhealthy` - Critical error

#### `GET /api/failsafe` - Failsafe Status
Current state of the failsafe monitor.

**Response:**
```json
{
  "running": true,
  "last_heartbeat": 1705612800,
  "seconds_since_heartbeat": 5,
  "heartbeat_count": 1234,
  "failsafe_triggered": false,
  "failsafe_triggered_at": null,
  "timeout_seconds": 30
}
```

#### `POST /api/heartbeat` - Receive Heartbeat
Called by GenMaster to maintain connection and send commands.

**Request Body:**
```json
{
  "timestamp": 1705612800,
  "generator_running": false,
  "command": "none",
  "armed": true
}
```

**Command Values:**
- `none` - No action
- `start` - Turn relay ON (start generator)
- `stop` - Turn relay OFF (stop generator)

**Response:**
```json
{
  "relay_state": false,
  "uptime": 3600,
  "failsafe_active": false,
  "heartbeat_count": 1235,
  "armed": true
}
```

---

### Relay Control

#### `GET /api/relay/state` - Get Relay State
Current relay and arming status.

**Response:**
```json
{
  "relay_state": false,
  "last_change": 1705612000,
  "change_count": 5,
  "mock_mode": false,
  "armed": true,
  "armed_at": 1705610000
}
```

#### `POST /api/relay/on` - Turn Relay ON
Activates the relay to start the generator.

**Request Body (optional):**
```json
{
  "force": false
}
```

- `force: false` (default) - Requires system to be armed
- `force: true` - Bypasses armed check (emergency use)

**Response:**
```json
{
  "success": true,
  "relay_state": true,
  "message": "Relay turned ON - generator starting"
}
```

**Errors:**
- `403 Forbidden` - System not armed and `force` not set

#### `POST /api/relay/off` - Turn Relay OFF
Deactivates the relay to stop the generator.

**Request Body (optional):**
```json
{
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "relay_state": false,
  "message": "Relay turned OFF - generator stopping"
}
```

*Note: OFF is always allowed for safety, even when not armed.*

---

### Arming Control

The arming system prevents accidental relay activation. When disarmed, relay commands are logged but not executed.

#### `GET /api/relay/arm` - Get Arm Status
**Response:**
```json
{
  "success": true,
  "armed": true,
  "message": "Armed",
  "armed_at": 1705610000
}
```

#### `POST /api/relay/arm` - Arm System
**Request Body (optional):**
```json
{
  "source": "api"
}
```

**Response:**
```json
{
  "success": true,
  "armed": true,
  "message": "Automation armed",
  "armed_at": 1705612800
}
```

#### `POST /api/relay/disarm` - Disarm System
**Response:**
```json
{
  "success": true,
  "armed": false,
  "message": "Automation disarmed",
  "warning": "Relay state unchanged - use explicit off command if needed"
}
```

*Note: Disarming does NOT automatically turn off the relay.*

---

### System Information

#### `GET /api/system` - Full System Info
Comprehensive system metrics including CPU, memory, disk, temperature, and network.

**Response:**
```json
{
  "hostname": "genslave",
  "platform": "linux",
  "cpu_percent": 12.5,
  "ram_total_mb": 512,
  "ram_used_mb": 256,
  "ram_available_mb": 256,
  "ram_percent": 50.0,
  "disk_total_gb": 14.5,
  "disk_used_gb": 3.2,
  "disk_free_gb": 11.3,
  "disk_percent": 22.0,
  "temperature_celsius": 45.0,
  "uptime_seconds": 86400,
  "ip_address": "192.168.1.100",
  "network_interfaces": [
    {
      "interface": "wlan0",
      "ip_address": "192.168.1.100",
      "mac_address": "b8:27:eb:xx:xx:xx",
      "is_wifi": true,
      "wifi_ssid": "MyNetwork",
      "wifi_signal_dbm": -45,
      "wifi_signal_percent": 75
    }
  ],
  "status": "healthy",
  "warnings": []
}
```

**Status Thresholds:**
- CPU > 80%: Warning, > 90%: Critical
- RAM > 80%: Warning, > 90%: Critical
- Disk > 85%: Warning, > 95%: Critical
- Temperature > 70°C: Warning, > 80°C: Critical

#### `POST /api/system/config` - Update Configuration
Allows GenMaster to push configuration changes.

**Request Body:**
```json
{
  "failsafe_timeout_seconds": 60,
  "webhook_url": "https://example.com/webhook",
  "webhook_secret": "secret123"
}
```

*Note: Changes are applied in memory only and do not persist across restarts.*

---

## LCD Display

The Automation Hat Mini includes a 160x80 pixel LCD display showing real-time status:

```
GenMaster: ALIVE
Generator: ARMED
CPU Temp: 101.8F
IP: 192.168.1.100
```

### Display States

**Line 1 - GenMaster Connection:**
| State | Color | Meaning |
|-------|-------|---------|
| `WAITING` | Yellow | No heartbeats received yet |
| `ALIVE` | Green | Heartbeats being received |
| `DOWN` | Red | Heartbeat timeout - connection lost |

**Line 2 - Generator Status:**
| State | Color | Meaning |
|-------|-------|---------|
| `DISARMED` | Yellow | System not armed |
| `ARMED` | White | Armed, generator off |
| `RUNNING` | Green | Generator running |

**Line 3 - CPU Temperature:**
- Blue: Normal (< 150°F / 65°C)
- Yellow: Warm (150-170°F / 65-77°C)
- Red: Hot (> 170°F / 77°C)

**Line 4 - IP Address:**
Shows the primary network IP for easy identification.

---

## Failsafe System

The failsafe system automatically stops the generator if communication with GenMaster is lost.

### How It Works

1. GenMaster sends heartbeats every 60 seconds (configurable)
2. GenSlave tracks time since last heartbeat
3. If no heartbeat for `FAILSAFE_TIMEOUT_SECONDS` (default 30s):
   - Relay is turned OFF (generator stops)
   - Failsafe state is set
   - Optional webhook notification is sent

### Failsafe Conditions

Failsafe only triggers when:
- System is **armed**
- At least one heartbeat has been received previously
- Heartbeat timeout has been exceeded

### Recovering from Failsafe

1. Restore communication with GenMaster
2. GenMaster sends a new heartbeat
3. Failsafe state automatically clears
4. Normal operation resumes

---

## Managing a Headless Pi

Since GenSlave runs on a headless Pi, all management is done via SSH or the API.

### SSH Access

```bash
# Via hostname (if mDNS is working)
ssh pi@genslave.local

# Via IP address
ssh pi@192.168.1.100

# Via Tailscale (if configured)
ssh pi@genslave
```

### Common Management Tasks

#### View Container Logs
```bash
cd /opt/genslave
sudo docker-compose logs -f
```

#### Restart the Container
```bash
cd /opt/genslave
sudo docker-compose restart
```

#### Stop the Container
```bash
cd /opt/genslave
sudo docker-compose down
```

#### Update to Latest Image
```bash
cd /opt/genslave
sudo docker-compose pull
sudo docker-compose up -d
```

#### Check Container Status
```bash
sudo docker ps
# or
cd /opt/genslave
sudo docker-compose ps
```

#### View Environment Configuration
```bash
cat /opt/genslave/.env
```

#### Edit Configuration
```bash
sudo nano /opt/genslave/.env
# After editing:
cd /opt/genslave
sudo docker-compose up -d
```

### Changing the API Key

If you need to change the API key (e.g., security rotation):

1. **Update GenMaster first** with the new `SLAVE_API_SECRET`
2. **Then update GenSlave**:
   ```bash
   ssh pi@genslave.local
   sudo nano /opt/genslave/.env
   # Change: GENSLAVE_API_SECRET=new-secret-here
   cd /opt/genslave
   sudo docker-compose up -d
   ```
3. **Verify** the new key works:
   ```bash
   curl -H "X-API-Key: new-secret-here" http://localhost:8001/api/health
   ```

### Viewing System Metrics via API

```bash
# Full system info
curl -H "X-API-Key: your-key" http://genslave:8001/api/system | jq

# Quick health check
curl -H "X-API-Key: your-key" http://genslave:8001/api/health | jq

# Relay status
curl -H "X-API-Key: your-key" http://genslave:8001/api/relay/state | jq
```

### Reboot the Pi

```bash
sudo reboot
```

The GenSlave container will automatically start on boot via the systemd service.

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
cd /opt/genslave
sudo docker-compose logs
```

**Common issues:**
- Image not pulled: `sudo docker-compose pull`
- Port conflict: Check if something else is using port 8001
- Missing .env file: Ensure `/opt/genslave/.env` exists

### API Returns 401 Unauthorized

**Cause:** Missing `X-API-Key` header

**Fix:** Include the header in your request:
```bash
curl -H "X-API-Key: your-secret" http://genslave:8001/api/health
```

### API Returns 403 Forbidden

**Cause:** API key doesn't match `GENSLAVE_API_SECRET`

**Fix:**
1. Check the secret in `/opt/genslave/.env`
2. Ensure it matches GenMaster's `SLAVE_API_SECRET`
3. Restart the container after changes

### Display Not Working

**Check SPI is enabled:**
```bash
ls -l /dev/spidev*
# Should show /dev/spidev0.0 and /dev/spidev0.1
```

**Enable SPI if missing:**
```bash
sudo raspi-config
# Interface Options -> SPI -> Enable
sudo reboot
```

**Check inside container:**
```bash
sudo docker exec -it genslave python3 -c "from st7735 import ST7735; print('OK')"
```

### Relay Not Responding

**Check if system is armed:**
```bash
curl -H "X-API-Key: your-key" http://localhost:8001/api/relay/state | jq .armed
```

**Arm the system:**
```bash
curl -X POST -H "X-API-Key: your-key" http://localhost:8001/api/relay/arm
```

**Check hardware detection:**
```bash
sudo docker-compose logs | grep -i "automation hat"
```

### Failsafe Keeps Triggering

**Check heartbeat status:**
```bash
curl -H "X-API-Key: your-key" http://localhost:8001/api/failsafe | jq
```

**Common causes:**
- GenMaster not sending heartbeats (check GenMaster logs)
- Network connectivity issues
- API key mismatch (GenMaster can't authenticate)
- Timeout too short (increase `FAILSAFE_TIMEOUT_SECONDS`)

### Network/WiFi Issues

**Check WiFi connection:**
```bash
iwconfig wlan0
```

**Check IP address:**
```bash
hostname -I
```

**Restart networking:**
```bash
sudo systemctl restart networking
```

### Container Logs Show "Mock Mode"

**Cause:** Automation Hat not detected

**Check:**
```bash
# Is the HAT properly seated on GPIO?
# Check I2C devices:
sudo i2cdetect -y 1
```

---

## Development

### Building the Docker Image

The image is cross-compiled on a Mac/Linux machine and pushed to Docker Hub.

**Build for Pi Zero W (arm/v6):**
```bash
cd genslave
./build.sh
```

**Build for Pi Zero 2W (arm/v7):**
Edit `build.sh` line 21:
```bash
PLATFORM="linux/arm/v7"
```
Then run `./build.sh`

### Local Testing (Without Hardware)

Run with mock mode enabled:
```bash
MOCK_HAT_MODE=true python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Project Structure

```
genslave/
├── app/
│   ├── __init__.py
│   ├── auth.py           # API authentication
│   ├── config.py         # Configuration management
│   ├── main.py           # FastAPI application
│   ├── models/           # Pydantic models
│   ├── routers/          # API route handlers
│   │   ├── health.py     # Health & heartbeat endpoints
│   │   ├── relay.py      # Relay control endpoints
│   │   └── system.py     # System info endpoints
│   └── services/         # Business logic
│       ├── display.py    # LCD display service
│       ├── failsafe.py   # Failsafe monitor
│       └── relay.py      # Relay control service
├── Dockerfile            # Docker build configuration
├── build.sh              # Cross-compile build script
├── docker-compose.yaml   # Container orchestration
├── requirements.txt      # Python dependencies
├── setup-docker.sh       # Pi installation script
└── README.md             # This file
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-18 | Initial release with API authentication, LCD display |

---

## License

Part of the RPi Generator Control suite.

Richard J. Sears
richardjsears@protonmail.com
https://github.com/rjsears
