# Agent Handoff: Project Structure & Conventions

## Purpose
This document establishes the foundational project structure, coding conventions, and shared patterns that ALL agents must follow when building components of the PiZero Generator Control system.

---

## Project Overview

**System**: Wireless generator control using two Raspberry Pi devices
- **GenMaster** (Raspberry Pi 5 8GB + NVMe): Monitors Victron Cerbo GX relay signal, hosts web interface, manages state - Docker deployment with PostgreSQL
- **GenSlave** (Raspberry Pi Zero 2W): Controls generator relay via Automation Hat Mini, responds to GenMaster commands - Native Python deployment with SQLite

**Primary Goals**:
1. Reliability - System must work consistently without manual intervention
2. State persistence - Survive reboots, power outages, and network interruptions
3. Minimal SSD wear - Database-centric design with reduced disk writes
4. Security - API authentication, Tailscale network isolation

---

## Complete File Structure

```
pizero_generator_control/
├── docs/
│   ├── agents/                      # Agent handoff documentation
│   │   ├── 01-project-structure.md  # This document
│   │   ├── 02-database-schema.md    # Database design
│   │   ├── 03-genmaster-backend.md  # GenMaster API
│   │   ├── 04-genmaster-frontend.md # Vue.js frontend
│   │   ├── 05-genslave-backend.md   # GenSlave API
│   │   ├── 06-docker-infrastructure.md
│   │   ├── 07-networking.md
│   │   └── 08-setup-scripts.md
│   └── PROJECT_TRACKER.md           # Master task tracking
│
├── genmaster/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI application entry point
│   │   ├── config.py                # Pydantic settings configuration
│   │   ├── database.py              # SQLAlchemy engine & session
│   │   ├── dependencies.py          # FastAPI dependency injection
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── __init__.py          # Export all models
│   │   │   ├── base.py              # Base model class
│   │   │   ├── system_state.py      # Generator state tracking
│   │   │   ├── config.py            # System configuration
│   │   │   ├── generator_runs.py    # Run history
│   │   │   ├── scheduled_runs.py    # Scheduled tasks
│   │   │   └── event_log.py         # Event logging
│   │   │
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── generator.py         # Generator control schemas
│   │   │   ├── health.py            # Health check schemas
│   │   │   ├── system.py            # System info schemas
│   │   │   ├── schedule.py          # Scheduling schemas
│   │   │   ├── config.py            # Configuration schemas
│   │   │   └── webhook.py           # Webhook payload schemas
│   │   │
│   │   ├── routers/                 # FastAPI route handlers
│   │   │   ├── __init__.py          # Include all routers
│   │   │   ├── generator.py         # /api/generator/* endpoints
│   │   │   ├── health.py            # /api/health/* endpoints
│   │   │   ├── system.py            # /api/system/* endpoints
│   │   │   ├── schedule.py          # /api/schedule/* endpoints
│   │   │   ├── config.py            # /api/config/* endpoints
│   │   │   ├── backup.py            # /api/backup/* endpoints
│   │   │   └── override.py          # /api/override/* endpoints
│   │   │
│   │   ├── services/                # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── gpio_monitor.py      # Victron GPIO17 signal monitoring
│   │   │   ├── heartbeat.py         # GenSlave heartbeat management
│   │   │   ├── state_machine.py     # Generator state transitions
│   │   │   ├── webhook.py           # Notification dispatch
│   │   │   ├── scheduler.py         # APScheduler wrapper
│   │   │   ├── slave_client.py      # HTTP client for GenSlave API
│   │   │   └── backup.py            # Database backup service
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── system_info.py       # CPU, RAM, Temp, Disk utilities
│   │       ├── logging.py           # Structured logging to database
│   │       └── auth.py              # API key validation
│   │
│   ├── frontend/                    # Vue.js application
│   │   ├── src/
│   │   │   ├── main.js              # Vue app entry point
│   │   │   ├── App.vue              # Root component
│   │   │   ├── api/                 # API client modules
│   │   │   │   ├── index.js         # Axios instance & interceptors
│   │   │   │   ├── generator.js     # Generator API calls
│   │   │   │   ├── health.js        # Health API calls
│   │   │   │   ├── system.js        # System API calls
│   │   │   │   └── schedule.js      # Schedule API calls
│   │   │   ├── components/          # Reusable Vue components
│   │   │   │   ├── StatusCard.vue
│   │   │   │   ├── HealthGauge.vue
│   │   │   │   ├── RuntimeChart.vue
│   │   │   │   ├── ScheduleTable.vue
│   │   │   │   ├── ConfirmDialog.vue
│   │   │   │   └── ToastNotification.vue
│   │   │   ├── views/               # Page-level components
│   │   │   │   ├── Dashboard.vue    # Main dashboard
│   │   │   │   ├── Schedule.vue     # Schedule management
│   │   │   │   ├── History.vue      # Run history
│   │   │   │   └── Settings.vue     # Configuration
│   │   │   ├── stores/              # Pinia state management
│   │   │   │   ├── index.js
│   │   │   │   ├── generator.js     # Generator state store
│   │   │   │   └── system.js        # System state store
│   │   │   └── assets/
│   │   │       └── styles/
│   │   │           └── main.css     # Tailwind imports
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── vite.config.js
│   │   ├── tailwind.config.js
│   │   └── postcss.config.js
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # Pytest fixtures
│   │   ├── test_api/                # API endpoint tests
│   │   ├── test_services/           # Service layer tests
│   │   └── test_models/             # Model tests
│   │
│   ├── alembic/                     # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml  # Development overrides
│   ├── nginx.conf
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── genslave/                        # Native Python deployment (no Docker)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI application entry point
│   │   ├── config.py                # Pydantic settings
│   │   ├── database.py              # SQLite database setup
│   │   ├── dependencies.py          # FastAPI dependencies
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── system_state.py      # Relay state tracking
│   │   │   └── config.py            # Configuration mirror
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── relay.py             # Relay control schemas
│   │   │   ├── heartbeat.py         # Heartbeat schemas
│   │   │   └── system.py            # System info schemas
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── relay.py             # /api/relay/* endpoints
│   │   │   ├── heartbeat.py         # /api/heartbeat endpoint
│   │   │   ├── health.py            # /api/health endpoint
│   │   │   ├── system.py            # /api/system endpoint
│   │   │   └── config.py            # /api/config endpoint
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── relay_control.py     # Automation Hat Mini relay
│   │   │   ├── lcd_display.py       # ST7735 LCD management
│   │   │   ├── heartbeat_monitor.py # GenMaster heartbeat tracking
│   │   │   ├── failsafe.py          # Auto-shutdown on comm loss
│   │   │   └── webhook.py           # Direct webhook (comm loss only)
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── system_info.py
│   │       ├── logging.py
│   │       └── auth.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── ...
│   │
│   ├── data/                        # SQLite database directory
│   │   └── genslave.db              # SQLite database file
│   │
│   ├── setup.sh                     # Native installation script
│   ├── genslave.service             # systemd service file
│   ├── requirements.txt
│   └── .env.example
│
├── shared/                          # Shared code (optional)
│   ├── __init__.py
│   ├── constants.py                 # Shared constants
│   └── webhook_schemas.py           # Webhook payload definitions
│
├── scripts/
│   ├── backup.sh                    # Database backup script
│   ├── health-check.sh              # System health monitoring
│   └── dev-setup.sh                 # Development environment setup
│
├── config/
│   ├── tailscale/
│   │   └── .gitkeep
│   └── cloudflare/
│       └── .gitkeep
│
├── setup.sh                         # Main installation script
├── generator_project_outline.md     # Project outline (reference)
├── instructions.md                  # Project instructions
└── README.md
```

---

## Coding Conventions

### Python (Backend)

**Version**: Python 3.11+

**Style Guide**:
- PEP 8 compliant
- Line length: 100 characters max
- Use type hints everywhere
- Docstrings for public functions (Google style)

**Naming Conventions**:
```python
# Variables and functions: snake_case
generator_state = "running"
def get_system_status():
    pass

# Classes: PascalCase
class GeneratorState:
    pass

# Constants: UPPER_SNAKE_CASE
HEARTBEAT_INTERVAL_SECONDS = 60
MAX_RETRY_ATTEMPTS = 3

# Private methods/variables: leading underscore
def _internal_helper():
    pass
_cached_value = None
```

**Import Order**:
```python
# 1. Standard library
import os
import asyncio
from datetime import datetime
from typing import Optional

# 2. Third-party packages
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import httpx

# 3. Local imports
from app.config import settings
from app.database import get_db
from app.models import SystemState
```

**Async Pattern**:
```python
# Use async for I/O operations
async def fetch_slave_status() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.slave_api_url}/api/status")
        return response.json()

# Use sync for CPU-bound or simple operations
def calculate_runtime(start_time: int) -> int:
    return int(time.time()) - start_time
```

### TypeScript/JavaScript (Frontend)

**Version**: Node 18+, Vue 3 with Composition API

**Style Guide**:
- ESLint + Prettier
- Single quotes for strings
- Semicolons required
- 2-space indentation

**Naming Conventions**:
```javascript
// Variables and functions: camelCase
const generatorState = ref('idle');
function fetchStatus() {}

// Components: PascalCase
import StatusCard from './StatusCard.vue';

// Constants: UPPER_SNAKE_CASE
const API_BASE_URL = '/api';
const POLL_INTERVAL_MS = 5000;

// CSS classes: kebab-case (Tailwind)
class="status-card bg-gray-800"
```

**Component Structure**:
```vue
<script setup>
// 1. Imports
import { ref, computed, onMounted } from 'vue';
import { useGeneratorStore } from '@/stores/generator';

// 2. Props & Emits
const props = defineProps({
  title: String,
  status: String
});
const emit = defineEmits(['update', 'error']);

// 3. Store/Composables
const store = useGeneratorStore();

// 4. Reactive state
const isLoading = ref(false);

// 5. Computed properties
const statusColor = computed(() => {
  return props.status === 'running' ? 'text-green-500' : 'text-gray-500';
});

// 6. Methods
async function handleAction() {
  // ...
}

// 7. Lifecycle hooks
onMounted(() => {
  // ...
});
</script>

<template>
  <!-- Template content -->
</template>

<style scoped>
/* Scoped styles if needed beyond Tailwind */
</style>
```

---

## Configuration Management

### Environment Variables

All configuration via environment variables with `.env` files:

**GenMaster `.env.example`**:
```bash
# Application
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=your-secret-key-here

# Database (PostgreSQL)
DATABASE_HOST=db
DATABASE_PORT=5432
DATABASE_USER=genmaster
DATABASE_PASSWORD=your-password-here
DATABASE_NAME=genmaster

# GenSlave Communication
SLAVE_API_URL=http://100.x.x.x:8000
SLAVE_API_SECRET=shared-secret-key

# Heartbeat
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# Webhooks (n8n)
WEBHOOK_BASE_URL=http://100.x.x.x:5678/webhook
WEBHOOK_SECRET=webhook-secret

# Tailscale (set during setup)
TAILSCALE_AUTHKEY=tskey-auth-xxxxx

# Cloudflare (optional)
CLOUDFLARE_ENABLED=false
CLOUDFLARE_TUNNEL_TOKEN=
```

**Pydantic Settings Pattern**:
```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_env: str = "production"
    app_debug: bool = False
    app_secret_key: str

    # PostgreSQL database settings
    database_host: str = "db"
    database_port: int = 5432
    database_user: str = "genmaster"
    database_password: str
    database_name: str = "genmaster"

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL for asyncpg"""
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    slave_api_url: str
    slave_api_secret: str

    heartbeat_interval_seconds: int = 60
    heartbeat_failure_threshold: int = 3

    webhook_base_url: str
    webhook_secret: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

---

## Error Handling Patterns

### API Error Responses

Consistent error format across all endpoints:

```python
from fastapi import HTTPException
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str

# Usage
raise HTTPException(
    status_code=400,
    detail={
        "error": "Invalid Request",
        "detail": "Duration must be between 1 and 480 minutes",
        "code": "INVALID_DURATION"
    }
)
```

**Standard Error Codes**:
| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request data |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `FORBIDDEN` | 403 | Action not allowed in current state |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | State conflict (e.g., already running) |
| `SLAVE_UNREACHABLE` | 503 | Cannot communicate with GenSlave |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Service Layer Error Handling

```python
# Custom exceptions
class SlaveUnreachableError(Exception):
    """GenSlave is not responding"""
    pass

class StateConflictError(Exception):
    """Operation conflicts with current state"""
    pass

# Service usage
async def start_generator(trigger: str) -> bool:
    try:
        # Attempt to start
        await slave_client.relay_on()
        return True
    except httpx.RequestError:
        raise SlaveUnreachableError("Failed to reach GenSlave")
```

---

## Database Patterns

### Repository Pattern

```python
# app/repositories/generator_runs.py
from sqlalchemy.orm import Session
from app.models import GeneratorRun

class GeneratorRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, start_time: int, trigger_type: str) -> GeneratorRun:
        run = GeneratorRun(
            start_time=start_time,
            trigger_type=trigger_type
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_active(self) -> Optional[GeneratorRun]:
        return self.db.query(GeneratorRun).filter(
            GeneratorRun.stop_time.is_(None)
        ).first()

    def complete(self, run_id: int, stop_time: int, stop_reason: str) -> GeneratorRun:
        run = self.db.query(GeneratorRun).get(run_id)
        run.stop_time = stop_time
        run.duration_seconds = stop_time - run.start_time
        run.stop_reason = stop_reason
        self.db.commit()
        return run
```

### Single-Row State Tables

For tables that always have exactly one row (system_state, config):

```python
# app/models/system_state.py
class SystemState(Base):
    __tablename__ = "system_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    generator_running: Mapped[bool] = mapped_column(default=False)
    # ... other fields

    @classmethod
    def get_instance(cls, db: Session) -> "SystemState":
        """Get or create the singleton state row"""
        state = db.query(cls).first()
        if not state:
            state = cls(id=1)
            db.add(state)
            db.commit()
        return state
```

---

## API Authentication

### Shared Secret Authentication

```python
# app/utils/auth.py
from fastapi import Header, HTTPException, Depends
from app.config import settings

async def verify_api_key(
    x_gencontrol_secret: str = Header(..., alias="X-GenControl-Secret")
) -> bool:
    if x_gencontrol_secret != settings.slave_api_secret:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Usage in router
@router.post("/relay/on", dependencies=[Depends(verify_api_key)])
async def relay_on():
    pass
```

---

## Logging Strategy

### Database-Only Logging

To minimize SSD writes, log only to database (no file logs):

```python
# app/utils/logging.py
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import EventLog

class DatabaseLogger:
    def __init__(self, db: Session):
        self.db = db

    def log(self, event_type: str, data: dict = None):
        event = EventLog(
            event_type=event_type,
            event_data=data,
            created_at=datetime.utcnow()
        )
        self.db.add(event)
        self.db.commit()

    def info(self, message: str, **kwargs):
        self.log("INFO", {"message": message, **kwargs})

    def warning(self, message: str, **kwargs):
        self.log("WARNING", {"message": message, **kwargs})

    def error(self, message: str, **kwargs):
        self.log("ERROR", {"message": message, **kwargs})
```

**Event Types to Log**:
- `GENERATOR_START` - Generator started (include trigger)
- `GENERATOR_STOP` - Generator stopped (include reason)
- `HEARTBEAT_LOST` - Communication lost
- `HEARTBEAT_RESTORED` - Communication restored
- `OVERRIDE_ENABLED` - Manual override activated
- `OVERRIDE_DISABLED` - Manual override deactivated
- `SYSTEM_BOOT` - System startup complete
- `CONFIG_CHANGED` - Configuration modified
- `ERROR` - Any error conditions

---

## Testing Requirements

### Test Coverage Expectations

- **Models**: 90%+ coverage
- **Services**: 85%+ coverage
- **API Endpoints**: 80%+ coverage
- **Frontend Components**: 70%+ coverage (Vue Test Utils)

### Test Structure

```python
# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.main import app

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def client(test_db):
    from fastapi.testclient import TestClient
    # Override dependency
    app.dependency_overrides[get_db] = lambda: test_db
    return TestClient(app)
```

---

## Git Workflow

### Branch Naming
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates

### Commit Message Format
```
<type>: <short description>

<optional longer description>

Co-Authored-By: Claude <agent>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

---

## Agent Instructions

When building your assigned component:

1. **Read this document first** - Understand conventions before coding
2. **Follow the file structure exactly** - Don't deviate from the defined paths
3. **Use type hints** - All Python code must be fully typed
4. **Write tests** - Include tests for all new functionality
5. **Handle errors gracefully** - Use the defined error patterns
6. **Log important events** - Use database logging for critical events
7. **Keep it simple** - Don't over-engineer; build exactly what's specified
8. **Reference the outline** - See `generator_project_outline.md` for full context

---

## Related Documents

- `02-database-schema.md` - Complete database design
- `03-genmaster-backend.md` - GenMaster API implementation
- `04-genmaster-frontend.md` - Vue.js frontend implementation
- `05-genslave-backend.md` - GenSlave API implementation
- `06-docker-infrastructure.md` - Docker and nginx configuration
- `07-networking.md` - Tailscale and Cloudflare setup
- `08-setup-scripts.md` - Installation scripts
- `PROJECT_TRACKER.md` - Master task tracking
