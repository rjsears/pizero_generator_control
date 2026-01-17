# GenMaster/GenSlave System Architecture

## Overview

The RPi Generator Control system is a distributed two-device architecture for automated generator management. It uses a master-slave pattern where GenMaster (Raspberry Pi 5) handles the web interface, business logic, and Victron integration, while GenSlave (Pi Zero 2W) controls the physical relay for generator start/stop.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    INTERNET                                         │
└─────────────────────────────────────────────────────────────────────────────────────┘
                    │                                              │
                    │ (Optional)                                   │
                    │ Cloudflare Tunnel                            │
                    ▼                                              │
          ┌─────────────────────┐                                  │
          │   Cloudflare Edge   │                                  │
          │  genmaster.domain   │                                  │
          └─────────────────────┘                                  │
                    │                                              │
                    ▼                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           TAILSCALE MESH NETWORK                                    │
│                        (Encrypted WireGuard Tunnels)                                │
│                              100.64.0.0/10                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌──────────────────────┐         ┌──────────────────────┐    ┌──────────────────┐  │
│  │      GenMaster       │◄───────►│       GenSlave       │    │    Your Phone    │  │
│  │   Raspberry Pi 5     │  HTTP   │    Pi Zero 2W        │    │   100.x.x.20     │  │
│  │   100.x.x.101:443    │  :8001  │    100.x.x.102       │    │                  │  │
│  │   8GB RAM, NVMe      │         │    512MB RAM         │    │                  │  │
│  └──────────────────────┘         └──────────────────────┘    └──────────────────┘  │
│            ▲                                │                                       │
│            │ GPIO 17 (input)                │ GPIO (output)                         │
│  ┌─────────┴─────────┐            ┌────────▼────────┐                               │
│  │  Victron Cerbo GX │            │ Generator Relay │                               │
│  │ (sends start/stop │            │ (Physical Start)│                               │
│  │  request signal)  │            └─────────────────┘                               │
│  └───────────────────┘                                                              │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## GenMaster Docker Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              GenMaster (Raspberry Pi 5)                             │
│                            8GB RAM / 128GB NVMe / ARM64                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                           Docker Compose Stack                              │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                             │    │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐   │    │
│  │  │    Nginx     │   │   FastAPI    │   │  PostgreSQL  │   │    Redis    │   │    │
│  │  │     :443     │──►│    :8000     │──►│    :5432     │   │    :6379    │   │    │
│  │  │              │   │  (internal)  │   │              │   │             │   │    │
│  │  │ Reverse Proxy│   │  + Vue.js    │   │   pg 16      │   │  Caching    │   │    │
│  │  │ SSL/Security │   │  Static      │   │   asyncpg    │   │  Sessions   │   │    │
│  │  └──────────────┘   └──────────────┘   └──────────────┘   └─────────────┘   │    │
│  │         │                  │                                                │    │
│  │         │                  │                                                │    │
│  │  ┌──────▼──────────────────▼─────────────────────────────────────────────┐  │    │
│  │  │                    genmaster-internal network                         │  │    │
│  │  └───────────────────────────────────────────────────────────────────────┘  │    │
│  │                                                                             │    │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │    │
│  │  │                    Optional Profile Services                           │ │    │
│  │  ├──────────────────┬──────────────────┬──────────────────────────────────┤ │    │
│  │  │    Tailscale     │   Cloudflared    │         Portainer                │ │    │
│  │  │ --profile        │ --profile        │     --profile portainer          │ │    │
│  │  │   tailscale      │   cloudflare     │         :9000                    │ │    │
│  │  │ (network: host)  │ (network: host)  │    /portainer/ path              │ │    │
│  │  └──────────────────┴──────────────────┴──────────────────────────────────┘ │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐   │
│  │                              Host System                                     │   │
│  ├──────────────────────────────────────────────────────────────────────────────┤   │
│  │  Victron Cerbo GX Relay ──────► GPIO 17 (Input - Generator Request Signal)   │   │
│  │                                 (Read via gpiozero + lgpio)                  │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Architecture

```
                                   EXTERNAL REQUEST
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              Cloudflare Tunnel (Optional)                           │
│                           DDoS Protection, SSL Termination                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    Nginx (:443)                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│   Request Classification (geo module):                                              │
│   ├── 127.0.0.1/32, ::1/128          → internal                                     │
│   ├── 10.0.0.0/8, 172.16.0.0/12      → internal (Docker)                            │
│   ├── 192.168.0.0/16                 → internal (LAN)                               │
│   ├── 100.64.0.0/10                  → internal (Tailscale CGNAT)                   │
│   └── default                        → external                                     │
│                                                                                     │
│   Route Handling:                                                                   │
│   ├── /health              → 200 "healthy" (no proxy)                               │
│   ├── /api/health          → FastAPI health check                                   │
│   ├── /api/auth/login      → FastAPI + strict rate limit (5r/m)                     │
│   ├── /api/*               → FastAPI + rate limit (30r/s)                           │
│   ├── /api/backup/download → FastAPI + extended timeout (600s)                      │
│   ├── /ws                  → FastAPI WebSocket (24h timeout)                        │
│   ├── /portainer/*         → Portainer :9000 (rewrite path)                         │
│   └── /*                   → FastAPI (Vue.js static files)                          │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
          ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
          │ FastAPI :8000   │  │ Portainer :9000 │  │  Static Assets  │
          │ API + WebSocket │  │ Docker Mgmt UI  │  │  1y cache       │
          └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Heartbeat System Architecture

The heartbeat system ensures reliable communication between GenMaster and GenSlave, with failsafe mechanisms.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              HEARTBEAT SYSTEM                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  GenMaster                                              GenSlave                    │
│  ─────────                                              ────────                    │
│                                                                                     │
│  ┌─────────────────────┐                    ┌─────────────────────┐                 │
│  │   HeartbeatService  │                    │   HeartbeatReceiver │                 │
│  │   (Background Task) │                    │   (FastAPI Endpoint)│                 │
│  └──────────┬──────────┘                    └──────────┬──────────┘                 │
│             │                                          │                            │
│             │  Every 5 seconds (configurable)          │                            │
│             │                                          │                            │
│             │   POST /api/heartbeat                    │                            │
│             │   ┌─────────────────────────┐            │                            │
│             │   │ {                       │            │                            │
│             ├──►│   "timestamp": 1234567, │───────────►│                            │
│             │   │   "generator_running":  │            │                            │
│             │   │     true/false,         │            │                            │
│             │   │   "armed": true/false,  │            │  ← Armed state synced      │
│             │   │   "command": "start"    │            │    from GenMaster          │
│             │   │     /"stop"/"none"      │            │                            │
│             │   │ }                       │            │                            │
│             │   └─────────────────────────┘            │                            │
│             │                                          │                            │
│             │   Response                               │                            │
│             │   ┌─────────────────────────┐            │                            │
│             │   │ {                       │            │                            │
│             │◄──│   "relay_state": true,  │◄───────────┤                            │
│             │   │   "uptime": 3600,       │            │                            │
│             │   │   "failsafe_active":    │            │                            │
│             │   │     false,              │            │                            │
│             │   │   "armed": true/false   │            │  ← GenSlave armed state    │
│             │   │ }                       │            │                            │
│             │   └─────────────────────────┘            │                            │
│             │                                          │                            │
│             ▼                                          ▼                            │
│  ┌─────────────────────┐                    ┌─────────────────────┐                 │
│  │   StateMachine      │                    │   FailsafeMonitor   │                 │
│  │   Updates:          │                    │   Triggers if:      │                 │
│  │   - slave_relay     │                    │   - No heartbeat    │                 │
│  │   - connection_stat │                    │     for 30 seconds  │                 │
│  │   - missed_count    │                    │   - Stops generator │                 │
│  └─────────────────────┘                    │   - Sends webhook   │                 │
│                                             └─────────────────────┘                 │
│                                                                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              FAILURE HANDLING                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  GenMaster Side:                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐                   │
│  │  missed_heartbeat_count >= heartbeat_failure_threshold (3)   │                   │
│  │         │                                                    │                   │
│  │         ▼                                                    │                   │
│  │  slave_connection_status = "disconnected"                    │                   │
│  │         │                                                    │                   │
│  │         ▼                                                    │                   │
│  │  - Log COMMUNICATION_LOST event                              │                   │
│  │  - Send webhook: communication.lost                          │                   │
│  │  - Block new generator starts                                │                   │
│  └──────────────────────────────────────────────────────────────┘                   │
│                                                                                     │
│  GenSlave Side (Independent Failsafe):                                              │
│  ┌──────────────────────────────────────────────────────────────┐                   │
│  │  No heartbeat received for > failsafe_timeout (30s)          │                   │
│  │         │                                                    │                   │
│  │         ▼                                                    │                   │
│  │  - Stop generator (relay OFF)                                │                   │
│  │  - Log locally                                               │                   │
│  │  - Attempt webhook to n8n (backup notification)              │                   │
│  │  - Continue monitoring for heartbeat restoration             │                   │
│  └──────────────────────────────────────────────────────────────┘                   │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Boot Sequence / Power Loss Recovery

Both GenMaster and GenSlave implement safety measures for power loss and reboot scenarios.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         POWER LOSS RECOVERY SEQUENCE                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                         GenSlave Boot Sequence                                │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                               │  │
│  │  1. systemd starts genslave.service                                           │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  2. relay.py imports automationhat                                            │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  3. RELAY SET TO OFF (line 37) ←── CRITICAL SAFETY: Hardware reset            │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  4. RelayService.__init__()                                                   │  │
│  │     - _armed = False ←── Always disarmed on boot                              │  │
│  │     - _mock_state = False                                                     │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  5. FailsafeMonitor starts                                                    │  │
│  │     - _last_heartbeat = None                                                  │  │
│  │     - Waits for heartbeats from GenMaster                                     │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  6. GenSlave READY (waiting for GenMaster heartbeat)                          │  │
│  │     - Armed state will sync from GenMaster via heartbeat                      │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                        GenMaster Boot Sequence                                │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │                                                                               │  │
│  │  1. Docker starts containers (PostgreSQL, Redis, GenMaster, Nginx)            │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  2. StateMachine.initialize() loads from database                             │  │
│  │         │                                                                     │  │
│  │         ├──► Log pre-boot state for debugging                                 │  │
│  │         │                                                                     │  │
│  │         ├──► RESET automation_armed = False ←── ALWAYS disarm on boot         │  │
│  │         │                                                                     │  │
│  │         ├──► RESET slave_connection_status = "unknown"                        │  │
│  │         │                                                                     │  │
│  │         ├──► If generator_running was True:                                   │  │
│  │         │      - Set generator_running = False                                │  │
│  │         │      - Close orphaned run record (stop_reason = "power_loss")       │  │
│  │         │      - Log WARNING                                                  │  │
│  │         │                                                                     │  │
│  │         └──► Log SYSTEM_BOOT_RESET event                                      │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  3. Services start (GPIO Monitor, Heartbeat, Scheduler)                       │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  4. Reconciliation with GenSlave                                              │  │
│  │         │                                                                     │  │
│  │         ├──► Query GenSlave relay state: GET /api/relay/state                 │  │
│  │         │                                                                     │  │
│  │         ├──► If slave unreachable:                                            │  │
│  │         │      - Log warning, continue (slave may boot later)                 │  │
│  │         │                                                                     │  │
│  │         ├──► If relay ON but generator_running = False:                       │  │
│  │         │      - Log RECONCILIATION_MISMATCH                                  │  │
│  │         │      - WARNING: Manual intervention may be required                 │  │
│  │         │                                                                     │  │
│  │         └──► Update slave_connection_status = "connected"                     │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  5. Log SYSTEM_BOOT event                                                     │  │
│  │         │                                                                     │  │
│  │         ▼                                                                     │  │
│  │  6. GenMaster READY                                                           │  │
│  │     - Heartbeats start (sync armed state to GenSlave)                         │  │
│  │     - Victron signals IGNORED until armed                                     │  │
│  │     - Scheduled runs SKIPPED until armed                                      │  │
│  │                                                                               │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              POST-BOOT STATE                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  After any power loss or reboot:                                                    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  Component          │ State              │ Notes                            │    │
│  │  ──────────────────────────────────────────────────────────────────────────│    │
│  │  GenMaster armed    │ False              │ ALWAYS reset on boot             │    │
│  │  GenSlave armed     │ False (synced)     │ Synced from GenMaster            │    │
│  │  GenSlave relay     │ OFF                │ Hardware safety reset            │    │
│  │  generator_running  │ False              │ Reset if was True                │    │
│  │  slave_connection   │ "unknown"→"connected" │ Updated by heartbeat          │    │
│  │  Victron response   │ DISABLED           │ Until operator arms              │    │
│  │  Scheduled runs     │ DISABLED           │ Until operator arms              │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  OPERATOR ACTION REQUIRED:                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │  1. Verify GenSlave connection in web UI (should show "connected")          │    │
│  │  2. Review system status and any warning messages                           │    │
│  │  3. Click "Arm Automation" or POST /api/system/arm                          │    │
│  │  4. System now responds to Victron signals and schedules                    │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Reconciliation Events

| Event | Severity | Description |
|-------|----------|-------------|
| `SYSTEM_BOOT_RESET` | WARNING/INFO | Logged on every boot with pre-boot state |
| `RECONCILIATION_MISMATCH` | WARNING | GenSlave relay ON but no active run in GenMaster |

### Database Fields Reset on Boot

```sql
-- Always reset
automation_armed = False
automation_armed_at = NULL
automation_armed_by = NULL
slave_connection_status = 'unknown'
missed_heartbeat_count = 0

-- Reset if generator was running
generator_running = False
run_trigger = 'idle'
generator_start_time = NULL
current_run_id = NULL  -- After closing orphaned run
```

---

## State Machine Flow

The StateMachine class (`state_machine.py`) is the central controller for generator operations.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              STATE MACHINE DIAGRAM                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│                              ┌─────────────────┐                                    │
│                              │      IDLE       │                                    │
│                              │generator_running│                                    │
│                              │   = false       │                                    │
│                              └────────┬────────┘                                    │
│                                       │                                             │
│         ┌─────────────────────────────┼─────────────────────────────┐               │
│         │                             │                             │               │
│         ▼                             ▼                             ▼               │
│  ┌─────────────┐             ┌─────────────┐             ┌─────────────┐            │
│  │   VICTRON   │             │   MANUAL    │             │  SCHEDULED  │            │
│  │   TRIGGER   │             │   START     │             │    START    │            │
│  │             │             │             │             │             │            │
│  │ GPIO 17 HIGH│             │ API request │             │ APScheduler │            │
│  └──────┬──────┘             └──────┬──────┘             └──────┬──────┘            │
│         │                           │                           │                   │
│         └───────────────────────────┼───────────────────────────┘                   │
│                                     │                                               │
│                                     ▼                                               │
│                    ┌─────────────────────────────────┐                              │
│                    │         VALIDATION              │                              │
│                    │  can_start_generator() check:   │                              │
│                    │  - automation_armed             │                              │
│                    │  - !generator_running           │                              │
│                    │  - !override(force_stop)        │                              │
│                    │  - slave_connected              │                              │
│                    └─────────────┬───────────────────┘                              │
│                                  │                                                  │
│                         ┌────────┴────────┐                                         │
│                         │                 │                                         │
│                    [PASS]            [FAIL]                                         │
│                         │                 │                                         │
│                         ▼                 ▼                                         │
│              ┌─────────────────┐  ┌─────────────────┐                               │
│              │    STARTING     │  │     ERROR       │                               │
│              │                 │  │ Raise ValueError│                               │
│              │ 1. Create Run   │  └─────────────────┘                               │
│              │ 2. Update State │                                                    │
│              │ 3. Send command │                                                    │
│              │    to GenSlave  │                                                    │
│              │ 4. Log event    │                                                    │
│              │ 5. Send webhook │                                                    │
│              └────────┬────────┘                                                    │
│                       │                                                             │
│                       ▼                                                             │
│              ┌─────────────────┐                                                    │
│              │     RUNNING     │                                                    │
│              │generator_running│                                                    │
│              │   = true        │                                                    │
│              │ run_trigger =   │                                                    │
│              │   victron/manual│                                                    │
│              │   /scheduled    │                                                    │
│              └────────┬────────┘                                                    │
│                       │                                                             │
│         ┌─────────────┼─────────────┬─────────────┬─────────────┐                   │
│         │             │             │             │             │                   │
│         ▼             ▼             ▼             ▼             ▼                   │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐              │
│  │  VICTRON  │ │  MANUAL   │ │ SCHEDULED │ │ COMM_LOSS │ │ OVERRIDE  │              │
│  │   STOP    │ │   STOP    │ │    END    │ │  FAILSAFE │ │ force_stop│              │
│  │           │ │           │ │           │ │           │ │           │              │
│  │GPIO 17 LOW│ │API request│ │Duration   │ │Heartbeat  │ │User toggle│              │
│  │(if victron│ │           │ │expired    │ │timeout    │ │           │              │
│  │ triggered)│ │           │ │           │ │           │ │           │              │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘              │
│        │             │             │             │             │                    │
│        └─────────────┴─────────────┴─────────────┴─────────────┘                    │
│                                    │                                                │
│                                    ▼                                                │
│                       ┌─────────────────────┐                                       │
│                       │      STOPPING       │                                       │
│                       │                     │                                       │
│                       │ 1. Complete Run     │                                       │
│                       │ 2. Update State     │                                       │
│                       │ 3. Send command     │                                       │
│                       │    to GenSlave      │                                       │
│                       │ 4. Log event        │                                       │
│                       │ 5. Send webhook     │                                       │
│                       └──────────┬──────────┘                                       │
│                                  │                                                  │
│                                  ▼                                                  │
│                       ┌─────────────────┐                                           │
│                       │      IDLE       │                                           │
│                       │ (back to start) │                                           │
│                       └─────────────────┘                                           │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Automation Arming System

The arming system is a safety layer that prevents automated actions during startup, maintenance, or testing. Automation is **disarmed by default** and must be explicitly armed by an operator.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           AUTOMATION ARMING FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                            SYSTEM BOOT                                      │    │
│  │                                                                             │    │
│  │  1. GenMaster starts → automation_armed = false                             │    │
│  │  2. GenSlave starts → waiting for arm command                               │    │
│  │  3. Heartbeat establishes → slave_connection = "connected"                  │    │
│  │  4. Operator reviews status in web UI                                       │    │
│  │  5. Operator clicks "Arm Automation"                                        │    │
│  │  6. System is now active                                                    │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         ARMED vs DISARMED BEHAVIOR                          │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                             │    │
│  │  Event                    │ DISARMED                │ ARMED                 │    │
│  │  ─────────────────────────┼─────────────────────────┼─────────────────────  │    │
│  │  Victron signal HIGH      │ Logged, no action       │ Start generator       │    │
│  │  Victron signal LOW       │ Logged, no action       │ Stop generator        │    │
│  │  Scheduled run triggers   │ Skipped, warning logged │ Execute normally      │    │
│  │  Manual start request     │ REJECTED with error     │ Execute if valid      │    │
│  │  Manual stop request      │ Execute (safety)        │ Execute               │    │
│  │  Heartbeat failures       │ Log only                │ Full failsafe logic   │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                           ARM/DISARM API                                    │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                             │    │
│  │  GET  /api/system/arm     →  Get current arm status                         │    │
│  │                               {                                             │    │
│  │                                 "armed": false,                             │    │
│  │                                 "armed_at": null,                           │    │
│  │                                 "armed_by": null,                           │    │
│  │                                 "slave_connection": "connected"             │    │
│  │                               }                                             │    │
│  │                                                                             │    │
│  │  POST /api/system/arm     →  Arm automation                                 │    │
│  │       Body: {"source": "ui"}                                                │    │
│  │       Response: {                                                           │    │
│  │         "success": true,                                                    │    │
│  │         "armed": true,                                                      │    │
│  │         "message": "Automation armed successfully",                         │    │
│  │         "armed_at": 1736985600,                                             │    │
│  │         "warnings": []  // Or ["GenSlave is disconnected..."]               │    │
│  │       }                                                                     │    │
│  │                                                                             │    │
│  │  POST /api/system/disarm  →  Disarm automation                              │    │
│  │       Body: {"source": "ui"}                                                │    │
│  │       Response: {                                                           │    │
│  │         "success": true,                                                    │    │
│  │         "armed": false,                                                     │    │
│  │         "message": "Automation disarmed",                                   │    │
│  │         "warnings": ["Generator is running - will NOT be stopped..."]       │    │
│  │       }                                                                     │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         ARMING STATE TRANSITIONS                            │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                             │    │
│  │                    ┌───────────────────┐                                    │    │
│  │                    │     DISARMED      │◄──── System Boot                   │    │
│  │                    │  (Default State)  │◄──── Power Recovery                │    │
│  │                    └─────────┬─────────┘                                    │    │
│  │                              │                                              │    │
│  │                     POST /api/system/arm                                    │    │
│  │                              │                                              │    │
│  │                              ▼                                              │    │
│  │                    ┌───────────────────┐                                    │    │
│  │                    │      ARMED        │                                    │    │
│  │                    │  (Active State)   │                                    │    │
│  │                    │                   │                                    │    │
│  │                    │  - Victron active │                                    │    │
│  │                    │  - Schedules run  │                                    │    │
│  │                    │  - Manual allowed │                                    │    │
│  │                    └─────────┬─────────┘                                    │    │
│  │                              │                                              │    │
│  │                    POST /api/system/disarm                                  │    │
│  │                              │                                              │    │
│  │                              ▼                                              │    │
│  │                    ┌───────────────────┐                                    │    │
│  │                    │     DISARMED      │                                    │    │
│  │                    │  (Safe State)     │                                    │    │
│  │                    │                   │                                    │    │
│  │                    │  NOTE: Generator  │                                    │    │
│  │                    │  is NOT stopped   │                                    │    │
│  │                    │  automatically!   │                                    │    │
│  │                    └───────────────────┘                                    │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         DATABASE FIELDS                                     │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                             │    │
│  │  system_state table:                                                        │    │
│  │  ├── automation_armed       BOOLEAN DEFAULT false                           │    │
│  │  ├── automation_armed_at    INTEGER (unix timestamp, nullable)              │    │
│  │  └── automation_armed_by    VARCHAR(50) (nullable)                          │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                         WEBHOOK EVENTS                                      │    │
│  ├─────────────────────────────────────────────────────────────────────────────┤    │
│  │                                                                             │    │
│  │  automation.armed      - Sent when system is armed                          │    │
│  │                          {"source": "ui", "armed_at": 1736985600}           │    │
│  │                                                                             │    │
│  │  automation.disarmed   - Sent when system is disarmed                       │    │
│  │                          {"source": "api", "generator_running": true}       │    │
│  │                                                                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

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

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              WEBHOOK EVENT TYPES                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Generator Events:                                                                  │
│  ├── generator.started.victron    - Started by Victron signal                       │
│  ├── generator.started.manual     - Started manually via UI/API                     │
│  ├── generator.started.scheduled  - Started by schedule                             │
│  ├── generator.stopped.victron    - Stopped by Victron signal                       │
│  ├── generator.stopped.manual     - Stopped manually                                │
│  ├── generator.stopped.scheduled_end - Duration expired                             │
│  ├── generator.stopped.override   - Stopped by force_stop override                  │
│  ├── generator.stopped.comm_loss  - Stopped by failsafe                             │
│  └── generator.stopped.error      - Stopped due to error                            │
│                                                                                     │
│  Communication Events:                                                              │
│  ├── communication.lost           - GenSlave connection lost                        │
│  └── communication.restored       - GenSlave connection restored                    │
│                                                                                     │
│  Override Events:                                                                   │
│  ├── override.enabled             - Manual override activated                       │
│  └── override.disabled            - Manual override deactivated                     │
│                                                                                     │
│  Arming Events:                                                                     │
│  ├── automation.armed             - Automation system armed                         │
│  └── automation.disarmed          - Automation system disarmed                      │
│                                                                                     │
│  System Events:                                                                     │
│  ├── system.startup               - GenMaster started                               │
│  └── system.error                 - Critical system error                           │
│                                                                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                              WEBHOOK DELIVERY                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌────────────────────┐      POST Request       ┌────────────────────┐              │
│  │    StateMachine    │ ───────────────────────►│  External Webhook  │              │
│  │ await _send_webhook│                         │  (Remote URL)      │              │
│  │    (event, data)   │                         │                    │              │
│  └────────────────────┘                         └────────────────────┘              │
│                                                                                     │
│  Example webhook URL (configured in Settings):                                      │
│  https://example.com/webhook/abc123-def456-ghi789                                   │
│                                                                                     │
│  Payload Structure:                                                                 │
│  {                                                                                  │
│    "event": "generator.started.victron",                                            │
│    "timestamp": 1736985600,                                                         │
│    "data": {                                                                        │
│      "run_id": 42,                                                                  │
│      "trigger": "victron"                                                           │
│    },                                                                               │
│    "source": "genmaster",                                                           │
│    "secret": "webhook-secret"  // For verification                                  │
│  }                                                                                  │
│                                                                                     │
│  Settings UI allows toggling individual event types on/off.                         │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Overview

PostgreSQL 16 with asyncpg driver for async operations.

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              DATABASE SCHEMA                                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              system_state                                     │  │
│  │                          (Singleton - 1 row)                                  │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │  id                         SERIAL PRIMARY KEY                                │  │
│  │  automation_armed           BOOLEAN DEFAULT false                             │  │
│  │  automation_armed_at        INTEGER (unix timestamp, nullable)                │  │
│  │  automation_armed_by        VARCHAR(50) (nullable)                            │  │
│  │  generator_running          BOOLEAN DEFAULT false                             │  │
│  │  generator_start_time       INTEGER (unix timestamp)                          │  │
│  │  current_run_id             INTEGER → generator_runs.id                       │  │
│  │  run_trigger                VARCHAR(20) 'idle'|'victron'|'manual'|'scheduled' │  │
│  │  victron_signal_state       BOOLEAN DEFAULT false                             │  │
│  │  victron_last_change        INTEGER (unix timestamp)                          │  │
│  │  override_enabled           BOOLEAN DEFAULT false                             │  │
│  │  override_type              VARCHAR(20) 'none'|'force_run'|'force_stop'       │  │
│  │  slave_connection_status    VARCHAR(20) 'unknown'|'connected'|'disconnected'  │  │
│  │  slave_relay_state          BOOLEAN (actual relay state from GenSlave)        │  │
│  │  last_heartbeat_sent        INTEGER (unix timestamp)                          │  │
│  │  last_heartbeat_received    INTEGER (unix timestamp)                          │  │
│  │  missed_heartbeat_count     INTEGER DEFAULT 0                                 │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              config                                           │  │
│  │                          (Singleton - 1 row)                                  │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │  id                         SERIAL PRIMARY KEY                                │  │
│  │  heartbeat_interval_seconds INTEGER DEFAULT 5                                 │  │
│  │  heartbeat_failure_threshold INTEGER DEFAULT 3                                │  │
│  │  failsafe_timeout_seconds   INTEGER DEFAULT 30                                │  │
│  │  webhook_enabled            BOOLEAN DEFAULT true                              │  │
│  │  webhook_url                VARCHAR(255)                                      │  │
│  │  webhook_secret             VARCHAR(255)                                      │  │
│  │  webhook_events             JSONB (enabled event types)                       │  │
│  │  slave_api_url              VARCHAR(255) DEFAULT 'http://genslave:8001'       │  │
│  │  slave_api_secret           VARCHAR(255)                                      │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              generator_runs                                   │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │  id                         SERIAL PRIMARY KEY                                │  │
│  │  start_time                 INTEGER NOT NULL (unix timestamp)                 │  │
│  │  end_time                   INTEGER (unix timestamp)                          │  │
│  │  duration_seconds           INTEGER (calculated)                              │  │
│  │  trigger_type               VARCHAR(20) 'victron'|'manual'|'scheduled'        │  │
│  │  stop_reason                VARCHAR(50)                                       │  │
│  │  scheduled_run_id           INTEGER → scheduled_runs.id                       │  │
│  │  notes                      TEXT                                              │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              scheduled_runs                                   │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │  id                         SERIAL PRIMARY KEY                                │  │
│  │  name                       VARCHAR(100)                                      │  │
│  │  cron_expression            VARCHAR(100)  -- APScheduler cron syntax          │  │
│  │  duration_minutes           INTEGER                                           │  │
│  │  enabled                    BOOLEAN DEFAULT true                              │  │
│  │  last_run                   INTEGER (unix timestamp)                          │  │
│  │  next_run                   INTEGER (unix timestamp)                          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              event_log                                        │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │  id                         SERIAL PRIMARY KEY                                │  │
│  │  timestamp                  INTEGER NOT NULL (unix timestamp)                 │  │
│  │  event_type                 VARCHAR(50) NOT NULL                              │  │
│  │  severity                   VARCHAR(20) 'INFO'|'WARNING'|'ERROR'              │  │
│  │  data                       JSONB                                             │  │
│  │  INDEX on (timestamp, event_type)                                             │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌───────────────────────────────────────────────────────────────────────────────┐  │
│  │                              users                                            │  │
│  ├───────────────────────────────────────────────────────────────────────────────┤  │
│  │  id                         SERIAL PRIMARY KEY                                │  │
│  │  username                   VARCHAR(50) UNIQUE NOT NULL                       │  │
│  │  password_hash              VARCHAR(255) NOT NULL                             │  │
│  │  is_admin                   BOOLEAN DEFAULT false                             │  │
│  │  created_at                 INTEGER (unix timestamp)                          │  │
│  │  last_login                 INTEGER (unix timestamp)                          │  │
│  └───────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Installation & Setup Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           INSTALLATION FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Option 1: Quick Install (curl)                                                     │
│  ─────────────────────────────                                                      │
│                                                                                     │
│  curl -fsSL https://raw.githubusercontent.com/.../install.sh | sudo bash            │
│                                                                                     │
│         │                                                                           │
│         ▼                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │                          install.sh                                     │        │
│  │  1. Check root permissions                                              │        │
│  │  2. Detect OS (Debian/Ubuntu/Raspbian)                                  │        │
│  │  3. Check architecture (arm64/armhf/x86_64)                             │        │
│  │  4. Verify internet connectivity                                        │        │
│  │  5. Install git, curl, wget, ca-certificates                            │        │
│  │  6. Clone repository to /tmp/genmaster-install                          │        │
│  │  7. Execute setup.sh                                                    │        │
│  │  8. Cleanup temp files                                                  │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│                                                                                     │
│         │                                                                           │
│         ▼                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐        │
│  │                          setup.sh                                       │        │
│  │                                                                         │        │
│  │  Command Line Options:                                                  │        │
│  │  ├── ./setup.sh              - Interactive setup                        │        │
│  │  ├── ./setup.sh --config     - Use pre-configuration file               │        │
│  │  ├── ./setup.sh --genslave   - Validate GenSlave connection             │        │
│  │  ├── ./setup.sh --genslaveip - Update GenSlave URL/IP                   │        │
│  │  └── ./setup.sh --help       - Show help                                │        │
│  │                                                                         │        │
│  │  Phase 1: Environment Detection                                         │        │
│  │  ├── LXC Warning - Show Proxmox apparmor config if LXC detected         │        │
│  │  ├── Hardware Detection (Raspberry Pi vs LXC/x86)                       │        │
│  │  ├── Auto-set MOCK_GPIO_MODE=true if not on Pi                          │        │
│  │  └── Check for resume from previous incomplete install                  │        │
│  │                                                                         │        │
│  │  Phase 2: System Preparation                                            │        │
│  │  ├── Detect OS (Debian/Ubuntu/RHEL/Arch/Alpine/SUSE)                    │        │
│  │  ├── Install utilities (curl, git, openssl, jq, tmux)                   │        │
│  │  ├── Install Docker with platform detection (macOS/WSL/Linux)           │        │
│  │  └── Enable and start Docker daemon                                     │        │
│  │                                                                         │        │
│  │  Phase 3: System Requirements Check                                     │        │
│  │  ├── Memory check (GB format with fallback to MB)                       │        │
│  │  ├── Disk space check (GB format)                                       │        │
│  │  ├── Port 443 availability                                              │        │
│  │  ├── OpenSSL and Curl availability                                      │        │
│  │  ├── Network connectivity (ping 8.8.8.8)                                │        │
│  │  └── Docker Hub connectivity test                                       │        │
│  │                                                                         │        │
│  │  Phase 4: Interactive Configuration                                     │        │
│  │  ├── Domain Configuration                                               │        │
│  │  │   ├── DNS resolution test                                            │        │
│  │  │   ├── IP matching validation                                         │        │
│  │  │   └── Ping connectivity test                                         │        │
│  │  ├── Database Configuration (auto-generate secure password)             │        │
│  │  ├── Timezone Configuration (default: America/Phoenix)                  │        │
│  │  │   └── Option to sync host timezone                                   │        │
│  │  ├── GenSlave Configuration                                             │        │
│  │  │   ├── URL format validation                                          │        │
│  │  │   ├── API secret generation                                          │        │
│  │  │   └── Optional connection validation (DNS/ping/port/health)          │        │
│  │  ├── Webhook Configuration                                              │        │
│  │  └── Optional Services (Tailscale/Cloudflare/Portainer)                 │        │
│  │                                                                         │        │
│  │  Phase 5: File Generation                                               │        │
│  │  ├── Generate .env with all configuration                               │        │
│  │  ├── Generate docker-compose.yml                                        │        │
│  │  ├── Generate nginx.conf with SSL                                       │        │
│  │  └── Generate self-signed SSL certificates                              │        │
│  │                                                                         │        │
│  │  Phase 6: Deployment                                                    │        │
│  │  ├── Pull Docker images                                                 │        │
│  │  ├── Start containers with selected profiles                            │        │
│  │  ├── Wait for health checks                                             │        │
│  │  ├── Display configuration summary                                      │        │
│  │  └── Show auto-generated credentials                                    │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
│                                                                                     │
│  Post-Install Commands:                                                             │
│  ├── ./setup.sh --genslave     - Validate GenSlave after it's set up               │
│  └── ./setup.sh --genslaveip   - Update GenSlave IP if it changes                  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Memory Budget (Raspberry Pi 5 - 8GB)

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY ALLOCATION                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Component                    Memory Usage    Notes                                 │
│  ─────────────────────────────────────────────────────────────────────────────────  │
│  Raspberry Pi OS              ~200 MB         Base system                           │
│  Docker Engine                ~100 MB         Container runtime                     │
│  PostgreSQL 16                ~100-200 MB     Database (shared_buffers: 128MB)      │
│  Redis                        ~50 MB          Caching layer                         │
│  Nginx                        ~20 MB          Reverse proxy                         │
│  FastAPI + Uvicorn            ~100-150 MB     Python application                    │
│  Vue.js Static                ~10 MB          Served by FastAPI                     │
│  Tailscale (optional)         ~50-75 MB       VPN daemon                            │
│  Cloudflared (optional)       ~75-100 MB      Tunnel daemon                         │
│  Portainer (optional)         ~100-150 MB     Docker management UI                  │
│  ─────────────────────────────────────────────────────────────────────────────────  │
│  Base Stack Total             ~580 MB                                               │
│  With All Options             ~900 MB                                               │
│  Available for System         ~7.1 GB         Plenty of headroom                    │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

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
   - Nginx geo module (internal vs external classification)
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

See [LXC-TESTING.md](./LXC-TESTING.md) for complete setup instructions.

---

## Related Documentation

- [01-project-overview.md](./agents/01-project-overview.md) - High-level project overview
- [LXC-TESTING.md](./LXC-TESTING.md) - LXC container testing guide
- [03-genmaster-backend.md](./agents/03-genmaster-backend.md) - Backend implementation details
- [05-genslave-backend.md](./agents/05-genslave-backend.md) - GenSlave implementation
- [06-docker-infrastructure.md](./agents/06-docker-infrastructure.md) - Docker configuration
- [07-networking.md](./agents/07-networking.md) - Tailscale and Cloudflare setup
- [08-setup-scripts.md](./agents/08-setup-scripts.md) - Installation automation
