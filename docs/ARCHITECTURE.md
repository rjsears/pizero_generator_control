# GenMaster/GenSlave System Architecture

## Overview

The RPi Generator Control system is a distributed two-device architecture for automated generator management. It uses a master-slave pattern where GenMaster (Raspberry Pi 5) handles the web interface, business logic, and Victron integration, while GenSlave (Pi Zero 2W) controls the physical relay for generator start/stop.

---

## System Architecture

![System Architecture](../images/genmaster_slave_arch.png)

---

## GenMaster Docker Container Architecture

![Docker Compose Stack](images/docker_compose_stack.jpeg)

---

## GenSlave Container Architecture

GenSlave runs as a single Docker container on the Pi Zero 2W. The image
(`rjsears/pizero_generator_control:genslave`) is built for `linux/arm/v6`
and ships from Docker Hub, so the Pi Zero only needs Docker installed —
no Python, no virtualenv, no system packages.

The container runs `privileged` for GPIO access to the Pimoroni Automation
Hat Mini, and uses `network_mode: host` so Tailscale on the host can route
inbound API calls from GenMaster directly to the container's port 8001.

![GenSlave Architecture](images/genslave_arch.jpeg)

### GenSlave Host File Structure

The Pi Zero only stores the compose file and runtime state — the application
code itself lives entirely inside the image:

```
/opt/genslave/
├── docker-compose.yaml      # Pulled from the repo on install
└── .env                     # Per-host configuration (API secret, GenMaster URL, etc.)
```

Two named Docker volumes hold mutable state across container recreates:

| Volume | Mount inside container | Purpose |
|--------|------------------------|---------|
| `genslave_data` | `/opt/genslave/data` | SQLite database (optional state cache) |
| `genslave_logs` | `/opt/genslave/logs` | Application logs |

### What's inside the image

The container's `/app` directory contains the FastAPI service:

```
/app/
├── main.py                  # FastAPI application
├── config.py                # Configuration from environment
├── routers/
│   ├── health.py            # Health check + heartbeat
│   ├── relay.py             # Relay control + arming
│   └── system.py            # System info
└── services/
    ├── relay.py             # Automation Hat Mini control
    └── failsafe.py          # Heartbeat monitor
```

Updates are deployed by pulling a newer tag of the image and recreating the
container — no source files on the Pi Zero ever change.

---

## Request Flow Architecture

![Request Flow](images/request_flow.jpeg)

---

## Heartbeat System Architecture

The heartbeat system ensures reliable communication between GenMaster and GenSlave, with failsafe mechanisms.

![Heartbeat System](images/heartbeat.jpeg)

---

## Boot Sequence / Power Loss Recovery

Both GenMaster and GenSlave implement safety measures for power loss and reboot scenarios.

![Boot Sequence](images/boot_sequence.png)

### Boot Arming Policy

GenMaster's behavior on reboot is controlled by an operator-configurable policy
(`config.boot_arming_policy`), exposed in the UI under
**Generator → Boot Arming Policy**. The setting is stored in the database
and persists across reboots. There are two valid values:

| Policy | What happens on GenMaster boot | When to use it |
|--------|--------------------------------|----------------|
| `fail_safe` (default) | If the relay was armed pre-boot, it is **disarmed**. `manual_disarm_active` is set. A `boot_disarmed_failsafe` notification fires so the operator knows the generator will not start until they re-arm it via the UI. | Default for safety. Recommended for any installation where unsupervised auto-restart is undesirable. |
| `preserve_state` | The pre-boot armed state is preserved. The generator can resume operation automatically after a power outage. | Only when your installation can safely auto-resume (proper ATS, weatherproofing, fuel/CO safety, operator awareness). |

Runtime GenSlave reconnects (when GenSlave drops out and reconnects during
normal operation) are handled by the heartbeat-driven sync — GenSlave reads
`armed` from every heartbeat and matches GenMaster's DB, with no separate
configuration needed.

### GenSlave on reboot (always the same)

Unlike GenMaster, GenSlave has no per-policy choice. On reboot it always:

1. Comes up with `_armed = False` and the relay physically OFF
2. Treats the first heartbeat from GenMaster as authoritative for both armed
   state and relay state — so within ~1 heartbeat cycle (~10s default) it
   ends up matching whatever GenMaster says
3. If GenMaster is in `fail_safe` and disarmed itself on boot, GenSlave stays
   disarmed. If GenMaster is in `preserve_state` and was armed, GenSlave
   re-arms via "self-heal" sync.

### Reconciliation Events

| Event | Severity | Description |
|-------|----------|-------------|
| `SYSTEM_BOOT_RESET` | WARNING/INFO | Logged on every boot. Now includes `boot_arming_policy` and `relay_disarmed_by_policy` so the log accurately reflects what happened. |
| `RECONCILIATION_MISMATCH` | WARNING | GenSlave relay ON but no active run in GenMaster |
| `boot_disarmed_failsafe` (notification) | WARNING | Sent to configured channels when `fail_safe` policy disarms the relay. Tells the operator they need to re-arm. |

### Database Fields Reset on Boot

```sql
-- Always reset
slave_connection_status = 'unknown'
missed_heartbeat_count = 0

-- Reset based on boot_arming_policy
slave_relay_armed = False        -- ONLY if policy = 'fail_safe' AND was armed pre-boot
manual_disarm_active = True      -- Set when fail_safe disarms (records operator-must-re-arm intent)

-- Reset if generator was running (regardless of policy)
generator_running = False
run_trigger = 'idle'
generator_start_time = NULL
current_run_id = NULL  -- After closing orphaned run
```

---

## State Machine Flow

The StateMachine class (`state_machine.py`) is the central controller for generator operations.

![State Machine](images/state_machine.png)

---

## Automation Arming System

The arming system is a safety layer that prevents automated actions during startup, maintenance, or testing. Automation is **disarmed by default** and must be explicitly armed by an operator.

![Arming System](images/arming.png)

### Arming Integration Points

1. **Victron Signal Handler** (`handle_victron_signal_change`)
   - Checks `automation_armed` before taking action
   - Logs signal changes regardless of arm state

2. **Start Generator** (`start_generator`)
   - `can_start_generator()` requires `automation_armed == true`
   - Returns clear error: "Cannot start - automation is not armed"

3. **Scheduler** (`_execute_scheduled_run`)
   - Checks `is_armed()` before executing
   - Logs skipped runs with reason

4. **Full Status** (`get_full_status`)
   - Includes `automation_armed` in system status response

---

## Webhook Event System

The webhook system sends notifications to external services (like n8n) for various system events.

![Webhook Events](images/webhooks.png)

---

## Database Schema Overview

PostgreSQL 16 with asyncpg driver for async operations.

![Database Schema](images/database_schema.png)

---

## Installation & Setup Flow

![Installation Flow](images/install_flow.png)

---

## Memory Budget (Raspberry Pi 5 - 8GB)

![Memory Budget](images/memory_budget.png)

---

## Port Reference

| Service      | Internal Port | External Access    | Notes              |
|--------------|---------------|--------------------|--------------------|
| Nginx        | 443           | Yes (HTTPS only)   | Main entry point   |
| FastAPI      | 8000          | No (internal only) | Backend API        |
| PostgreSQL   | 5432          | No (internal only) | Database           |
| Redis        | 6379          | No (internal only) | Cache              |
| Portainer    | 9000          | /portainer/ path   | Optional profile   |
| GenSlave API | 8001          | Tailscale only     | On Pi Zero 2W      |

---

## Security Layers

1. **Network Level**
   - Tailscale mesh VPN (WireGuard encryption)
   - UFW firewall rules
   - Docker network isolation

2. **Application Level**
   - Nginx rate limiting (API: 30r/s, Auth: 5r/m)
   - JWT authentication for API
   - API secret for GenSlave communication
   - Webhook secret for external services

3. **Transport Level**
   - HTTPS via Tailscale certs or Cloudflare
   - Nginx security headers (X-Frame-Options, X-XSS-Protection, etc.)

4. **Access Control**
   - Nginx geo module — IP allowlist gating the entire 443 interface (UI, API, websocket, health, Portainer); off-list clients receive HTTP 403
   - Tailscale ACLs (tag-based access)
   - Cloudflare Access (optional additional auth)

---

## Development/Testing Mode (LXC Containers)

GenMaster can run in LXC containers for testing without real GPIO hardware.

### Auto-Detection

- GenMaster automatically detects when NOT running on a Raspberry Pi
- Falls back to mock GPIO mode (checks `/proc/cpuinfo` for "Raspberry Pi")
- Development API becomes available at `/api/dev/*`
- Set `GENSLAVE_ENABLED=false` in `.env` for UI-only testing (disables heartbeat)

### Development API Endpoints

When in mock mode, these endpoints simulate Victron GPIO signals:

```
GET  /api/dev/status           - Development mode status
GET  /api/dev/gpio/state       - Current mock GPIO state
POST /api/dev/gpio/victron-signal  - Simulate Victron signal {"active": true/false}
POST /api/dev/gpio/toggle      - Toggle signal state
POST /api/dev/gpio/reset       - Reset to inactive
POST /api/dev/webhook/test     - Test webhook delivery
```

### Testing a Generator Cycle

```bash
# Start GenMaster (auto-detects LXC/dev environment)
docker compose up -d

# Simulate Victron requesting generator
curl -X POST http://localhost:8000/api/dev/gpio/victron-signal \
     -H "Content-Type: application/json" \
     -d '{"active": true}'

# Watch state transition: IDLE → STARTING → RUNNING

# Simulate Victron releasing generator
curl -X POST http://localhost:8000/api/dev/gpio/victron-signal \
     -H "Content-Type: application/json" \
     -d '{"active": false}'

# Watch state transition: RUNNING → STOPPING → IDLE
```

---

## Related Documentation

- [Generator Controls](GENERATOR.md) - Start, stop, and monitor operations
- [Scheduling](SCHEDULING.md) - Automated and exercise runs
- [GenSlave Setup](GENSLAVE.md) - Hardware and installation
- [Victron Integration](VICTRON.md) - GPIO signal monitoring
- [Tailscale VPN](TAILSCALE.md) - Secure device communication
- [Cloudflare Tunnel](CLOUDFLARE.md) - Remote access setup
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
