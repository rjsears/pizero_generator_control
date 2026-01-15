# Agent Handoff: GenMaster Backend API

## Purpose
This document provides complete specifications for building the GenMaster FastAPI backend, including all endpoints, services, business logic, and integration points.

---

## Overview

GenMaster is the primary controller that:
1. Monitors Victron Cerbo GX relay signal via GPIO17
2. Hosts the web interface and REST API
3. Manages generator state machine
4. Communicates with GenSlave via heartbeat protocol
5. Sends webhook notifications to n8n
6. Handles scheduled generator runs

---

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | 0.109+ | Web framework |
| Uvicorn | 0.27+ | ASGI server |
| SQLAlchemy | 2.0+ | ORM |
| APScheduler | 3.10+ | Task scheduling |
| gpiozero | 2.0+ | GPIO access |
| httpx | 0.26+ | Async HTTP client |
| Pydantic | 2.5+ | Data validation |

---

## Application Structure

```
genmaster/app/
├── __init__.py
├── main.py              # FastAPI app & lifespan
├── config.py            # Settings
├── database.py          # SQLAlchemy setup
├── dependencies.py      # FastAPI dependencies
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── routers/             # API endpoints
├── services/            # Business logic
├── repositories/        # Data access
└── utils/               # Utilities
```

---

## Main Application Entry Point

```python
# genmaster/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import (
    generator, health, system, schedule,
    config as config_router, backup, override
)
from app.services.gpio_monitor import GPIOMonitor
from app.services.heartbeat import HeartbeatService
from app.services.scheduler import SchedulerService
from app.services.state_machine import StateMachine

# Global service instances
gpio_monitor: GPIOMonitor = None
heartbeat_service: HeartbeatService = None
scheduler_service: SchedulerService = None
state_machine: StateMachine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global gpio_monitor, heartbeat_service, scheduler_service, state_machine

    # Startup
    print("Starting GenMaster services...")

    # Initialize state machine
    state_machine = StateMachine()
    await state_machine.initialize()

    # Initialize GPIO monitoring
    gpio_monitor = GPIOMonitor(state_machine)
    gpio_monitor.start()

    # Initialize heartbeat service
    heartbeat_service = HeartbeatService(state_machine)
    await heartbeat_service.start()

    # Initialize scheduler
    scheduler_service = SchedulerService(state_machine)
    scheduler_service.start()

    # Log startup complete
    await state_machine.log_event("SYSTEM_BOOT", {"version": "1.0.0"})

    yield

    # Shutdown
    print("Shutting down GenMaster services...")
    scheduler_service.stop()
    await heartbeat_service.stop()
    gpio_monitor.stop()
    await state_machine.log_event("SYSTEM_SHUTDOWN")


app = FastAPI(
    title="GenMaster API",
    description="Generator Control System - Master Controller",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generator.router, prefix="/api/generator", tags=["Generator"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(config_router.router, prefix="/api/config", tags=["Config"])
app.include_router(backup.router, prefix="/api/backup", tags=["Backup"])
app.include_router(override.router, prefix="/api/override", tags=["Override"])


@app.get("/api/status")
async def get_status():
    """Get complete system status."""
    return await state_machine.get_full_status()


# Dependency to access services from routes
def get_state_machine() -> StateMachine:
    return state_machine

def get_heartbeat_service() -> HeartbeatService:
    return heartbeat_service

def get_scheduler_service() -> SchedulerService:
    return scheduler_service
```

---

## Configuration

```python
# genmaster/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_env: str = "production"
    app_debug: bool = False
    app_secret_key: str = "change-me-in-production"

    # PostgreSQL Database
    database_host: str = "db"
    database_port: int = 5432
    database_user: str = "genmaster"
    database_password: str = "change-me"
    database_name: str = "genmaster"

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL for asyncpg."""
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL URL for Alembic migrations."""
        return f"postgresql+psycopg2://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"

    # GenSlave Communication
    slave_api_url: str = "http://genslave:8000"
    slave_api_secret: str = "change-me"

    # Heartbeat (defaults, can be overridden in DB config)
    heartbeat_interval_seconds: int = 60
    heartbeat_failure_threshold: int = 3
    heartbeat_timeout_seconds: int = 10

    # Webhooks
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_timeout_seconds: int = 10

    # GPIO
    victron_gpio_pin: int = 17
    gpio_bounce_time: float = 0.1

    # Tailscale
    tailscale_authkey: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

## Pydantic Schemas

### Generator Schemas

```python
# genmaster/app/schemas/generator.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class GeneratorStatus(BaseModel):
    """Current generator status."""
    running: bool
    start_time: Optional[int] = None
    runtime_seconds: Optional[int] = None
    trigger: Literal["idle", "victron", "manual", "scheduled"]
    current_run_id: Optional[int] = None

    class Config:
        from_attributes = True


class GeneratorStartRequest(BaseModel):
    """Request to manually start the generator."""
    duration_minutes: int = Field(
        ...,
        ge=1,
        le=480,
        description="Run duration in minutes (1-480)"
    )
    notes: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional notes for this run"
    )


class GeneratorStartResponse(BaseModel):
    """Response after starting generator."""
    success: bool
    message: str
    run_id: Optional[int] = None
    start_time: Optional[int] = None


class GeneratorStopRequest(BaseModel):
    """Request to manually stop the generator."""
    reason: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional reason for stopping"
    )


class GeneratorStopResponse(BaseModel):
    """Response after stopping generator."""
    success: bool
    message: str
    run_id: Optional[int] = None
    runtime_seconds: Optional[int] = None


class GeneratorRunHistory(BaseModel):
    """Historical generator run record."""
    id: int
    start_time: int
    stop_time: Optional[int]
    duration_seconds: Optional[int]
    trigger_type: str
    stop_reason: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class GeneratorStats(BaseModel):
    """Generator runtime statistics."""
    total_runtime_seconds: int
    total_runtime_formatted: str
    run_count: int
    avg_runtime_seconds: Optional[int]
    by_trigger: dict
    period_start: int
    period_end: int
```

### Health Schemas

```python
# genmaster/app/schemas/health.py
from pydantic import BaseModel
from typing import Optional, Literal


class SlaveHealth(BaseModel):
    """GenSlave health status."""
    status: Literal["connected", "disconnected", "unknown"]
    last_heartbeat: Optional[int] = None
    last_heartbeat_ago_seconds: Optional[int] = None
    missed_count: int = 0
    relay_state: Optional[bool] = None
    latency_ms: Optional[int] = None


class HeartbeatTestResponse(BaseModel):
    """Response from heartbeat test."""
    success: bool
    latency_ms: Optional[int] = None
    slave_status: Optional[dict] = None
    error: Optional[str] = None


class WebhookTestResponse(BaseModel):
    """Response from webhook test."""
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
```

### System Schemas

```python
# genmaster/app/schemas/system.py
from pydantic import BaseModel
from typing import Optional


class SystemHealth(BaseModel):
    """System health metrics."""
    cpu_percent: float
    ram_percent: float
    ram_used_mb: int
    ram_total_mb: int
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    temperature_celsius: Optional[float] = None
    uptime_seconds: int
    health_status: str  # good, warning, critical


class CombinedSystemHealth(BaseModel):
    """Combined health for both devices."""
    genmaster: SystemHealth
    genslave: Optional[SystemHealth] = None


class VictronStatus(BaseModel):
    """Victron relay input status."""
    signal_active: bool
    gpio_pin: int
    last_change: Optional[int] = None
    last_change_ago_seconds: Optional[int] = None


class FullSystemStatus(BaseModel):
    """Complete system status."""
    generator: dict
    victron: VictronStatus
    slave_health: dict
    override: dict
    system_health: SystemHealth
```

### Schedule Schemas

```python
# genmaster/app/schemas/schedule.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime


class ScheduleCreateRequest(BaseModel):
    """Request to create a scheduled run."""
    name: Optional[str] = Field(None, max_length=100)
    scheduled_start: int = Field(..., description="Unix timestamp for start time")
    duration_minutes: int = Field(..., ge=1, le=480)
    recurring: bool = False
    recurrence_pattern: Optional[str] = Field(
        None,
        description="Recurrence: 'daily', 'weekly', or cron expression"
    )
    recurrence_end_date: Optional[int] = Field(
        None,
        description="Unix timestamp when recurrence ends"
    )

    @field_validator('scheduled_start')
    @classmethod
    def validate_future_time(cls, v):
        import time
        if v < time.time():
            raise ValueError("Scheduled start must be in the future")
        return v

    @field_validator('recurrence_pattern')
    @classmethod
    def validate_recurrence(cls, v, info):
        if info.data.get('recurring') and not v:
            raise ValueError("recurrence_pattern required when recurring=True")
        return v


class ScheduleResponse(BaseModel):
    """Scheduled run response."""
    id: int
    name: Optional[str]
    scheduled_start: int
    scheduled_start_formatted: str
    duration_minutes: int
    recurring: bool
    recurrence_pattern: Optional[str]
    enabled: bool
    next_execution: Optional[int]
    next_execution_formatted: Optional[str]
    last_executed: Optional[int]
    execution_count: int

    class Config:
        from_attributes = True


class ScheduleUpdateRequest(BaseModel):
    """Request to update a scheduled run."""
    name: Optional[str] = None
    scheduled_start: Optional[int] = None
    duration_minutes: Optional[int] = Field(None, ge=1, le=480)
    enabled: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    recurrence_end_date: Optional[int] = None
```

### Config Schemas

```python
# genmaster/app/schemas/config.py
from pydantic import BaseModel, Field
from typing import Optional


class ConfigResponse(BaseModel):
    """System configuration (read)."""
    heartbeat_interval_seconds: int
    heartbeat_failure_threshold: int
    webhook_enabled: bool
    webhook_base_url: Optional[str]
    temp_warning_celsius: int
    temp_critical_celsius: int
    disk_warning_percent: int
    disk_critical_percent: int
    ram_warning_percent: int
    event_log_retention_days: int
    tailscale_hostname: Optional[str]
    cloudflare_enabled: bool
    cloudflare_hostname: Optional[str]


class ConfigUpdateRequest(BaseModel):
    """System configuration update."""
    heartbeat_interval_seconds: Optional[int] = Field(None, ge=10, le=300)
    heartbeat_failure_threshold: Optional[int] = Field(None, ge=1, le=10)
    webhook_enabled: Optional[bool] = None
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    temp_warning_celsius: Optional[int] = Field(None, ge=50, le=90)
    temp_critical_celsius: Optional[int] = Field(None, ge=60, le=100)
    disk_warning_percent: Optional[int] = Field(None, ge=50, le=95)
    disk_critical_percent: Optional[int] = Field(None, ge=60, le=99)
    ram_warning_percent: Optional[int] = Field(None, ge=50, le=95)
    event_log_retention_days: Optional[int] = Field(None, ge=1, le=365)
```

### Webhook Schemas

```python
# genmaster/app/schemas/webhook.py
from pydantic import BaseModel
from typing import Optional, Any


class WebhookPayload(BaseModel):
    """Webhook notification payload."""
    event: str
    timestamp: int
    source: str = "genmaster"
    data: dict
    meta: dict


class WebhookEvent:
    """Webhook event types."""
    GENERATOR_STARTED_VICTRON = "generator.started.victron"
    GENERATOR_STARTED_MANUAL = "generator.started.manual"
    GENERATOR_STARTED_SCHEDULED = "generator.started.scheduled"
    GENERATOR_STOPPED_VICTRON = "generator.stopped.victron"
    GENERATOR_STOPPED_MANUAL = "generator.stopped.manual"
    GENERATOR_STOPPED_SCHEDULED = "generator.stopped.scheduled_end"
    GENERATOR_STOPPED_COMM_LOSS = "generator.stopped.comm_loss"
    COMMUNICATION_LOST = "communication.lost"
    COMMUNICATION_RESTORED = "communication.restored"
    OVERRIDE_ENABLED = "override.enabled"
    OVERRIDE_DISABLED = "override.disabled"
    SYSTEM_REBOOT = "system.reboot"
    HEALTH_WARNING = "health.warning"
```

---

## API Routers

### Generator Router

```python
# genmaster/app/routers/generator.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import time

from app.database import get_db
from app.schemas.generator import (
    GeneratorStatus, GeneratorStartRequest, GeneratorStartResponse,
    GeneratorStopRequest, GeneratorStopResponse, GeneratorRunHistory,
    GeneratorStats
)
from app.services.state_machine import StateMachine
from app.main import get_state_machine
from app.repositories.generator_runs import GeneratorRunRepository

router = APIRouter()


@router.get("/state", response_model=GeneratorStatus)
async def get_generator_state(
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Get current generator state."""
    return await state_machine.get_generator_status()


@router.post("/start", response_model=GeneratorStartResponse)
async def start_generator(
    request: GeneratorStartRequest,
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Manually start the generator."""
    try:
        result = await state_machine.start_generator(
            trigger="manual",
            duration_minutes=request.duration_minutes,
            notes=request.notes
        )
        return GeneratorStartResponse(
            success=True,
            message="Generator started successfully",
            run_id=result.run_id,
            start_time=result.start_time
        )
    except StateConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SlaveUnreachableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/stop", response_model=GeneratorStopResponse)
async def stop_generator(
    request: GeneratorStopRequest,
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Manually stop the generator."""
    try:
        result = await state_machine.stop_generator(
            reason="manual",
            notes=request.reason
        )
        return GeneratorStopResponse(
            success=True,
            message="Generator stopped successfully",
            run_id=result.run_id,
            runtime_seconds=result.runtime_seconds
        )
    except StateConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SlaveUnreachableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/history", response_model=list[GeneratorRunHistory])
async def get_run_history(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get generator run history."""
    repo = GeneratorRunRepository(db)
    runs = repo.get_recent(limit=limit, offset=offset)
    return [GeneratorRunHistory.model_validate(run) for run in runs]


@router.get("/stats", response_model=GeneratorStats)
async def get_generator_stats(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get generator runtime statistics."""
    repo = GeneratorRunRepository(db)
    since = int(time.time()) - (days * 86400)
    now = int(time.time())

    total_seconds = repo.get_total_runtime_seconds(since)
    run_count = repo.get_run_count(since)
    by_trigger = repo.get_stats_by_trigger(since)

    # Format total runtime
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    formatted = f"{hours}h {minutes}m"

    return GeneratorStats(
        total_runtime_seconds=total_seconds,
        total_runtime_formatted=formatted,
        run_count=run_count,
        avg_runtime_seconds=total_seconds // run_count if run_count > 0 else None,
        by_trigger=by_trigger,
        period_start=since,
        period_end=now
    )
```

### Health Router

```python
# genmaster/app/routers/health.py
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.health import SlaveHealth, HeartbeatTestResponse, WebhookTestResponse
from app.services.heartbeat import HeartbeatService
from app.services.webhook import WebhookService
from app.main import get_heartbeat_service, get_state_machine

router = APIRouter()


@router.get("/slave", response_model=SlaveHealth)
async def get_slave_health(
    state_machine = Depends(get_state_machine)
):
    """Get GenSlave health status."""
    return await state_machine.get_slave_health()


@router.post("/test-heartbeat", response_model=HeartbeatTestResponse)
async def test_heartbeat(
    heartbeat_service: HeartbeatService = Depends(get_heartbeat_service)
):
    """Send a test heartbeat to GenSlave."""
    try:
        result = await heartbeat_service.send_heartbeat(test=True)
        return HeartbeatTestResponse(
            success=True,
            latency_ms=result.latency_ms,
            slave_status=result.slave_status
        )
    except Exception as e:
        return HeartbeatTestResponse(
            success=False,
            error=str(e)
        )


@router.post("/test-webhook", response_model=WebhookTestResponse)
async def test_webhook(
    state_machine = Depends(get_state_machine)
):
    """Send a test webhook notification."""
    webhook_service = WebhookService()
    try:
        result = await webhook_service.send_test()
        return WebhookTestResponse(
            success=True,
            status_code=result.status_code,
            response_time_ms=result.response_time_ms
        )
    except Exception as e:
        return WebhookTestResponse(
            success=False,
            error=str(e)
        )
```

### System Router

```python
# genmaster/app/routers/system.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.schemas.system import SystemHealth, CombinedSystemHealth, VictronStatus, FullSystemStatus
from app.utils.system_info import get_system_health
from app.services.state_machine import StateMachine
from app.main import get_state_machine

router = APIRouter()


@router.get("/health", response_model=SystemHealth)
async def get_system_health_endpoint():
    """Get GenMaster system health metrics."""
    return get_system_health()


@router.get("/health/all", response_model=CombinedSystemHealth)
async def get_all_system_health(
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Get health metrics for both GenMaster and GenSlave."""
    master_health = get_system_health()
    slave_health = await state_machine.get_slave_system_health()

    return CombinedSystemHealth(
        genmaster=master_health,
        genslave=slave_health
    )


@router.get("/victron", response_model=VictronStatus)
async def get_victron_status(
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Get Victron relay input status."""
    return await state_machine.get_victron_status()


@router.post("/reboot")
async def reboot_system(
    background_tasks: BackgroundTasks,
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Initiate system reboot."""
    await state_machine.log_event("SYSTEM_REBOOT")
    await state_machine.send_webhook("system.reboot", {})

    # Schedule reboot in background
    background_tasks.add_task(_perform_reboot)

    return {"message": "Reboot initiated", "delay_seconds": 5}


async def _perform_reboot():
    """Perform system reboot after delay."""
    import asyncio
    import subprocess
    await asyncio.sleep(5)
    subprocess.run(["sudo", "reboot"])
```

### Schedule Router

```python
# genmaster/app/routers/schedule.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.schedule import (
    ScheduleCreateRequest, ScheduleResponse, ScheduleUpdateRequest
)
from app.repositories.scheduled_runs import ScheduledRunRepository
from app.services.scheduler import SchedulerService
from app.main import get_scheduler_service

router = APIRouter()


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    enabled_only: bool = False,
    db: Session = Depends(get_db)
):
    """List all scheduled runs."""
    repo = ScheduledRunRepository(db)
    schedules = repo.get_all(enabled_only=enabled_only)
    return [_format_schedule(s) for s in schedules]


@router.post("", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleCreateRequest,
    db: Session = Depends(get_db),
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Create a new scheduled run."""
    repo = ScheduledRunRepository(db)
    schedule = repo.create(
        name=request.name,
        scheduled_start=request.scheduled_start,
        duration_minutes=request.duration_minutes,
        recurring=request.recurring,
        recurrence_pattern=request.recurrence_pattern,
        recurrence_end_date=request.recurrence_end_date
    )

    # Register with scheduler
    scheduler.add_schedule(schedule)

    return _format_schedule(schedule)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific scheduled run."""
    repo = ScheduledRunRepository(db)
    schedule = repo.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return _format_schedule(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    request: ScheduleUpdateRequest,
    db: Session = Depends(get_db),
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Update a scheduled run."""
    repo = ScheduledRunRepository(db)
    schedule = repo.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule = repo.update(schedule_id, **request.model_dump(exclude_unset=True))

    # Update in scheduler
    scheduler.update_schedule(schedule)

    return _format_schedule(schedule)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Delete a scheduled run."""
    repo = ScheduledRunRepository(db)
    schedule = repo.get_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Remove from scheduler
    scheduler.remove_schedule(schedule_id)

    repo.delete(schedule_id)
    return {"message": "Schedule deleted"}


def _format_schedule(schedule) -> ScheduleResponse:
    """Format schedule for response."""
    from datetime import datetime
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        scheduled_start=schedule.scheduled_start,
        scheduled_start_formatted=datetime.fromtimestamp(schedule.scheduled_start).isoformat(),
        duration_minutes=schedule.duration_minutes,
        recurring=schedule.recurring,
        recurrence_pattern=schedule.recurrence_pattern,
        enabled=schedule.enabled,
        next_execution=schedule.next_execution,
        next_execution_formatted=(
            datetime.fromtimestamp(schedule.next_execution).isoformat()
            if schedule.next_execution else None
        ),
        last_executed=schedule.last_executed,
        execution_count=schedule.execution_count
    )
```

### Override Router

```python
# genmaster/app/routers/override.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Literal

from app.services.state_machine import StateMachine
from app.main import get_state_machine

router = APIRouter()


class OverrideStatus(BaseModel):
    enabled: bool
    type: Literal["none", "force_run", "force_stop"]


class OverrideEnableRequest(BaseModel):
    type: Literal["force_run", "force_stop"]


@router.get("", response_model=OverrideStatus)
async def get_override_status(
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Get current override status."""
    return await state_machine.get_override_status()


@router.post("/enable", response_model=OverrideStatus)
async def enable_override(
    request: OverrideEnableRequest,
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Enable manual override."""
    await state_machine.enable_override(request.type)
    return await state_machine.get_override_status()


@router.post("/disable", response_model=OverrideStatus)
async def disable_override(
    state_machine: StateMachine = Depends(get_state_machine)
):
    """Disable manual override."""
    await state_machine.disable_override()
    return await state_machine.get_override_status()
```

### Config Router

```python
# genmaster/app/routers/config.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.config import ConfigResponse, ConfigUpdateRequest
from app.models import Config

router = APIRouter()


@router.get("", response_model=ConfigResponse)
async def get_config(db: Session = Depends(get_db)):
    """Get system configuration."""
    config = Config.get_instance(db)
    return ConfigResponse(
        heartbeat_interval_seconds=config.heartbeat_interval_seconds,
        heartbeat_failure_threshold=config.heartbeat_failure_threshold,
        webhook_enabled=config.webhook_enabled,
        webhook_base_url=config.webhook_base_url,
        temp_warning_celsius=config.temp_warning_celsius,
        temp_critical_celsius=config.temp_critical_celsius,
        disk_warning_percent=config.disk_warning_percent,
        disk_critical_percent=config.disk_critical_percent,
        ram_warning_percent=config.ram_warning_percent,
        event_log_retention_days=config.event_log_retention_days,
        tailscale_hostname=config.tailscale_hostname,
        cloudflare_enabled=config.cloudflare_enabled,
        cloudflare_hostname=config.cloudflare_hostname
    )


@router.put("", response_model=ConfigResponse)
async def update_config(
    request: ConfigUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update system configuration."""
    config = Config.get_instance(db)

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)

    # Log config change
    from app.models import EventLog
    EventLog.log(db, "CONFIG_CHANGED", {"updated_fields": list(update_data.keys())})

    return await get_config(db)
```

### Backup Router

```python
# genmaster/app/routers/backup.py
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.services.backup import BackupService

router = APIRouter()


@router.post("")
async def create_backup(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger database backup."""
    backup_service = BackupService()
    backup_path = await backup_service.create_backup()

    return {
        "message": "Backup created",
        "filename": os.path.basename(backup_path),
        "size_bytes": os.path.getsize(backup_path)
    }


@router.get("/download")
async def download_backup():
    """Download the latest backup file."""
    backup_service = BackupService()
    backup_path = backup_service.get_latest_backup()

    if not backup_path or not os.path.exists(backup_path):
        raise HTTPException(status_code=404, detail="No backup available")

    return FileResponse(
        backup_path,
        media_type="application/gzip",
        filename=os.path.basename(backup_path)
    )


@router.get("/list")
async def list_backups():
    """List available backups."""
    backup_service = BackupService()
    backups = backup_service.list_backups()
    return {"backups": backups}
```

---

## Services

### State Machine Service

```python
# genmaster/app/services/state_machine.py
import time
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import SystemState, Config, GeneratorRun, EventLog
from app.services.slave_client import SlaveClient
from app.services.webhook import WebhookService


class StartResult:
    def __init__(self, run_id: int, start_time: int):
        self.run_id = run_id
        self.start_time = start_time


class StopResult:
    def __init__(self, run_id: int, runtime_seconds: int):
        self.run_id = run_id
        self.runtime_seconds = runtime_seconds


class StateConflictError(Exception):
    pass


class SlaveUnreachableError(Exception):
    pass


class StateMachine:
    """Manages generator state transitions."""

    def __init__(self):
        self.slave_client = SlaveClient()
        self.webhook_service = WebhookService()
        self._db: Optional[Session] = None

    def _get_db(self) -> Session:
        if self._db is None or not self._db.is_active:
            self._db = SessionLocal()
        return self._db

    async def initialize(self):
        """Initialize state machine on startup."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        # Check if generator was running before restart
        if state.generator_running:
            # Attempt to sync with GenSlave
            try:
                slave_status = await self.slave_client.get_status()
                if not slave_status.get('relay_state'):
                    # GenSlave says relay is off, sync our state
                    state.generator_running = False
                    state.run_trigger = "idle"
                    db.commit()
            except Exception:
                # Can't reach slave, mark disconnected
                state.slave_connection_status = "disconnected"
                db.commit()

    async def start_generator(
        self,
        trigger: str,
        duration_minutes: Optional[int] = None,
        notes: Optional[str] = None,
        scheduled_run_id: Optional[int] = None
    ) -> StartResult:
        """Start the generator."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        # Check if can start
        if state.generator_running:
            raise StateConflictError("Generator is already running")

        if state.override_enabled and state.override_type == "force_stop":
            raise StateConflictError("Override is preventing generator start")

        if state.slave_connection_status == "disconnected":
            raise SlaveUnreachableError("Cannot start: GenSlave is disconnected")

        # Send command to GenSlave
        try:
            await self.slave_client.relay_on()
        except Exception as e:
            raise SlaveUnreachableError(f"Failed to communicate with GenSlave: {e}")

        # Create run record
        start_time = int(time.time())
        run = GeneratorRun(
            start_time=start_time,
            trigger_type=trigger,
            scheduled_run_id=scheduled_run_id,
            notes=notes
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Update state
        state.generator_running = True
        state.generator_start_time = start_time
        state.current_run_id = run.id
        state.run_trigger = trigger
        db.commit()

        # Log event
        EventLog.log(db, "GENERATOR_START", {
            "trigger": trigger,
            "run_id": run.id,
            "duration_minutes": duration_minutes
        })

        # Send webhook
        await self.send_webhook(f"generator.started.{trigger}", {
            "generator_state": "running",
            "trigger": trigger,
            "run_id": run.id
        })

        # Schedule auto-stop if duration specified
        if duration_minutes:
            from app.main import scheduler_service
            scheduler_service.schedule_auto_stop(run.id, duration_minutes)

        return StartResult(run_id=run.id, start_time=start_time)

    async def stop_generator(
        self,
        reason: str,
        notes: Optional[str] = None
    ) -> StopResult:
        """Stop the generator."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        if not state.generator_running:
            raise StateConflictError("Generator is not running")

        # Send command to GenSlave
        try:
            await self.slave_client.relay_off()
        except Exception as e:
            # Log error but still update local state
            EventLog.log(db, "ERROR", {
                "message": f"Failed to send stop command: {e}",
                "action": "stop_generator"
            }, severity="ERROR")

        stop_time = int(time.time())
        runtime_seconds = stop_time - state.generator_start_time

        # Update run record
        if state.current_run_id:
            run = db.query(GeneratorRun).get(state.current_run_id)
            if run:
                run.stop_time = stop_time
                run.duration_seconds = runtime_seconds
                run.stop_reason = reason
                if notes:
                    run.notes = (run.notes or "") + f" Stop: {notes}"

        run_id = state.current_run_id

        # Update state
        state.generator_running = False
        state.generator_start_time = None
        state.current_run_id = None
        state.run_trigger = "idle"
        db.commit()

        # Log event
        EventLog.log(db, "GENERATOR_STOP", {
            "reason": reason,
            "run_id": run_id,
            "runtime_seconds": runtime_seconds
        })

        # Send webhook
        await self.send_webhook(f"generator.stopped.{reason}", {
            "generator_state": "stopped",
            "reason": reason,
            "run_id": run_id,
            "runtime_seconds": runtime_seconds
        })

        return StopResult(run_id=run_id, runtime_seconds=runtime_seconds)

    async def handle_victron_signal_change(self, signal_active: bool):
        """Handle Victron relay signal change."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        # Update signal state
        state.victron_signal_state = signal_active
        state.victron_last_change = int(time.time())
        db.commit()

        EventLog.log(db, "VICTRON_SIGNAL_CHANGE", {"active": signal_active})

        # Check override
        if state.override_enabled:
            return  # Ignore Victron when override is active

        if signal_active and not state.generator_running:
            # Victron wants generator to run
            try:
                await self.start_generator(trigger="victron")
            except (StateConflictError, SlaveUnreachableError) as e:
                EventLog.log(db, "ERROR", {
                    "message": f"Failed to start on Victron signal: {e}"
                }, severity="ERROR")

        elif not signal_active and state.generator_running and state.run_trigger == "victron":
            # Victron wants generator to stop (only if Victron started it)
            try:
                await self.stop_generator(reason="victron")
            except StateConflictError as e:
                EventLog.log(db, "ERROR", {
                    "message": f"Failed to stop on Victron signal: {e}"
                }, severity="ERROR")

    async def enable_override(self, override_type: str):
        """Enable manual override."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        state.override_enabled = True
        state.override_type = override_type
        db.commit()

        EventLog.log(db, "OVERRIDE_ENABLED", {"type": override_type})
        await self.send_webhook("override.enabled", {"type": override_type})

        # If force_stop and generator is running, stop it
        if override_type == "force_stop" and state.generator_running:
            await self.stop_generator(reason="override")

    async def disable_override(self):
        """Disable manual override."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        state.override_enabled = False
        state.override_type = "none"
        db.commit()

        EventLog.log(db, "OVERRIDE_DISABLED")
        await self.send_webhook("override.disabled", {})

        # Check if Victron wants generator running
        if state.victron_signal_state and not state.generator_running:
            try:
                await self.start_generator(trigger="victron")
            except Exception:
                pass  # Will be logged in start_generator

    async def update_heartbeat_status(
        self,
        success: bool,
        slave_status: Optional[dict] = None
    ):
        """Update heartbeat status after send attempt."""
        db = self._get_db()
        state = SystemState.get_instance(db)
        config = Config.get_instance(db)

        state.last_heartbeat_sent = int(time.time())

        if success:
            state.last_heartbeat_received = int(time.time())
            state.missed_heartbeat_count = 0

            # Update slave status if provided
            if slave_status:
                state.slave_relay_state = slave_status.get('relay_state')

            # Check if was disconnected
            if state.slave_connection_status == "disconnected":
                state.slave_connection_status = "connected"
                EventLog.log(db, "COMM_RESTORED")
                await self.send_webhook("communication.restored", {})
            else:
                state.slave_connection_status = "connected"

        else:
            state.missed_heartbeat_count += 1

            # Check threshold
            if state.missed_heartbeat_count >= config.heartbeat_failure_threshold:
                if state.slave_connection_status != "disconnected":
                    state.slave_connection_status = "disconnected"
                    EventLog.log(db, "COMM_LOST", {
                        "missed_count": state.missed_heartbeat_count
                    }, severity="ERROR")
                    await self.send_webhook("communication.lost", {
                        "missed_count": state.missed_heartbeat_count
                    })

        db.commit()

    async def send_webhook(self, event: str, data: dict):
        """Send webhook notification."""
        await self.webhook_service.send(event, data)

    async def log_event(self, event_type: str, data: dict = None, severity: str = "INFO"):
        """Log an event to the database."""
        db = self._get_db()
        EventLog.log(db, event_type, data, severity)

    async def get_generator_status(self) -> dict:
        """Get current generator status."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        runtime_seconds = None
        if state.generator_running and state.generator_start_time:
            runtime_seconds = int(time.time()) - state.generator_start_time

        return {
            "running": state.generator_running,
            "start_time": state.generator_start_time,
            "runtime_seconds": runtime_seconds,
            "trigger": state.run_trigger,
            "current_run_id": state.current_run_id
        }

    async def get_override_status(self) -> dict:
        """Get current override status."""
        db = self._get_db()
        state = SystemState.get_instance(db)
        return {
            "enabled": state.override_enabled,
            "type": state.override_type
        }

    async def get_slave_health(self) -> dict:
        """Get GenSlave health status."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        last_heartbeat_ago = None
        if state.last_heartbeat_received:
            last_heartbeat_ago = int(time.time()) - state.last_heartbeat_received

        return {
            "status": state.slave_connection_status,
            "last_heartbeat": state.last_heartbeat_received,
            "last_heartbeat_ago_seconds": last_heartbeat_ago,
            "missed_count": state.missed_heartbeat_count,
            "relay_state": state.slave_relay_state
        }

    async def get_victron_status(self) -> dict:
        """Get Victron input status."""
        db = self._get_db()
        state = SystemState.get_instance(db)

        last_change_ago = None
        if state.victron_last_change:
            last_change_ago = int(time.time()) - state.victron_last_change

        return {
            "signal_active": state.victron_signal_state,
            "gpio_pin": 17,
            "last_change": state.victron_last_change,
            "last_change_ago_seconds": last_change_ago
        }

    async def get_full_status(self) -> dict:
        """Get complete system status."""
        from app.utils.system_info import get_system_health

        return {
            "generator": await self.get_generator_status(),
            "victron": await self.get_victron_status(),
            "slave_health": await self.get_slave_health(),
            "override": await self.get_override_status(),
            "system_health": get_system_health()
        }

    async def get_slave_system_health(self) -> Optional[dict]:
        """Get GenSlave system health."""
        try:
            return await self.slave_client.get_system_health()
        except Exception:
            return None
```

### GPIO Monitor Service

```python
# genmaster/app/services/gpio_monitor.py
import asyncio
from gpiozero import Button
from app.config import settings
from app.services.state_machine import StateMachine


class GPIOMonitor:
    """Monitors Victron relay signal on GPIO17."""

    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.gpio_pin = settings.victron_gpio_pin
        self.button: Button = None
        self._running = False

    def start(self):
        """Start GPIO monitoring."""
        self.button = Button(
            self.gpio_pin,
            pull_up=True,
            bounce_time=settings.gpio_bounce_time
        )

        # When Victron closes relay, GPIO goes LOW (button "pressed")
        self.button.when_pressed = self._on_signal_active
        # When Victron opens relay, GPIO goes HIGH (button "released")
        self.button.when_released = self._on_signal_inactive

        self._running = True

        # Check initial state
        if self.button.is_pressed:
            asyncio.create_task(
                self.state_machine.handle_victron_signal_change(True)
            )

    def stop(self):
        """Stop GPIO monitoring."""
        self._running = False
        if self.button:
            self.button.close()

    def _on_signal_active(self):
        """Called when Victron relay closes (wants generator to run)."""
        if self._running:
            asyncio.create_task(
                self.state_machine.handle_victron_signal_change(True)
            )

    def _on_signal_inactive(self):
        """Called when Victron relay opens (wants generator to stop)."""
        if self._running:
            asyncio.create_task(
                self.state_machine.handle_victron_signal_change(False)
            )

    def get_current_state(self) -> bool:
        """Get current GPIO state."""
        if self.button:
            return self.button.is_pressed
        return False
```

### Heartbeat Service

```python
# genmaster/app/services/heartbeat.py
import asyncio
import time
from typing import Optional
from dataclasses import dataclass
from app.config import settings
from app.services.slave_client import SlaveClient
from app.services.state_machine import StateMachine
from app.database import SessionLocal
from app.models import Config


@dataclass
class HeartbeatResult:
    success: bool
    latency_ms: Optional[int] = None
    slave_status: Optional[dict] = None
    error: Optional[str] = None


class HeartbeatService:
    """Manages heartbeat communication with GenSlave."""

    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.slave_client = SlaveClient()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._sequence = 0

    async def start(self):
        """Start heartbeat service."""
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self):
        """Stop heartbeat service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self._running:
            # Get interval from config
            db = SessionLocal()
            try:
                config = Config.get_instance(db)
                interval = config.heartbeat_interval_seconds
            finally:
                db.close()

            # Send heartbeat
            result = await self.send_heartbeat()
            await self.state_machine.update_heartbeat_status(
                success=result.success,
                slave_status=result.slave_status
            )

            # Wait for next interval
            await asyncio.sleep(interval)

    async def send_heartbeat(self, test: bool = False) -> HeartbeatResult:
        """Send a heartbeat to GenSlave."""
        self._sequence += 1
        start_time = time.time()

        try:
            # Get current master state
            master_state = await self.state_machine.get_generator_status()

            # Send heartbeat
            response = await self.slave_client.heartbeat(
                timestamp=int(time.time()),
                master_state=master_state,
                sequence=self._sequence
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return HeartbeatResult(
                success=True,
                latency_ms=latency_ms,
                slave_status=response
            )

        except Exception as e:
            return HeartbeatResult(
                success=False,
                error=str(e)
            )
```

### Slave Client Service

```python
# genmaster/app/services/slave_client.py
import httpx
from typing import Optional
from app.config import settings


class SlaveClient:
    """HTTP client for GenSlave API."""

    def __init__(self):
        self.base_url = settings.slave_api_url
        self.secret = settings.slave_api_secret
        self.timeout = settings.heartbeat_timeout_seconds

    def _get_headers(self) -> dict:
        return {
            "X-GenControl-Secret": self.secret,
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make HTTP request to GenSlave."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._get_headers(),
                **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def get_status(self) -> dict:
        """Get GenSlave status."""
        return await self._request("GET", "/api/status")

    async def relay_on(self) -> dict:
        """Turn relay on (start generator)."""
        return await self._request("POST", "/api/relay/on")

    async def relay_off(self) -> dict:
        """Turn relay off (stop generator)."""
        return await self._request("POST", "/api/relay/off")

    async def get_relay_state(self) -> bool:
        """Get current relay state."""
        response = await self._request("GET", "/api/relay/state")
        return response.get("state", False)

    async def heartbeat(
        self,
        timestamp: int,
        master_state: dict,
        sequence: int
    ) -> dict:
        """Send heartbeat to GenSlave."""
        return await self._request(
            "POST",
            "/api/heartbeat",
            json={
                "timestamp": timestamp,
                "master_state": master_state,
                "sequence": sequence
            }
        )

    async def get_system_health(self) -> dict:
        """Get GenSlave system health."""
        return await self._request("GET", "/api/system")

    async def push_config(self, config: dict) -> dict:
        """Push configuration to GenSlave."""
        return await self._request("POST", "/api/config", json=config)
```

### Webhook Service

```python
# genmaster/app/services/webhook.py
import httpx
import time
import hashlib
import hmac
from typing import Optional
from dataclasses import dataclass
from app.config import settings
from app.database import SessionLocal
from app.models import Config, EventLog


@dataclass
class WebhookResult:
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error: Optional[str] = None


class WebhookService:
    """Sends webhook notifications to n8n."""

    def __init__(self):
        self._sequence = 0

    def _get_config(self):
        """Get webhook config from database."""
        db = SessionLocal()
        try:
            config = Config.get_instance(db)
            return {
                "base_url": config.webhook_base_url,
                "secret": config.webhook_secret,
                "enabled": config.webhook_enabled
            }
        finally:
            db.close()

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Create HMAC signature for payload."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    async def send(self, event: str, data: dict) -> WebhookResult:
        """Send webhook notification."""
        config = self._get_config()

        if not config["enabled"] or not config["base_url"]:
            return WebhookResult(success=True)  # Skip if disabled

        self._sequence += 1
        timestamp = int(time.time())

        payload = {
            "event": event,
            "timestamp": timestamp,
            "source": "genmaster",
            "data": data,
            "meta": {
                "sequence": self._sequence,
                "version": "1.0.0"
            }
        }

        start_time = time.time()

        try:
            headers = {"Content-Type": "application/json"}

            # Add signature if secret configured
            if config["secret"]:
                import json
                signature = self._sign_payload(json.dumps(payload), config["secret"])
                headers["X-Webhook-Signature"] = signature

            async with httpx.AsyncClient(timeout=settings.webhook_timeout_seconds) as client:
                response = await client.post(
                    config["base_url"],
                    json=payload,
                    headers=headers
                )

            response_time_ms = int((time.time() - start_time) * 1000)

            # Log webhook send
            db = SessionLocal()
            try:
                EventLog.log(db, "WEBHOOK_SENT", {
                    "event": event,
                    "status_code": response.status_code,
                    "response_time_ms": response_time_ms
                })
            finally:
                db.close()

            return WebhookResult(
                success=response.is_success,
                status_code=response.status_code,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Log failure
            db = SessionLocal()
            try:
                EventLog.log(db, "WEBHOOK_FAILED", {
                    "event": event,
                    "error": str(e)
                }, severity="ERROR")
            finally:
                db.close()

            return WebhookResult(
                success=False,
                error=str(e)
            )

    async def send_test(self) -> WebhookResult:
        """Send test webhook."""
        return await self.send("test", {"message": "Test webhook from GenMaster"})
```

### Scheduler Service

```python
# genmaster/app/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from typing import Optional
from app.services.state_machine import StateMachine
from app.database import SessionLocal
from app.models import ScheduledRun


class SchedulerService:
    """Manages scheduled generator runs using APScheduler."""

    def __init__(self, state_machine: StateMachine):
        self.state_machine = state_machine
        self.scheduler = AsyncIOScheduler()
        self._auto_stop_jobs = {}  # run_id -> job_id

    def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        self._load_schedules()

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()

    def _load_schedules(self):
        """Load all enabled schedules from database."""
        db = SessionLocal()
        try:
            schedules = db.query(ScheduledRun).filter(
                ScheduledRun.enabled == True
            ).all()
            for schedule in schedules:
                self.add_schedule(schedule)
        finally:
            db.close()

    def add_schedule(self, schedule: ScheduledRun):
        """Add a schedule to the scheduler."""
        job_id = f"schedule_{schedule.id}"

        if schedule.recurring and schedule.recurrence_pattern:
            trigger = self._create_recurring_trigger(schedule)
        else:
            trigger = DateTrigger(
                run_date=datetime.fromtimestamp(schedule.scheduled_start)
            )

        self.scheduler.add_job(
            self._execute_scheduled_run,
            trigger=trigger,
            id=job_id,
            args=[schedule.id],
            replace_existing=True
        )

    def _create_recurring_trigger(self, schedule: ScheduledRun):
        """Create trigger for recurring schedule."""
        pattern = schedule.recurrence_pattern

        if pattern == "daily":
            dt = datetime.fromtimestamp(schedule.scheduled_start)
            return CronTrigger(hour=dt.hour, minute=dt.minute)
        elif pattern == "weekly":
            dt = datetime.fromtimestamp(schedule.scheduled_start)
            return CronTrigger(
                day_of_week=dt.weekday(),
                hour=dt.hour,
                minute=dt.minute
            )
        else:
            # Assume cron expression
            return CronTrigger.from_crontab(pattern)

    def update_schedule(self, schedule: ScheduledRun):
        """Update an existing schedule."""
        self.remove_schedule(schedule.id)
        if schedule.enabled:
            self.add_schedule(schedule)

    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from the scheduler."""
        job_id = f"schedule_{schedule_id}"
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass

    async def _execute_scheduled_run(self, schedule_id: int):
        """Execute a scheduled generator run."""
        db = SessionLocal()
        try:
            schedule = db.query(ScheduledRun).get(schedule_id)
            if not schedule or not schedule.enabled:
                return

            # Start generator
            try:
                await self.state_machine.start_generator(
                    trigger="scheduled",
                    duration_minutes=schedule.duration_minutes,
                    scheduled_run_id=schedule_id
                )

                # Update schedule stats
                schedule.last_executed = int(datetime.now().timestamp())
                schedule.execution_count += 1

                if schedule.recurring:
                    schedule.next_execution = self._calculate_next(schedule)
                else:
                    schedule.enabled = False  # One-time schedule

                db.commit()

            except Exception as e:
                from app.models import EventLog
                EventLog.log(db, "ERROR", {
                    "message": f"Scheduled run failed: {e}",
                    "schedule_id": schedule_id
                }, severity="ERROR")

        finally:
            db.close()

    def _calculate_next(self, schedule: ScheduledRun) -> Optional[int]:
        """Calculate next execution time for recurring schedule."""
        job_id = f"schedule_{schedule.id}"
        job = self.scheduler.get_job(job_id)
        if job and job.next_run_time:
            return int(job.next_run_time.timestamp())
        return None

    def schedule_auto_stop(self, run_id: int, duration_minutes: int):
        """Schedule automatic generator stop after duration."""
        from datetime import timedelta

        job_id = f"auto_stop_{run_id}"
        run_date = datetime.now() + timedelta(minutes=duration_minutes)

        self.scheduler.add_job(
            self._execute_auto_stop,
            DateTrigger(run_date=run_date),
            id=job_id,
            args=[run_id]
        )
        self._auto_stop_jobs[run_id] = job_id

    async def _execute_auto_stop(self, run_id: int):
        """Execute automatic generator stop."""
        try:
            await self.state_machine.stop_generator(reason="scheduled_end")
        except Exception:
            pass
        finally:
            self._auto_stop_jobs.pop(run_id, None)

    def cancel_auto_stop(self, run_id: int):
        """Cancel scheduled auto-stop."""
        job_id = self._auto_stop_jobs.get(run_id)
        if job_id:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
            self._auto_stop_jobs.pop(run_id, None)
```

---

## Utilities

### System Info

```python
# genmaster/app/utils/system_info.py
import psutil
from typing import Optional


def get_system_health() -> dict:
    """Get system health metrics."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # Memory
    memory = psutil.virtual_memory()
    ram_percent = memory.percent
    ram_used_mb = memory.used // (1024 * 1024)
    ram_total_mb = memory.total // (1024 * 1024)

    # Disk
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_used_gb = disk.used / (1024 ** 3)
    disk_total_gb = disk.total / (1024 ** 3)

    # Temperature (Raspberry Pi specific)
    temperature = get_cpu_temperature()

    # Uptime
    boot_time = psutil.boot_time()
    import time
    uptime_seconds = int(time.time() - boot_time)

    # Determine health status
    health_status = "good"
    if cpu_percent > 90 or ram_percent > 90 or disk_percent > 90:
        health_status = "critical"
    elif cpu_percent > 70 or ram_percent > 80 or disk_percent > 80:
        health_status = "warning"
    if temperature and temperature > 80:
        health_status = "critical"
    elif temperature and temperature > 70:
        health_status = "warning" if health_status == "good" else health_status

    return {
        "cpu_percent": round(cpu_percent, 1),
        "ram_percent": round(ram_percent, 1),
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "disk_percent": round(disk_percent, 1),
        "disk_used_gb": round(disk_used_gb, 2),
        "disk_total_gb": round(disk_total_gb, 2),
        "temperature_celsius": temperature,
        "uptime_seconds": uptime_seconds,
        "health_status": health_status
    }


def get_cpu_temperature() -> Optional[float]:
    """Get CPU temperature (Raspberry Pi)."""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
            return round(temp, 1)
    except Exception:
        return None
```

---

## Requirements

```
# genmaster/requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0                  # PostgreSQL async driver
psycopg2-binary>=2.9.9           # PostgreSQL sync driver for Alembic
alembic>=1.13.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
apscheduler>=3.10.0
gpiozero>=2.0
httpx>=0.26.0
psutil>=5.9.0
python-dotenv>=1.0.0
```

---

## Agent Implementation Checklist

- [ ] Create `app/config.py` with Pydantic settings
- [ ] Create `app/main.py` with FastAPI app and lifespan
- [ ] Create all Pydantic schemas in `app/schemas/`
- [ ] Create all routers in `app/routers/`
- [ ] Create `app/services/state_machine.py`
- [ ] Create `app/services/gpio_monitor.py`
- [ ] Create `app/services/heartbeat.py`
- [ ] Create `app/services/slave_client.py`
- [ ] Create `app/services/webhook.py`
- [ ] Create `app/services/scheduler.py`
- [ ] Create `app/services/backup.py`
- [ ] Create `app/utils/system_info.py`
- [ ] Create `app/utils/auth.py` for API key validation
- [ ] Create `app/repositories/` for data access
- [ ] Create `requirements.txt`
- [ ] Create `.env.example`
- [ ] Write tests for all services
- [ ] Write tests for all API endpoints
- [ ] Test GPIO monitoring with hardware
- [ ] Test heartbeat communication
- [ ] Test webhook delivery

---

## Related Documents

- `01-project-structure.md` - Conventions and patterns
- `02-database-schema.md` - Database models used here
- `04-genmaster-frontend.md` - Frontend consuming this API
- `05-genslave-backend.md` - GenSlave API this communicates with
