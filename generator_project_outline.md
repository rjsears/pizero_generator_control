# PiZero Generator Control Project - Comprehensive Outline

## 1. Executive Summary

This project creates a wireless generator control system using two Raspberry Pi Zero 2W devices:
- **GenMaster**: Monitors Victron Cerbo GX relay signal, hosts web interface, manages state
- **GenSlave**: Controls generator relay via Automation Hat Mini, responds to GenMaster commands

The system prioritizes reliability, state persistence, and minimal SSD wear through database-centric design.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VICTRON CERBO GX                               │
│                            (MK2 Relay Output)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                            2-Wire Connection
                           (Normally Open Contact)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               GenMaster                                     │
│                          (Raspberry Pi Zero 2W)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  • GPIO17 Input (Victron Signal Sensing)                                    │
│  • FastAPI Backend                                                          │
│  • Vue.js + Tailwind Frontend                                               │
│  • MariaDB Database                                                         │
│  • Nginx Reverse Proxy                                                      │
│  • APScheduler (Scheduled Runs)                                             │
│  • State Management Engine                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                            WiFi / Tailscale
                          (Bidirectional API)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                GenSlave                                     │
│                          (Raspberry Pi Zero 2W)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Automation Hat Mini                                                      │
│    - Relay 1 (GPIO16): Generator Start/Stop                                 │
│    - 0.96" LCD Status Display                                               │
│  • FastAPI Backend (Command Receiver)                                       │
│  • MariaDB Database (Config + State Mirror)                                 │
│  • Heartbeat Responder                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                               Relay Contact
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GENERATOR                                      │
│                     (Remote Start Terminal)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Hardware Requirements

### GenMaster
| Component | Specification |
|-----------|---------------|
| Computer | Raspberry Pi Zero 2W |
| Storage | SSD (via USB adapter recommended) |
| Power | 5V 2.5A supply |
| GPIO | Pin 11 (GPIO17) for Victron input |
| Network | WiFi + Tailscale |

### GenSlave
| Component | Specification |
|-----------|---------------|
| Computer | Raspberry Pi Zero 2W |
| HAT | Pimoroni Automation Hat Mini |
| Storage | SSD (via USB adapter recommended) |
| Power | 5V 2.5A supply |
| Relay | 24V @ 2A max (built into HAT, GPIO16) |
| Display | 0.96" 160x80 LCD (built into HAT) |
| Network | WiFi + Tailscale |

### Victron Connection (GenMaster)
- 2-wire normally-open contact from Cerbo GX MK2 Relay
- Connected to GPIO17 (Pin 11) and Ground (Pin 9 or similar)
- Internal pull-up resistor enabled on GPIO17

---

## 4. Software Stack

### Core Technologies
| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | FastAPI | REST API, async operations |
| Frontend | Vue.js 3 | Reactive UI components |
| Styling | Tailwind CSS | Lightweight, responsive design |
| Database | MariaDB | State persistence, logging |
| ORM | SQLAlchemy | Database abstraction |
| Scheduler | APScheduler | Scheduled generator runs |
| Charts | Chart.js | Runtime graphs, statistics |
| Web Server | Nginx | Reverse proxy, static files |
| GPIO | gpiozero | Python GPIO library (simpler than RPi.GPIO) |
| HAT | automationhat | Pimoroni library for Automation Hat Mini |
| Container | Docker + Docker Compose | Application isolation |

### Python Libraries
```
fastapi
uvicorn[standard]
sqlalchemy
pymysql
apscheduler
gpiozero
pigpio  # For remote GPIO if needed
automationhat  # GenSlave only
psutil  # System monitoring
httpx  # Async HTTP client for API calls
pydantic  # Data validation
python-dotenv  # Configuration
```

---

## 5. GenMaster Component Details

### 5.1 GPIO Input Monitoring

```python
# Conceptual implementation using gpiozero
from gpiozero import Button
from signal import pause

victron_signal = Button(17, pull_up=True, bounce_time=0.1)

def on_generator_requested():
    """Called when Victron closes the relay (GPIO17 goes LOW)"""
    # Update state, notify GenSlave to start generator
    pass

def on_generator_stop_requested():
    """Called when Victron opens the relay (GPIO17 goes HIGH)"""
    # Update state, notify GenSlave to stop generator
    pass

victron_signal.when_pressed = on_generator_requested
victron_signal.when_released = on_generator_stop_requested
```

### 5.2 State Machine

```
                    ┌──────────────────┐
                    │      IDLE        │
                    │ (Generator Off)  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ VICTRON_START │   │ MANUAL_START  │   │ SCHEDULED_START│
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   STARTING    │
                    │ (Cmd Sent)    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   RUNNING     │
                    │ (Confirmed)   │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ VICTRON_STOP  │   │ MANUAL_STOP   │   │ SCHEDULED_END │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   STOPPING    │
                    │ (Cmd Sent)    │
                    └───────┬───────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │      IDLE        │
                    └──────────────────┘
```

### 5.3 API Endpoints (GenMaster)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Current system status |
| GET | `/api/generator/state` | Generator running state |
| POST | `/api/generator/start` | Manual start (with duration) |
| POST | `/api/generator/stop` | Manual stop |
| GET | `/api/health` | GenSlave health status |
| POST | `/api/health/test` | Test webhook |
| POST | `/api/override/enable` | Enable manual override |
| POST | `/api/override/disable` | Disable manual override |
| GET | `/api/stats` | Runtime statistics |
| GET | `/api/system` | CPU, RAM, Temp, Disk |
| POST | `/api/schedule` | Create scheduled run |
| GET | `/api/schedule` | List scheduled runs |
| DELETE | `/api/schedule/{id}` | Cancel scheduled run |
| POST | `/api/backup` | Trigger database backup |
| GET | `/api/backup/download` | Download backup file |
| POST | `/api/reboot` | Reboot GenMaster |
| GET | `/api/config` | Get configuration |
| PUT | `/api/config` | Update configuration |

---

## 6. GenSlave Component Details

### 6.1 Automation Hat Mini Control

```python
# Conceptual implementation
import automationhat
import time

# Initialize (must run after HAT is ready)
time.sleep(0.1)

def start_generator():
    """Close relay to start generator"""
    automationhat.relay.one.on()
    return automationhat.relay.one.is_on()

def stop_generator():
    """Open relay to stop generator"""
    automationhat.relay.one.off()
    return not automationhat.relay.one.is_on()

def get_relay_state():
    """Check current relay state"""
    return automationhat.relay.one.is_on()

def update_lcd_status(status_text):
    """Update LCD display with current status"""
    # automationhat includes ST7735 display support
    pass
```

### 6.2 API Endpoints (GenSlave)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Current relay state + health |
| POST | `/api/relay/on` | Close relay (start generator) |
| POST | `/api/relay/off` | Open relay (stop generator) |
| GET | `/api/relay/state` | Get relay state only |
| POST | `/api/heartbeat` | Heartbeat ping from GenMaster |
| GET | `/api/health` | GenMaster health from GenSlave perspective |
| GET | `/api/system` | CPU, RAM, Temp, Disk |
| POST | `/api/config` | Receive config push from GenMaster |

### 6.3 LCD Display Content

The Automation Hat Mini's 160x80 LCD can show:
- Current relay state (ON/OFF)
- Last heartbeat time
- GenMaster connection status
- Generator runtime (if running)
- IP address for debugging

---

## 7. Communication Protocol

### 7.1 Heartbeat Design

**Requirements:**
- Bidirectional (each knows the other is alive)
- Lightweight (minimal bandwidth/resources)
- Foolproof with failsafes
- 60-second interval
- Configurable failure threshold (default: 3 misses = 180 seconds)

**Proposed Protocol:**

```
GenMaster                                    GenSlave
    │                                            │
    │──────── POST /api/heartbeat ──────────────▶│
    │         {                                  │
    │           "timestamp": 1234567890,         │
    │           "master_state": {...},           │
    │           "sequence": 42                   │
    │         }                                  │
    │                                            │
    │◀─────── Response ─────────────────────────│
    │         {                                  │
    │           "timestamp": 1234567891,         │
    │           "slave_state": {...},            │
    │           "relay_state": true,             │
    │           "sequence_ack": 42               │
    │         }                                  │
    │                                            │
```

**Heartbeat State Tracking:**
- Both sides store `last_heartbeat_timestamp` (Unix epoch) in database
- Both sides store `missed_heartbeat_count` in database
- On successful heartbeat: reset `missed_heartbeat_count` to 0
- On missed heartbeat: increment `missed_heartbeat_count`
- When `missed_heartbeat_count` >= threshold: trigger failsafe

### 7.2 Failsafe Behavior

**GenMaster loses contact with GenSlave:**
1. Increment missed heartbeat counter
2. After threshold reached:
   - Send "Lost Communication" webhook notification
   - Set `override_mode = SHUTDOWN` (prevent sending start commands)
   - Log event to database
3. When communication restored:
   - Send "Communication Restored" webhook
   - Check if generator should be running (re-sync state)
   - Clear override if appropriate

**GenSlave loses contact with GenMaster:**
1. Increment missed heartbeat counter
2. After threshold reached:
   - If generator is running: STOP generator immediately
   - Send "Lost Communication - Generator Stopped" webhook (direct to n8n)
   - Update LCD: "COMM LOST - SHUTDOWN"
3. When communication restored:
   - Send "Communication Restored" webhook
   - Wait for explicit command from GenMaster

### 7.3 Command Authentication

For added security (even on Tailscale), consider:
- Shared secret in headers: `X-GenControl-Secret: <configured_secret>`
- Request signing with timestamp to prevent replay attacks

---

## 8. Database Schema

### 8.1 GenMaster Tables

```sql
-- System State (single row, always ID=1)
CREATE TABLE system_state (
    id INT PRIMARY KEY DEFAULT 1,
    generator_running BOOLEAN DEFAULT FALSE,
    generator_start_time BIGINT NULL,
    run_trigger ENUM('idle', 'victron', 'manual', 'scheduled') DEFAULT 'idle',
    override_enabled BOOLEAN DEFAULT FALSE,
    override_type ENUM('none', 'force_run', 'force_stop') DEFAULT 'none',
    victron_signal_state BOOLEAN DEFAULT FALSE,
    last_heartbeat_sent BIGINT NULL,
    last_heartbeat_received BIGINT NULL,
    missed_heartbeat_count INT DEFAULT 0,
    slave_connection_status ENUM('connected', 'disconnected') DEFAULT 'disconnected',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Configuration
CREATE TABLE config (
    id INT PRIMARY KEY DEFAULT 1,
    heartbeat_interval_seconds INT DEFAULT 60,
    heartbeat_failure_threshold INT DEFAULT 3,
    webhook_base_url VARCHAR(255),
    webhook_secret VARCHAR(255),
    slave_api_url VARCHAR(255),
    slave_api_secret VARCHAR(255),
    notification_enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Generator Run History
CREATE TABLE generator_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time BIGINT NOT NULL,
    stop_time BIGINT NULL,
    duration_seconds INT NULL,
    trigger_type ENUM('victron', 'manual', 'scheduled') NOT NULL,
    stop_reason ENUM('victron', 'manual', 'scheduled_end', 'comm_loss', 'override') NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Runs
CREATE TABLE scheduled_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scheduled_start BIGINT NOT NULL,
    duration_minutes INT NOT NULL,
    recurring BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(50) NULL,  -- cron-like pattern
    enabled BOOLEAN DEFAULT TRUE,
    last_executed BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event Log (minimal, for critical events only)
CREATE TABLE event_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created (created_at),
    INDEX idx_type (event_type)
);
```

### 8.2 GenSlave Tables

```sql
-- System State (single row, always ID=1)
CREATE TABLE system_state (
    id INT PRIMARY KEY DEFAULT 1,
    relay_state BOOLEAN DEFAULT FALSE,
    relay_on_time BIGINT NULL,
    last_heartbeat_received BIGINT NULL,
    missed_heartbeat_count INT DEFAULT 0,
    master_connection_status ENUM('connected', 'disconnected') DEFAULT 'disconnected',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Configuration (pushed from GenMaster)
CREATE TABLE config (
    id INT PRIMARY KEY DEFAULT 1,
    heartbeat_interval_seconds INT DEFAULT 60,
    heartbeat_failure_threshold INT DEFAULT 3,
    webhook_base_url VARCHAR(255),
    webhook_secret VARCHAR(255),
    master_api_url VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

---

## 9. Web Interface Design

### 9.1 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GenMaster Control Panel                              [Backup] [Reboot]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │    GENERATOR STATUS     │  │    COMMUNICATION        │                   │
│  │  ━━━━━━━━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━━━━━━━━  │                   │
│  │                         │  │                         │                   │
│  │   ● RUNNING             │  │   GenSlave: ● ONLINE    │                   │
│  │   Runtime: 02:34:15     │  │   Last Ping: 12s ago    │                   │
│  │   Trigger: Victron      │  │   Latency: 45ms         │                   │
│  │                         │  │                         │                   │
│  │   [STOP GENERATOR]      │  │   [Test Webhook]        │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │    VICTRON INPUT        │  │    MANUAL OVERRIDE      │                   │
│  │  ━━━━━━━━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━━━━━━━━  │                   │
│  │                         │  │                         │                   │
│  │   GPIO17: ● ACTIVE      │  │   Override: [OFF ◯━━●]  │                   │
│  │   (Run Requested)       │  │                         │                   │
│  │                         │  │   Status: Auto Mode     │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │    MANUAL START                                                      │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │   │
│  │                                                                      │   │
│  │    Duration: [____] minutes    [START GENERATOR]                     │   │
│  │                                                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │    STATISTICS                                                        │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │   │
│  │   ┌────────────────────────────────────────────────────────────┐    │   │
│  │   │  [Chart.js - Generator Runtime History - Last 30 Days]    │    │   │
│  │   └────────────────────────────────────────────────────────────┘    │   │
│  │   Total Runtime This Month: 45h 23m    │    Run Count: 127         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │    GENMASTER HEALTH     │  │    GENSLAVE HEALTH      │                   │
│  │  ━━━━━━━━━━━━━━━━━━━━━  │  │  ━━━━━━━━━━━━━━━━━━━━━  │                   │
│  │   CPU:  ████░░░░ 45%    │  │   CPU:  ██░░░░░░ 22%    │                   │
│  │   RAM:  ███░░░░░ 38%    │  │   RAM:  ██░░░░░░ 28%    │                   │
│  │   Temp: 52°C            │  │   Temp: 48°C            │                   │
│  │   Disk: ██████░░ 75%    │  │   Disk: ████░░░░ 50%    │                   │
│  │   Health: ● Good        │  │   Health: ● Good        │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │    SCHEDULED RUNS                                         [+ Add]    │   │
│  │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │   │
│  │   │ Time          │ Duration │ Recurring │ Status   │ Actions │      │   │
│  │   │ Tomorrow 6am  │ 30 min   │ Weekly    │ Active   │ [✎][✕]  │      │   │
│  │   │ Jan 15 10am   │ 15 min   │ Once      │ Active   │ [✎][✕]  │      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Color Scheme

| Element | Color | Hex |
|---------|-------|-----|
| Running/Active | Green | #22C55E |
| Stopped/Inactive | Gray | #6B7280 |
| Warning | Amber | #F59E0B |
| Error/Critical | Red | #EF4444 |
| Background | Dark Gray | #1F2937 |
| Card Background | Darker Gray | #111827 |
| Text Primary | White | #F9FAFB |
| Text Secondary | Light Gray | #9CA3AF |

---

## 10. Notification System (Webhooks)

### 10.1 Webhook Events

| Event | Trigger | Priority |
|-------|---------|----------|
| `generator.started.victron` | Victron closes relay | Normal |
| `generator.started.manual` | User clicks Start | Normal |
| `generator.started.scheduled` | Scheduled run begins | Normal |
| `generator.stopped.victron` | Victron opens relay | Normal |
| `generator.stopped.manual` | User clicks Stop | Normal |
| `generator.stopped.scheduled` | Scheduled run ends | Normal |
| `generator.stopped.comm_loss` | GenSlave failsafe | Critical |
| `communication.lost` | Heartbeat threshold exceeded | Critical |
| `communication.restored` | Heartbeat resumed | Normal |
| `override.enabled` | Manual override activated | Warning |
| `override.disabled` | Automatic mode restored | Normal |
| `system.reboot` | Reboot initiated | Warning |
| `health.warning` | Temp/Disk/RAM threshold | Warning |

### 10.2 Webhook Payload Structure

```json
{
  "event": "generator.started.victron",
  "timestamp": 1705234567,
  "source": "genmaster",
  "data": {
    "generator_state": "running",
    "trigger": "victron",
    "runtime_seconds": 0
  },
  "meta": {
    "sequence": 12345,
    "version": "1.0.0"
  }
}
```

### 10.3 n8n Integration

Assuming direct access to n8n_management instance, create webhook receivers:
- `POST /webhook/generator-control` - Main event receiver
- Create n8n workflow to parse event type and route to appropriate notification channels

---

## 11. Boot Recovery Process

### 11.1 GenMaster Boot Sequence

```
1. Start Docker containers
2. Wait for MariaDB ready
3. Read system_state from database
4. Read config from database
5. Initialize GPIO17 monitoring
6. Check current GPIO17 state
7. Attempt contact with GenSlave
   ├─► Success: Query GenSlave relay state
   │   ├─► If DB says should run AND Victron says run AND relay off → Send start
   │   ├─► If DB says should run AND Victron says stop AND not manual → Send stop
   │   └─► If DB says not running AND relay on → Send stop
   └─► Failure: Mark GenSlave disconnected, set override=shutdown
8. Start heartbeat scheduler
9. Start web server
10. Send "System Boot Complete" webhook
```

### 11.2 GenSlave Boot Sequence

```
1. Start Docker containers
2. Wait for MariaDB ready
3. Read system_state from database
4. Read config from database
5. Initialize Automation Hat Mini
6. Read current relay state from hardware
7. Compare hardware state with DB state
   ├─► Mismatch: Trust hardware, update DB
   └─► Match: Continue
8. Start heartbeat listener
9. Start API server
10. Update LCD with status
11. Wait for GenMaster heartbeat
```

---

## 12. Docker Considerations

### 12.1 Pros of Docker

| Advantage | Description |
|-----------|-------------|
| Isolation | Application runs in isolated environment |
| Reproducibility | Same container works identically on any Pi |
| Easy Updates | Pull new image, restart container |
| Dependency Management | All dependencies bundled in image |
| Easy Backup/Restore | Volume mounts for persistent data |
| Resource Limits | Can limit CPU/memory per container |

### 12.2 Cons of Docker

| Disadvantage | Description |
|--------------|-------------|
| GPIO Access | Requires `--privileged` or device mapping |
| Memory Overhead | ~50-100MB additional RAM usage |
| Complexity | Additional layer to debug |
| SSD Writes | Docker logs can increase writes |
| Boot Time | Slightly slower startup |

### 12.3 Recommended Docker Configuration

```yaml
# docker-compose.yml for GenMaster
version: '3.8'

services:
  genmaster:
    build: .
    privileged: true  # Required for GPIO
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - /sys:/sys:ro  # For system monitoring
    environment:
      - DATABASE_URL=mysql+pymysql://genmaster:password@db/genmaster
    depends_on:
      - db
    networks:
      - gennet

  db:
    image: mariadb:10.11
    restart: unless-stopped
    volumes:
      - db_data:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=genmaster
      - MYSQL_USER=genmaster
      - MYSQL_PASSWORD=password
    networks:
      - gennet
    # Reduce SSD writes
    command: >
      --innodb_flush_log_at_trx_commit=2
      --sync_binlog=0
      --innodb_flush_method=O_DIRECT

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
    depends_on:
      - genmaster
    networks:
      - gennet

volumes:
  db_data:

networks:
  gennet:
```

### 12.4 GPIO Access in Docker

For GenMaster (GPIO17 input):
```yaml
devices:
  - /dev/gpiomem:/dev/gpiomem
```

For GenSlave (Automation Hat Mini requires I2C, SPI, GPIO):
```yaml
privileged: true
# OR more granular:
devices:
  - /dev/gpiomem:/dev/gpiomem
  - /dev/i2c-1:/dev/i2c-1
  - /dev/spidev0.0:/dev/spidev0.0
  - /dev/spidev0.1:/dev/spidev0.1
```

---

## 13. SSD Longevity Considerations

### 13.1 Write Reduction Strategies

| Strategy | Implementation |
|----------|----------------|
| Disable swap | `sudo swapoff -a` |
| tmpfs for temp files | Mount `/tmp` as tmpfs |
| Reduce DB sync | `innodb_flush_log_at_trx_commit=2` |
| No log files | All logging to database only |
| Batch DB writes | Buffer non-critical writes |
| Disable Docker logs | `logging: driver: none` |

### 13.2 Setup Script Configuration

```bash
# In setup.sh
# Disable swap
sudo systemctl disable dphys-swapfile
sudo swapoff -a

# Mount tmp as tmpfs
echo "tmpfs /tmp tmpfs defaults,noatime,nosuid,size=100m 0 0" | sudo tee -a /etc/fstab

# Reduce journald writes
sudo mkdir -p /etc/systemd/journald.conf.d/
echo "[Journal]
Storage=volatile
RuntimeMaxUse=50M" | sudo tee /etc/systemd/journald.conf.d/reduce-writes.conf
```

---

## 14. Remote Access & Networking

### 14.1 Overview

Remote access is essential for managing the generator control system when away from the local network. We use a layered approach:

| Layer | Technology | Status | Purpose |
|-------|------------|--------|---------|
| Primary | **Tailscale** | Required | Secure mesh VPN for all device communication |
| Secondary | **Cloudflare Tunnel** | Optional | Public web access without exposing ports |

### 14.2 Tailscale (Required)

**Why Tailscale is Required:**
- Creates secure mesh network between GenMaster, GenSlave, and your devices
- Both Pi Zeros get stable IPs (100.x.x.x) accessible from anywhere
- Direct communication between n8n_management and generator devices
- WireGuard-based encryption with minimal overhead
- MagicDNS provides hostname resolution (genmaster, genslave)

**Resource Usage on Pi Zero 2W:**
| Metric | Value | Impact |
|--------|-------|--------|
| RAM | ~20-30MB | Acceptable (4-6% of 512MB) |
| CPU (idle) | <1% | Negligible |
| CPU (active) | 2-5% | Minimal during transfers |
| Network | WireGuard kernel module | Very efficient |

**Network Architecture with Tailscale:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           YOUR DEVICES                                      │
│              (Phone, Laptop, Desktop - all on Tailscale)                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          Tailscale Mesh Network
                            (Encrypted WireGuard)
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  GenMaster    │◄─────────►│   GenSlave    │           │ n8n_management│
│ 100.x.x.101   │  Heartbeat│ 100.x.x.102   │           │  100.x.x.50   │
│               │  Commands │               │           │               │
│ - Web UI      │           │ - Relay API   │◄─────────►│ - Webhooks    │
│ - Master API  │           │ - LCD Display │  Notifs   │ - Automation  │
└───────────────┘           └───────────────┘           └───────────────┘
```

**Tailscale Configuration:**

```bash
# Tailscale auth key types:
# - Reusable: For multiple devices (recommended for initial setup)
# - Single-use: More secure, one device per key
# - Pre-approved: Skip admin approval step

# Setup command (run by setup.sh)
tailscale up --authkey=tskey-auth-xxxxx --hostname=genmaster
```

**Docker Integration:**

```yaml
# Tailscale as sidecar container
services:
  tailscale:
    image: tailscale/tailscale:latest
    hostname: genmaster  # or genslave
    environment:
      - TS_AUTHKEY=${TAILSCALE_AUTHKEY}
      - TS_STATE_DIR=/var/lib/tailscale
      - TS_USERSPACE=false
    volumes:
      - tailscale_state:/var/lib/tailscale
      - /dev/net/tun:/dev/net/tun
    cap_add:
      - NET_ADMIN
      - NET_RAW
    restart: unless-stopped
    network_mode: host  # Required for proper networking

volumes:
  tailscale_state:
```

**ACL Configuration (Tailscale Admin Console):**

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:admin"],
      "dst": ["tag:generator:*"]
    },
    {
      "action": "accept",
      "src": ["tag:generator"],
      "dst": ["tag:generator:*", "tag:n8n:*"]
    }
  ],
  "tagOwners": {
    "tag:generator": ["autogroup:admin"],
    "tag:n8n": ["autogroup:admin"],
    "tag:admin": ["autogroup:admin"]
  }
}
```

### 14.3 Cloudflare Tunnel (Optional)

**When to Use Cloudflare Tunnel:**
- Access web UI from devices NOT on Tailscale (guest access)
- Public webhook endpoint for external services
- Redundant access path if Tailscale has issues

**When NOT to Use:**
- All your devices are on Tailscale (most common case)
- Concerned about resource usage on Pi Zero
- Want to minimize complexity

**Resource Usage on Pi Zero 2W:**
| Metric | Value | Impact |
|--------|-------|--------|
| RAM | ~50-100MB | Significant (10-20% of 512MB) |
| CPU (idle) | 2-3% | Noticeable |
| CPU (active) | 5-15% | Higher during traffic |
| Combined w/Tailscale | ~80-130MB RAM | May cause memory pressure |

**Architecture with Cloudflare Tunnel:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                       │
│                   (Any device, anywhere, no VPN needed)                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                   HTTPS
                        genmaster.yourdomain.com
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUDFLARE EDGE                                     │
│                    (DDoS protection, SSL termination)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                          Cloudflare Tunnel
                         (Outbound connection)
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            GenMaster                                        │
│                         (cloudflared daemon)                                │
│                                                                             │
│   Internet Traffic ──► cloudflared ──► nginx ──► FastAPI                    │
│                                                                             │
│   Tailscale Traffic ──────────────────► nginx ──► FastAPI                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Cloudflare Tunnel Docker Configuration:**

```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    restart: unless-stopped
    network_mode: host
    profiles:
      - cloudflare  # Only starts if profile is specified
```

**Nginx Configuration for Dual Access:**

```nginx
# /etc/nginx/conf.d/genmaster.conf

# Geo-based access classification
geo $access_level {
    default          "external";
    127.0.0.1/32     "internal";
    100.64.0.0/10    "internal";    # Tailscale CGNAT range
    172.16.0.0/12    "internal";    # Docker networks
    10.0.0.0/8       "internal";    # Private networks
    192.168.0.0/16   "internal";    # Private networks
}

server {
    listen 80;
    server_name _;

    # Full access for Tailscale/internal
    location / {
        if ($access_level = "internal") {
            proxy_pass http://127.0.0.1:8000;
            break;
        }
        # External access - require Cloudflare Access auth or limit endpoints
        return 403;
    }

    # API endpoints - always available (protected by API secret)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Access-Level $access_level;
    }
}
```

### 14.4 Setup Script Integration

The setup.sh script will handle network configuration with interactive prompts:

```bash
# Network setup flow in setup.sh

configure_networking() {
    print_section "Network Configuration"

    # Tailscale (Required)
    print_subsection "Tailscale Setup (Required)"
    print_info "Tailscale provides secure remote access to your devices"

    if ! command -v tailscale &> /dev/null; then
        print_info "Installing Tailscale..."
        curl -fsSL https://tailscale.com/install.sh | sh
    fi

    read_masked_token "Enter Tailscale Auth Key" TAILSCALE_AUTHKEY

    # Cloudflare Tunnel (Optional)
    print_subsection "Cloudflare Tunnel (Optional)"
    print_info "Cloudflare Tunnel allows public web access without exposing ports"
    print_warning "Adds ~50-100MB RAM usage"

    if confirm_prompt "Enable Cloudflare Tunnel?" "n"; then
        CLOUDFLARE_ENABLED=true
        read_masked_token "Enter Cloudflare Tunnel Token" CLOUDFLARE_TUNNEL_TOKEN
        prompt_with_default "Public hostname" "genmaster.example.com" CLOUDFLARE_HOSTNAME
    else
        CLOUDFLARE_ENABLED=false
    fi

    save_state
}
```

### 14.5 Memory Budget Analysis

**Pi Zero 2W Total RAM: 512MB**

| Component | RAM Usage | With CF Tunnel |
|-----------|-----------|----------------|
| Linux OS | ~50MB | ~50MB |
| Docker Engine | ~50MB | ~50MB |
| MariaDB | ~80MB | ~80MB |
| FastAPI + Uvicorn | ~40MB | ~40MB |
| Nginx | ~10MB | ~10MB |
| Tailscale | ~25MB | ~25MB |
| Cloudflare Tunnel | - | ~75MB |
| Vue.js (browser) | ~30MB | ~30MB |
| **Total** | **~285MB** | **~360MB** |
| **Available** | **~227MB** | **~152MB** |

**Recommendation:** Cloudflare Tunnel is viable but reduces available memory significantly. Only enable if you have a specific need for public access.

### 14.6 Database Schema Updates for Networking

```sql
-- Add to config table
ALTER TABLE config ADD COLUMN tailscale_hostname VARCHAR(50);
ALTER TABLE config ADD COLUMN tailscale_ip VARCHAR(45);
ALTER TABLE config ADD COLUMN cloudflare_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE config ADD COLUMN cloudflare_hostname VARCHAR(255);
```

---

## 15. Security Considerations

| Concern | Mitigation |
|---------|------------|
| API Authentication | Shared secret in headers + HTTPS via Tailscale |
| Database Access | Local socket only, strong passwords |
| GPIO Access | Container isolation, minimal privileges |
| Web Interface | Tailscale-only by default, Cloudflare Access if public |
| Webhook Security | Signed payloads with timestamp |
| Network Isolation | Tailscale ACLs limit device communication |
| Public Access | Cloudflare Access authentication (if tunnel enabled) |

---

## 16. Questions and Clarifications Needed

### Hardware Questions

1. **Victron Relay Behavior**: When the Victron relay closes, does it connect GPIO17 to ground, or does it provide a voltage? (Assuming ground connection based on "normally open" description)

2. **Generator Start Mechanism**: Does the generator have a momentary start requirement (pulse) or a continuous contact requirement (hold relay closed while running)?

3. **Generator Feedback**: Is there any way to confirm the generator actually started (vibration sensor, voltage feedback, etc.), or do we assume success if relay closes?

### Software Questions

4. **n8n Webhook Format**: What is the exact URL format and authentication method for your n8n instance? Do you want notifications via a specific channel (email, Slack, SMS)?

5. **Web Interface Access**: Will the web interface be accessed only via Tailscale (private IP), or do you need public access with authentication?

6. **Scheduled Run Recurrence**: For recurring scheduled runs, do you want full cron-style flexibility, or simpler options (daily, weekly, monthly)?

7. **Override Behavior**: When manual override is enabled:
   - Should it FORCE the generator to run regardless of Victron?
   - Or should it PREVENT the generator from running regardless of Victron?
   - Or should it be a toggle for both behaviors?

8. **Database Backup**: Where should the backup file be stored? Local download only, or also push to external storage (S3, etc.)?

### Operational Questions

9. **Heartbeat Failure Response**: If GenMaster loses communication and then Victron requests a start, should we:
   - Queue the request until communication is restored?
   - Immediately notify and do nothing?
   - Attempt to start anyway and hope for the best?

10. **GenSlave LCD Content**: What specific information do you want displayed on the Automation Hat Mini's LCD?

11. **System Health Thresholds**: At what values should we send health warnings?
    - Temperature: 70°C? 80°C?
    - Disk usage: 80%? 90%?
    - RAM usage: 85%? 90%?

12. **Event Log Retention**: How long should we keep event logs in the database? (7 days? 30 days? Forever?)

---

## 17. Implementation Roadmap

### Phase 1: Foundation
- [ ] Set up development environment
- [ ] Create project structure
- [ ] Implement database models (SQLAlchemy)
- [ ] Create basic FastAPI application
- [ ] Test GPIO reading on GenMaster (GPIO17)
- [ ] Test Automation Hat Mini on GenSlave (relay control)

### Phase 2: Core Communication
- [ ] Implement GenSlave API endpoints
- [ ] Implement GenMaster API endpoints
- [ ] Create heartbeat protocol
- [ ] Implement failsafe logic
- [ ] Test bidirectional communication

### Phase 3: State Management
- [ ] Implement state machine
- [ ] Create boot recovery logic
- [ ] Implement Victron signal monitoring
- [ ] Add manual start/stop functionality
- [ ] Test state persistence across reboots

### Phase 4: Web Interface
- [ ] Set up Vue.js project with Tailwind
- [ ] Create dashboard components
- [ ] Implement real-time status updates
- [ ] Add Chart.js visualizations
- [ ] Create configuration pages

### Phase 5: Notifications
- [ ] Design webhook payload format
- [ ] Implement webhook sender
- [ ] Create n8n workflows
- [ ] Test all notification events
- [ ] Add webhook test button

### Phase 6: Scheduling
- [ ] Implement APScheduler integration
- [ ] Create scheduled run management
- [ ] Add recurring run support
- [ ] Test schedule execution

### Phase 7: Containerization
- [ ] Create GenMaster Dockerfile
- [ ] Create GenSlave Dockerfile
- [ ] Create docker-compose files
- [ ] Test GPIO access in containers
- [ ] Create setup.sh scripts

### Phase 8: Remote Access & Networking
- [ ] Integrate Tailscale into Docker Compose
- [ ] Configure Tailscale auth key handling in setup.sh
- [ ] Implement optional Cloudflare Tunnel support
- [ ] Configure nginx for dual access (Tailscale + Cloudflare)
- [ ] Test remote connectivity and failover
- [ ] Document Tailscale ACL configuration

### Phase 9: Polish & Testing
- [ ] Implement database backup/restore
- [ ] Add system health monitoring
- [ ] Comprehensive testing
- [ ] Documentation
- [ ] Performance optimization

---

## 18. File Structure (Proposed)

```
pizero_generator_control/
├── genmaster/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── state.py
│   │   │   ├── config.py
│   │   │   ├── runs.py
│   │   │   └── schedules.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── generator.py
│   │   │   ├── health.py
│   │   │   ├── system.py
│   │   │   ├── schedule.py
│   │   │   └── config.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── gpio.py          # Victron signal monitoring
│   │   │   ├── heartbeat.py     # GenSlave communication
│   │   │   ├── state_machine.py # State management
│   │   │   ├── webhook.py       # Notification sender
│   │   │   └── scheduler.py     # APScheduler wrapper
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── system_info.py   # CPU, RAM, Temp, Disk
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── main.js
│   │   │   ├── App.vue
│   │   │   ├── components/
│   │   │   └── views/
│   │   ├── package.json
│   │   ├── tailwind.config.js
│   │   └── vite.config.js
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── nginx.conf
│   └── requirements.txt
├── genslave/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── state.py
│   │   │   └── config.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── relay.py
│   │   │   ├── heartbeat.py
│   │   │   └── system.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── relay.py         # Automation Hat control
│   │   │   ├── lcd.py           # Display management
│   │   │   ├── heartbeat.py     # GenMaster monitoring
│   │   │   └── failsafe.py      # Auto-shutdown logic
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── system_info.py
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── setup.sh                     # Main setup script (--GenMaster or --GenSlave)
├── config/
│   ├── tailscale/
│   │   └── .gitkeep             # Tailscale state stored here
│   └── cloudflare/
│       └── .gitkeep             # Cloudflare config (if enabled)
├── scripts/
│   ├── backup.sh                # Database backup script
│   └── health-check.sh          # System health monitoring
├── instructions.md
├── generator_project_outline.md # This document
└── README.md
```

---

## 19. Next Steps

Once you've reviewed this outline and answered the questions above, we can:

1. Finalize the technical decisions (especially around Docker and webhook integration)
2. Begin implementing Phase 1 (Foundation)
3. Create the actual project structure and start coding

I'm ready to dive deeper into any section or start implementation when you give the go-ahead.
