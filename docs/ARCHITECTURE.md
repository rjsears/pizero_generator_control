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
│             │   │   "command": "start"    │            │                            │
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
│             │   │     false               │            │                            │
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
│  │  Phase 1: System Preparation                                            │        │
│  │  ├── Detect if running in container (LXC/Docker)                        │        │
│  │  ├── Install base packages (docker.io, docker-compose, etc.)            │        │
│  │  ├── Check memory (minimum 4GB for Pi 5)                                │        │
│  │  └── Verify all required ports available                                │        │
│  │                                                                         │        │
│  │  Phase 2: Network Diagnostics                                           │        │
│  │  ├── check_dns() - Verify DNS resolution                                │        │
│  │  ├── get_local_ips() - Enumerate network interfaces                     │        │
│  │  ├── Test connectivity to required endpoints                            │        │
│  │  └── Detect Tailscale IP range (100.64.0.0/10)                          │        │
│  │                                                                         │        │
│  │  Phase 3: Interactive Configuration                                     │        │
│  │  ├── ask_tailscale() - Configure Tailscale (Y/n)                        │        │
│  │  ├── ask_cloudflare() - Configure Cloudflare Tunnel (y/N)               │        │
│  │  ├── ask_letsencrypt() - Configure Let's Encrypt (y/N)                  │        │
│  │  ├── ask_portainer() - Configure Portainer (Y/n)                        │        │
│  │  ├── Configure GenSlave connection URL                                  │        │
│  │  └── Configure webhook settings                                         │        │
│  │                                                                         │        │
│  │  Phase 4: File Generation                                               │        │
│  │  ├── Generate .env from template                                        │        │
│  │  ├── Generate docker-compose.override.yml if needed                     │        │
│  │  └── Copy application to /opt/genmaster                                 │        │
│  │                                                                         │        │
│  │  Phase 5: Docker Setup                                                  │        │
│  │  ├── Pull required images                                               │        │
│  │  ├── Build genmaster image                                              │        │
│  │  ├── Start containers with selected profiles                            │        │
│  │  │   docker compose --profile tailscale --profile portainer up -d       │        │
│  │  └── Wait for health checks                                             │        │
│  │                                                                         │        │
│  │  Phase 6: Post-Install                                                  │        │
│  │  ├── Run database migrations                                            │        │
│  │  ├── Create admin user if needed                                        │        │
│  │  ├── Display access URLs                                                │        │
│  │  └── Show next steps                                                    │        │
│  └─────────────────────────────────────────────────────────────────────────┘        │
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
