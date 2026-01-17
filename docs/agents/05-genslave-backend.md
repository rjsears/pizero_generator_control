# Agent Handoff: GenSlave Backend

## Purpose
This document provides complete specifications for building the GenSlave FastAPI backend, including relay control via Automation Hat Mini, LCD display management, heartbeat response, and failsafe logic.

---

## Overview

GenSlave is the secondary controller that:
1. Controls generator relay via Automation Hat Mini (GPIO16)
2. Displays status on built-in 0.96" LCD
3. Responds to commands from GenMaster
4. Monitors GenMaster heartbeats
5. Executes failsafe shutdown if communication lost

---

## Deployment Architecture

**IMPORTANT**: GenSlave runs **natively** (no Docker) on a Pi Zero 2W to maximize available RAM.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Deployment | Native Python | 512MB RAM constraint |
| Database | SQLite | ~0MB overhead vs 80-150MB for MariaDB |
| Web Server | Uvicorn direct | No nginx reverse proxy needed |
| Process Manager | systemd | Built-in, minimal overhead |
| Python | 3.11+ via pyenv | Latest features, consistent version |

### Memory Budget (Pi Zero 2W - 512MB)

| Component | Memory |
|-----------|--------|
| OS + System | ~100MB |
| Python + FastAPI + Uvicorn | ~50-80MB |
| SQLite (file-based) | ~0MB |
| Automation HAT libraries | ~10MB |
| **Total Used** | **~160-190MB** |
| **Available for Operations** | **~320-350MB** |

---

## Hardware

### Automation Hat Mini

| Feature | Specification |
|---------|---------------|
| Relay | 1x SPDT, 2A @ 24V max, GPIO16 |
| Display | 0.96" 160x80 IPS LCD (ST7735) |
| Analog Inputs | 3x 12-bit ADC (not used) |
| Digital Outputs | 3x sinking outputs (not used) |
| LED | 1x RGB status LED |

### Wiring

```
Generator Remote Start Terminal
        │
        ├─── Relay COM (Common)
        │
        ├─── Relay NO (Normally Open) ──► Generator Ground
        │
        └─── When relay closes, circuit completes, generator starts
```

---

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime (via pyenv) |
| FastAPI | 0.109+ | Web framework |
| Uvicorn | 0.27+ | ASGI server (direct, no nginx) |
| SQLAlchemy | 2.0+ | ORM (sync mode for SQLite) |
| SQLite | 3.x | Embedded database (file-based) |
| aiosqlite | 0.19+ | Async SQLite driver |
| automationhat | 0.4+ | HAT control library |
| Pillow | 10.0+ | LCD image generation |
| ST7735 | - | LCD driver (via automationhat) |
| httpx | 0.26+ | Async HTTP for webhooks |

---

## Project Structure

```
/opt/genslave/                   # Installation root
├── .env                         # Environment configuration
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── data/                        # Data directory
│   └── genslave.db             # SQLite database file
├── logs/                        # Application logs
│   └── genslave.log
└── app/
    ├── __init__.py
    ├── main.py                  # FastAPI app & lifespan
    ├── config.py                # Settings
    ├── database.py              # SQLite + SQLAlchemy setup
    ├── dependencies.py          # FastAPI dependencies
    ├── models/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── system_state.py
    │   └── config.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── relay.py
    │   ├── heartbeat.py
    │   └── system.py
    ├── routers/
    │   ├── __init__.py
    │   ├── relay.py
    │   ├── heartbeat.py
    │   ├── health.py
    │   ├── system.py
    │   └── config.py
    ├── services/
    │   ├── __init__.py
    │   ├── relay_control.py
    │   ├── lcd_display.py
    │   ├── heartbeat_monitor.py
    │   ├── failsafe.py
    │   └── webhook.py
    └── utils/
        ├── __init__.py
        ├── system_info.py
        ├── logging.py
        └── auth.py
```

---

## Main Application

```python
# genslave/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_database, ensure_default_records
from app.routers import relay, heartbeat, health, system, config as config_router
from app.services.relay_control import RelayControl
from app.services.lcd_display import LCDDisplay
from app.services.heartbeat_monitor import HeartbeatMonitor
from app.services.failsafe import FailsafeService

# Global service instances
relay_control: RelayControl = None
lcd_display: LCDDisplay = None
heartbeat_monitor: HeartbeatMonitor = None
failsafe_service: FailsafeService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global relay_control, lcd_display, heartbeat_monitor, failsafe_service

    print("Starting GenSlave services...")

    # Ensure directories exist
    settings.ensure_directories()

    # Initialize SQLite database (create tables if needed)
    init_database()
    ensure_default_records()

    # Initialize relay control
    relay_control = RelayControl()
    relay_control.initialize()

    # Initialize LCD display
    lcd_display = LCDDisplay()
    lcd_display.initialize()
    lcd_display.show_startup()

    # Initialize failsafe service
    failsafe_service = FailsafeService(relay_control, lcd_display)

    # Initialize heartbeat monitor
    heartbeat_monitor = HeartbeatMonitor(failsafe_service, lcd_display)
    await heartbeat_monitor.start()

    # Sync state from database
    await relay_control.sync_from_database()

    # Update LCD with current state
    lcd_display.update_status(
        relay_state=relay_control.get_state(),
        master_status="waiting",
        message="Ready"
    )

    yield

    # Shutdown
    print("Shutting down GenSlave services...")
    await heartbeat_monitor.stop()
    lcd_display.show_shutdown()
    relay_control.cleanup()


app = FastAPI(
    title="GenSlave API",
    description="Generator Control System - Slave Controller",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(relay.router, prefix="/api/relay", tags=["Relay"])
app.include_router(heartbeat.router, prefix="/api/heartbeat", tags=["Heartbeat"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(config_router.router, prefix="/api/config", tags=["Config"])


@app.get("/api/status")
async def get_status():
    """Get complete GenSlave status."""
    return {
        "relay_state": relay_control.get_state(),
        "relay_on_time": relay_control.get_on_time(),
        "master_connection": heartbeat_monitor.get_status(),
        "failsafe_triggered": failsafe_service.is_triggered(),
        "system": await get_system_info()
    }


async def get_system_info():
    from app.utils.system_info import get_system_health
    return get_system_health()


# Dependency accessors
def get_relay_control() -> RelayControl:
    return relay_control

def get_lcd_display() -> LCDDisplay:
    return lcd_display

def get_heartbeat_monitor() -> HeartbeatMonitor:
    return heartbeat_monitor

def get_failsafe_service() -> FailsafeService:
    return failsafe_service
```

---

## Configuration

```python
# genslave/app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    # Application
    app_env: str = "production"
    app_debug: bool = False
    app_secret_key: str = "change-me"

    # Database (SQLite - file-based, no server needed)
    database_path: str = "/opt/genslave/data/genslave.db"

    @property
    def database_url(self) -> str:
        """Generate SQLite database URL."""
        return f"sqlite+aiosqlite:///{self.database_path}"

    @property
    def sync_database_url(self) -> str:
        """Sync database URL for migrations/scripts."""
        return f"sqlite:///{self.database_path}"

    # API Authentication
    api_secret: str = "change-me"

    # Heartbeat (defaults, updated from GenMaster)
    heartbeat_interval_seconds: int = 60
    heartbeat_failure_threshold: int = 3

    # Webhook (for failsafe notifications)
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    # GenMaster (for reference)
    master_api_url: Optional[str] = None

    # Hardware
    MOCK_HAT_MODE: bool = False  # Set True for development without hardware

    # LCD
    lcd_enabled: bool = True
    lcd_brightness: int = 100

    # Logging
    log_path: str = "/opt/genslave/logs/genslave.log"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def ensure_directories(self):
        """Ensure data and log directories exist."""
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

---

## Database Setup (SQLite)

GenSlave uses SQLite for zero-overhead persistent storage. Unlike GenMaster which uses PostgreSQL with Alembic migrations, GenSlave creates tables directly on startup.

```python
# genslave/app/database.py
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from contextlib import asynccontextmanager
from pathlib import Path

from app.config import settings


# Ensure database directory exists
Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    # SQLite-specific: check_same_thread needed for async
    connect_args={"check_same_thread": False}
)

# Sync engine for table creation and direct operations
sync_engine = create_engine(
    settings.sync_database_url,
    echo=settings.app_debug,
    connect_args={"check_same_thread": False}
)


# Enable SQLite optimizations
@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Configure SQLite for better performance."""
    cursor = dbapi_connection.cursor()
    # Enable Write-Ahead Logging for better concurrent access
    cursor.execute("PRAGMA journal_mode=WAL")
    # Faster writes (data still safe due to WAL)
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Use more memory for better performance
    cursor.execute("PRAGMA cache_size=-8000")  # 8MB cache
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Sync session factory (for startup/shutdown)
SessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_async_session() -> AsyncSession:
    """Async context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_session() -> Session:
    """Get synchronous session for startup operations."""
    return SessionLocal()


# FastAPI dependency
async def get_db():
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def init_database():
    """Initialize database tables (called on first startup)."""
    from app.models.base import Base
    from app.models import system_state, config  # Import all models

    # Create all tables
    Base.metadata.create_all(bind=sync_engine)
    print(f"Database initialized at {settings.database_path}")


def ensure_default_records():
    """Ensure default configuration records exist."""
    from app.models.system_state import SystemState
    from app.models.config import Config

    db = SessionLocal()
    try:
        # Ensure SystemState singleton exists
        if not db.query(SystemState).first():
            db.add(SystemState())
            db.commit()
            print("Created default SystemState record")

        # Ensure Config singleton exists
        if not db.query(Config).first():
            db.add(Config())
            db.commit()
            print("Created default Config record")
    finally:
        db.close()
```

### SQLite Models (No Alembic)

GenSlave models are simplified and don't use Alembic migrations. Tables are created directly on startup.

```python
# genslave/app/models/base.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, DateTime, func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class TimestampMixin:
    """Mixin for created/updated timestamps."""
    created_at: Mapped[int] = mapped_column(Integer, default=lambda: int(__import__('time').time()))
    updated_at: Mapped[int] = mapped_column(
        Integer,
        default=lambda: int(__import__('time').time()),
        onupdate=lambda: int(__import__('time').time())
    )
```

```python
# genslave/app/models/system_state.py
from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.models.base import Base, TimestampMixin


class SystemState(Base, TimestampMixin):
    """Singleton table for system state persistence."""
    __tablename__ = "system_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Relay state
    relay_state: Mapped[bool] = mapped_column(Boolean, default=False)
    relay_on_time: Mapped[int] = mapped_column(Integer, nullable=True)
    relay_off_time: Mapped[int] = mapped_column(Integer, nullable=True)

    # Last command
    last_command: Mapped[str] = mapped_column(String(20), nullable=True)
    last_command_time: Mapped[int] = mapped_column(Integer, nullable=True)
    last_command_source: Mapped[str] = mapped_column(String(50), nullable=True)

    # Heartbeat tracking
    last_heartbeat_received: Mapped[int] = mapped_column(Integer, nullable=True)
    missed_heartbeat_count: Mapped[int] = mapped_column(Integer, default=0)
    master_connection_status: Mapped[str] = mapped_column(String(20), default="unknown")

    # Failsafe
    failsafe_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    failsafe_time: Mapped[int] = mapped_column(Integer, nullable=True)

    @classmethod
    def get_instance(cls, db: Session) -> "SystemState":
        """Get singleton instance, create if needed."""
        state = db.query(cls).first()
        if not state:
            state = cls(id=1)
            db.add(state)
            db.commit()
        return state
```

```python
# genslave/app/models/config.py
from sqlalchemy import Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.models.base import Base, TimestampMixin


class Config(Base, TimestampMixin):
    """Singleton table for configuration (pushed from GenMaster)."""
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # Heartbeat settings
    heartbeat_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    heartbeat_failure_threshold: Mapped[int] = mapped_column(Integer, default=3)

    # Webhook settings
    webhook_base_url: Mapped[str] = mapped_column(String(500), nullable=True)
    webhook_secret: Mapped[str] = mapped_column(String(100), nullable=True)

    # LCD settings
    lcd_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lcd_brightness: Mapped[int] = mapped_column(Integer, default=100)

    # GenMaster reference
    master_api_url: Mapped[str] = mapped_column(String(500), nullable=True)

    @classmethod
    def get_instance(cls, db: Session) -> "Config":
        """Get singleton instance, create if needed."""
        config = db.query(cls).first()
        if not config:
            config = cls(id=1)
            db.add(config)
            db.commit()
        return config
```

```python
# genslave/app/models/__init__.py
from app.models.base import Base, TimestampMixin
from app.models.system_state import SystemState
from app.models.config import Config

__all__ = ["Base", "TimestampMixin", "SystemState", "Config"]
```

---

## Pydantic Schemas

### Relay Schemas

```python
# genslave/app/schemas/relay.py
from pydantic import BaseModel
from typing import Optional


class RelayState(BaseModel):
    """Current relay state."""
    state: bool
    on_time: Optional[int] = None
    runtime_seconds: Optional[int] = None


class RelayCommandResponse(BaseModel):
    """Response after relay command."""
    success: bool
    state: bool
    message: str
```

### Heartbeat Schemas

```python
# genslave/app/schemas/heartbeat.py
from pydantic import BaseModel
from typing import Optional


class HeartbeatRequest(BaseModel):
    """Heartbeat from GenMaster."""
    timestamp: int
    generator_running: bool
    armed: bool           # Automation armed state from GenMaster
    command: str = "none" # Commands sent separately, not via heartbeat


class HeartbeatResponse(BaseModel):
    """Response to heartbeat."""
    timestamp: int
    slave_state: dict
    relay_state: bool
    armed: bool           # Echo back armed state for verification
    system_health: Optional[dict] = None


class HeartbeatStatus(BaseModel):
    """Heartbeat monitor status."""
    master_connected: bool
    last_heartbeat: Optional[int] = None
    last_heartbeat_ago_seconds: Optional[int] = None
    missed_count: int
```

### System Schemas

```python
# genslave/app/schemas/system.py
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
    health_status: str
```

---

## API Routers

### Relay Router

```python
# genslave/app/routers/relay.py
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.relay import RelayState, RelayCommandResponse
from app.services.relay_control import RelayControl
from app.services.lcd_display import LCDDisplay
from app.main import get_relay_control, get_lcd_display
from app.utils.auth import verify_api_key
from app.models import SystemState

router = APIRouter()


@router.get("/state", response_model=RelayState)
async def get_relay_state(
    relay: RelayControl = Depends(get_relay_control)
):
    """Get current relay state."""
    state = relay.get_state()
    on_time = relay.get_on_time()
    runtime = None

    if state and on_time:
        runtime = int(time.time()) - on_time

    return RelayState(
        state=state,
        on_time=on_time,
        runtime_seconds=runtime
    )


@router.post("/on", response_model=RelayCommandResponse, dependencies=[Depends(verify_api_key)])
async def relay_on(
    relay: RelayControl = Depends(get_relay_control),
    lcd: LCDDisplay = Depends(get_lcd_display),
    db: Session = Depends(get_db)
):
    """Turn relay ON (start generator)."""
    if relay.get_state():
        return RelayCommandResponse(
            success=True,
            state=True,
            message="Relay already ON"
        )

    success = relay.turn_on()

    if success:
        # Update database state
        state = SystemState.get_instance(db)
        state.relay_state = True
        state.relay_on_time = int(time.time())
        state.last_command = "on"
        state.last_command_time = int(time.time())
        state.last_command_source = "genmaster"
        db.commit()

        # Update LCD
        lcd.update_status(
            relay_state=True,
            master_status="connected",
            message="Generator Running"
        )

        return RelayCommandResponse(
            success=True,
            state=True,
            message="Relay turned ON"
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to turn relay ON")


@router.post("/off", response_model=RelayCommandResponse, dependencies=[Depends(verify_api_key)])
async def relay_off(
    relay: RelayControl = Depends(get_relay_control),
    lcd: LCDDisplay = Depends(get_lcd_display),
    db: Session = Depends(get_db)
):
    """Turn relay OFF (stop generator)."""
    if not relay.get_state():
        return RelayCommandResponse(
            success=True,
            state=False,
            message="Relay already OFF"
        )

    success = relay.turn_off()

    if success:
        # Update database state
        state = SystemState.get_instance(db)
        state.relay_state = False
        state.relay_off_time = int(time.time())
        state.last_command = "off"
        state.last_command_time = int(time.time())
        state.last_command_source = "genmaster"
        db.commit()

        # Update LCD
        lcd.update_status(
            relay_state=False,
            master_status="connected",
            message="Generator Stopped"
        )

        return RelayCommandResponse(
            success=True,
            state=False,
            message="Relay turned OFF"
        )
    else:
        raise HTTPException(status_code=500, detail="Failed to turn relay OFF")
```

### Heartbeat Router

```python
# genslave/app/routers/heartbeat.py
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.heartbeat import HeartbeatRequest, HeartbeatResponse, HeartbeatStatus
from app.services.relay_control import RelayControl
from app.services.heartbeat_monitor import HeartbeatMonitor
from app.services.lcd_display import LCDDisplay
from app.main import get_relay_control, get_heartbeat_monitor, get_lcd_display
from app.utils.auth import verify_api_key
from app.utils.system_info import get_system_health
from app.models import SystemState

router = APIRouter()


@router.post("", response_model=HeartbeatResponse, dependencies=[Depends(verify_api_key)])
async def receive_heartbeat(
    request: HeartbeatRequest,
    relay: RelayControl = Depends(get_relay_control),
    monitor: HeartbeatMonitor = Depends(get_heartbeat_monitor),
    lcd: LCDDisplay = Depends(get_lcd_display),
    db: Session = Depends(get_db)
):
    """Receive heartbeat from GenMaster."""
    current_time = int(time.time())

    # Update heartbeat monitor
    await monitor.record_heartbeat(request.timestamp, request.master_state)

    # Update database
    state = SystemState.get_instance(db)
    state.last_heartbeat_received = current_time
    state.missed_heartbeat_count = 0
    state.master_connection_status = "connected"
    db.commit()

    # Update LCD
    lcd.update_status(
        relay_state=relay.get_state(),
        master_status="connected",
        last_heartbeat=current_time
    )

    # Build response
    slave_state = {
        "relay_state": relay.get_state(),
        "relay_on_time": relay.get_on_time(),
        "failsafe_triggered": state.failsafe_triggered
    }

    return HeartbeatResponse(
        timestamp=current_time,
        slave_state=slave_state,
        relay_state=relay.get_state(),
        sequence_ack=request.sequence,
        system_health=get_system_health()
    )


@router.get("/status", response_model=HeartbeatStatus)
async def get_heartbeat_status(
    monitor: HeartbeatMonitor = Depends(get_heartbeat_monitor)
):
    """Get heartbeat monitor status."""
    return monitor.get_status()
```

### Health Router

```python
# genslave/app/routers/health.py
from fastapi import APIRouter, Depends
from app.services.heartbeat_monitor import HeartbeatMonitor
from app.main import get_heartbeat_monitor

router = APIRouter()


@router.get("")
async def health_check(
    monitor: HeartbeatMonitor = Depends(get_heartbeat_monitor)
):
    """Basic health check endpoint."""
    status = monitor.get_status()
    return {
        "status": "healthy",
        "master_connected": status["master_connected"],
        "relay_operational": True
    }
```

### System Router

```python
# genslave/app/routers/system.py
from fastapi import APIRouter
from app.schemas.system import SystemHealth
from app.utils.system_info import get_system_health

router = APIRouter()


@router.get("", response_model=SystemHealth)
async def get_system_status():
    """Get system health metrics."""
    return get_system_health()
```

### Config Router

```python
# genslave/app/routers/config.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import Config
from app.utils.auth import verify_api_key

router = APIRouter()


class ConfigPush(BaseModel):
    """Configuration pushed from GenMaster."""
    heartbeat_interval_seconds: Optional[int] = None
    heartbeat_failure_threshold: Optional[int] = None
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    master_api_url: Optional[str] = None


@router.post("", dependencies=[Depends(verify_api_key)])
async def receive_config(
    config_data: ConfigPush,
    db: Session = Depends(get_db)
):
    """Receive configuration update from GenMaster."""
    config = Config.get_instance(db)

    # Update provided fields
    update_data = config_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(config, key):
            setattr(config, key, value)

    db.commit()

    return {"message": "Configuration updated", "updated_fields": list(update_data.keys())}


@router.get("")
async def get_config(db: Session = Depends(get_db)):
    """Get current configuration."""
    config = Config.get_instance(db)
    return {
        "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
        "heartbeat_failure_threshold": config.heartbeat_failure_threshold,
        "lcd_enabled": config.lcd_enabled,
        "lcd_brightness": config.lcd_brightness
    }
```

---

## Services

### Relay Control Service

**IMPORTANT**: The Automation Hat Mini relay has **no state readback capability**. The `is_on()` method does not exist on the relay object. State must be tracked internally.

```python
# genslave/app/services/relay_control.py
import logging
import time
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import automationhat, fall back to mock if not available
# Detection is done by actually trying to use the relay, not is_automation_hat()
automationhat = None
HAT_AVAILABLE = False

if settings.MOCK_HAT_MODE:
    logger.info("Mock HAT mode enabled via configuration")
else:
    try:
        import automationhat as _automationhat
        try:
            # Try to use relay - this will fail if no hat connected
            # NOTE: is_automation_hat() doesn't work for Mini version
            _automationhat.relay.one.off()  # Ensure relay starts OFF
            automationhat = _automationhat
            HAT_AVAILABLE = True
            logger.info("Automation Hat Mini detected and initialized (relay test passed)")
        except Exception as e:
            logger.warning(f"automationhat library loaded but hardware test failed: {e}")
    except ImportError as e:
        logger.warning(f"automationhat library not available: {e}")


class RelayService:
    """
    Controls the Automation Hat Mini relay.

    IMPORTANT: Automation Hat Mini has no state readback capability.
    The relay state is tracked internally since there's no is_on() method.
    """

    def __init__(self):
        # Track state internally - hardware has no readback
        self._state: bool = False
        self._on_time: Optional[int] = None
        self._initialized: bool = False
        self._mock_mode: bool = not HAT_AVAILABLE

    def initialize(self) -> None:
        """Initialize relay - ensures OFF state on startup."""
        if HAT_AVAILABLE:
            try:
                automationhat.relay.one.off()
                logger.info("Relay initialized to OFF state")
            except Exception as e:
                logger.error(f"Failed to initialize relay: {e}")
                self._mock_mode = True

        self._state = False
        self._on_time = None
        self._initialized = True
        logger.info(f"RelayService initialized (mock_mode={self._mock_mode})")

    def turn_on(self) -> bool:
        """Turn relay ON (close contact to start generator)."""
        if not self._initialized:
            logger.error("RelayService not initialized")
            return False

        try:
            if HAT_AVAILABLE and not self._mock_mode:
                automationhat.relay.one.on()

            # Track state internally (no hardware readback)
            self._state = True
            self._on_time = int(time.time())
            logger.info("Relay turned ON")
            return True
        except Exception as e:
            logger.error(f"Failed to turn relay ON: {e}")
            return False

    def turn_off(self) -> bool:
        """Turn relay OFF (open contact to stop generator)."""
        if not self._initialized:
            logger.error("RelayService not initialized")
            return False

        try:
            if HAT_AVAILABLE and not self._mock_mode:
                automationhat.relay.one.off()

            # Track state internally (no hardware readback)
            self._state = False
            self._on_time = None
            logger.info("Relay turned OFF")
            return True
        except Exception as e:
            logger.error(f"Failed to turn relay OFF: {e}")
            return False

    def get_state(self) -> bool:
        """Get current relay state (from internal tracking)."""
        return self._state

    def get_on_time(self) -> Optional[int]:
        """Get timestamp when relay was turned ON."""
        return self._on_time if self._state else None

    def get_runtime_seconds(self) -> Optional[int]:
        """Get how long the relay has been ON."""
        if self._state and self._on_time:
            return int(time.time()) - self._on_time
        return None

    @property
    def is_mock_mode(self) -> bool:
        """Check if running in mock mode."""
        return self._mock_mode

    def cleanup(self) -> None:
        """Cleanup - ensure relay is OFF."""
        if self._initialized and HAT_AVAILABLE and not self._mock_mode:
            try:
                automationhat.relay.one.off()
            except Exception:
                pass
        self._state = False
        self._on_time = None
        self._initialized = False
        logger.info("RelayService cleaned up")
```

### LCD Display Service

```python
# genslave/app/services/lcd_display.py
import time
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

# Try to import display libraries
try:
    from ST7735 import ST7735
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    print("WARNING: ST7735 not available, LCD disabled")


class LCDDisplay:
    """Manages the Automation Hat Mini's 160x80 LCD display."""

    # Display dimensions
    WIDTH = 160
    HEIGHT = 80

    # Colors (RGB)
    COLOR_BG = (17, 24, 39)         # Dark gray background
    COLOR_TEXT = (249, 250, 251)    # White text
    COLOR_GREEN = (34, 197, 94)     # Running/connected
    COLOR_RED = (239, 68, 68)       # Stopped/error
    COLOR_AMBER = (245, 158, 11)    # Warning
    COLOR_GRAY = (107, 114, 128)    # Inactive

    def __init__(self):
        self._display = None
        self._enabled = settings.lcd_enabled
        self._last_update = 0
        self._current_state = {}

    def initialize(self):
        """Initialize LCD display."""
        if not self._enabled or not DISPLAY_AVAILABLE:
            print("LCD display disabled or unavailable")
            return

        try:
            self._display = ST7735(
                port=0,
                cs=1,
                dc=9,
                backlight=13,
                rotation=270,
                spi_speed_hz=10000000
            )
            self._display.set_backlight(settings.lcd_brightness / 100.0)
            print("LCD display initialized")
        except Exception as e:
            print(f"Failed to initialize LCD: {e}")
            self._enabled = False

    def _create_image(self) -> tuple:
        """Create a new image and draw object."""
        image = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLOR_BG)
        draw = ImageDraw.Draw(image)
        return image, draw

    def _get_font(self, size: int = 12):
        """Get font, fallback to default if custom font not available."""
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
        except:
            return ImageFont.load_default()

    def show_startup(self):
        """Show startup screen."""
        if not self._enabled or not self._display:
            return

        image, draw = self._create_image()
        font_large = self._get_font(16)
        font_small = self._get_font(10)

        # Center text
        draw.text((self.WIDTH // 2, 25), "GenSlave", fill=self.COLOR_GREEN,
                  font=font_large, anchor="mm")
        draw.text((self.WIDTH // 2, 50), "Starting...", fill=self.COLOR_GRAY,
                  font=font_small, anchor="mm")

        self._display.display(image)

    def show_shutdown(self):
        """Show shutdown screen."""
        if not self._enabled or not self._display:
            return

        image, draw = self._create_image()
        font = self._get_font(14)

        draw.text((self.WIDTH // 2, self.HEIGHT // 2), "Shutting Down",
                  fill=self.COLOR_AMBER, font=font, anchor="mm")

        self._display.display(image)

    def update_status(
        self,
        relay_state: bool,
        master_status: str = "unknown",
        message: str = "",
        last_heartbeat: Optional[int] = None
    ):
        """Update display with current status."""
        if not self._enabled or not self._display:
            return

        # Throttle updates to max 2 per second
        now = time.time()
        if now - self._last_update < 0.5:
            return
        self._last_update = now

        image, draw = self._create_image()
        font_large = self._get_font(18)
        font_medium = self._get_font(12)
        font_small = self._get_font(10)

        # Relay status (top)
        relay_color = self.COLOR_GREEN if relay_state else self.COLOR_GRAY
        relay_text = "RUNNING" if relay_state else "STOPPED"
        draw.text((self.WIDTH // 2, 18), relay_text, fill=relay_color,
                  font=font_large, anchor="mm")

        # Divider line
        draw.line([(10, 35), (self.WIDTH - 10, 35)], fill=self.COLOR_GRAY, width=1)

        # Master connection status
        if master_status == "connected":
            status_color = self.COLOR_GREEN
            status_text = "Master: OK"
        elif master_status == "disconnected":
            status_color = self.COLOR_RED
            status_text = "Master: LOST"
        else:
            status_color = self.COLOR_AMBER
            status_text = "Master: ?"

        draw.text((10, 45), status_text, fill=status_color, font=font_medium)

        # Last heartbeat
        if last_heartbeat:
            ago = int(time.time()) - last_heartbeat
            hb_text = f"HB: {ago}s ago"
            draw.text((self.WIDTH - 10, 45), hb_text, fill=self.COLOR_GRAY,
                      font=font_small, anchor="ra")

        # Message (bottom)
        if message:
            draw.text((self.WIDTH // 2, 68), message[:20], fill=self.COLOR_TEXT,
                      font=font_small, anchor="mm")

        self._display.display(image)

        # Store current state
        self._current_state = {
            "relay_state": relay_state,
            "master_status": master_status,
            "message": message
        }

    def show_failsafe(self):
        """Show failsafe triggered screen."""
        if not self._enabled or not self._display:
            return

        image, draw = self._create_image()
        font_large = self._get_font(16)
        font_small = self._get_font(10)

        # Warning colors
        draw.rectangle([(0, 0), (self.WIDTH, self.HEIGHT)], fill=(50, 0, 0))

        draw.text((self.WIDTH // 2, 25), "FAILSAFE", fill=self.COLOR_RED,
                  font=font_large, anchor="mm")
        draw.text((self.WIDTH // 2, 45), "COMM LOST", fill=self.COLOR_RED,
                  font=font_large, anchor="mm")
        draw.text((self.WIDTH // 2, 65), "Generator Stopped", fill=self.COLOR_AMBER,
                  font=font_small, anchor="mm")

        self._display.display(image)

    def show_error(self, error_msg: str):
        """Show error screen."""
        if not self._enabled or not self._display:
            return

        image, draw = self._create_image()
        font = self._get_font(12)

        draw.text((self.WIDTH // 2, 30), "ERROR", fill=self.COLOR_RED,
                  font=font, anchor="mm")
        draw.text((self.WIDTH // 2, 50), error_msg[:18], fill=self.COLOR_TEXT,
                  font=font, anchor="mm")

        self._display.display(image)

    def set_brightness(self, percent: int):
        """Set display brightness (0-100)."""
        if self._display:
            self._display.set_backlight(max(0, min(100, percent)) / 100.0)
```

### Heartbeat Monitor Service

```python
# genslave/app/services/heartbeat_monitor.py
import asyncio
import time
from typing import Optional
from dataclasses import dataclass

from app.database import SessionLocal
from app.models import SystemState, Config
from app.services.failsafe import FailsafeService
from app.services.lcd_display import LCDDisplay


@dataclass
class HeartbeatInfo:
    last_received: Optional[int] = None
    missed_count: int = 0
    master_state: Optional[dict] = None


class HeartbeatMonitor:
    """Monitors heartbeats from GenMaster."""

    def __init__(self, failsafe: FailsafeService, lcd: LCDDisplay):
        self.failsafe = failsafe
        self.lcd = lcd
        self._info = HeartbeatInfo()
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start heartbeat monitoring."""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print("Heartbeat monitor started")

    async def stop(self):
        """Stop heartbeat monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("Heartbeat monitor stopped")

    async def record_heartbeat(self, timestamp: int, master_state: dict):
        """Record received heartbeat."""
        self._info.last_received = int(time.time())
        self._info.missed_count = 0
        self._info.master_state = master_state

        # Clear failsafe if it was triggered
        if self.failsafe.is_triggered():
            await self.failsafe.clear()

    def get_status(self) -> dict:
        """Get heartbeat monitor status."""
        last_ago = None
        if self._info.last_received:
            last_ago = int(time.time()) - self._info.last_received

        return {
            "master_connected": self._info.missed_count == 0 and self._info.last_received is not None,
            "last_heartbeat": self._info.last_received,
            "last_heartbeat_ago_seconds": last_ago,
            "missed_count": self._info.missed_count
        }

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            # Get config from database
            db = SessionLocal()
            try:
                config = Config.get_instance(db)
                interval = config.heartbeat_interval_seconds
                threshold = config.heartbeat_failure_threshold
            finally:
                db.close()

            # Check for missed heartbeat
            if self._info.last_received:
                elapsed = int(time.time()) - self._info.last_received

                # If more than 1.5x interval has passed, count as missed
                if elapsed > interval * 1.5:
                    await self._handle_missed_heartbeat(threshold)

            # Wait for next check (check slightly more frequently than interval)
            await asyncio.sleep(interval * 0.75)

    async def _handle_missed_heartbeat(self, threshold: int):
        """Handle a missed heartbeat."""
        self._info.missed_count += 1
        print(f"Missed heartbeat #{self._info.missed_count}")

        # Update database
        db = SessionLocal()
        try:
            state = SystemState.get_instance(db)
            state.missed_heartbeat_count = self._info.missed_count

            if self._info.missed_count >= threshold:
                state.master_connection_status = "disconnected"
            db.commit()
        finally:
            db.close()

        # Update LCD
        self.lcd.update_status(
            relay_state=False,  # Will be updated by failsafe if triggered
            master_status="disconnected" if self._info.missed_count >= threshold else "warning",
            message=f"Missed HB: {self._info.missed_count}"
        )

        # Trigger failsafe if threshold reached
        if self._info.missed_count >= threshold:
            await self.failsafe.trigger()
```

### Failsafe Service

```python
# genslave/app/services/failsafe.py
import time
from app.database import SessionLocal
from app.models import SystemState
from app.services.relay_control import RelayControl
from app.services.lcd_display import LCDDisplay
from app.services.webhook import send_failsafe_webhook


class FailsafeService:
    """Handles failsafe shutdown when communication is lost."""

    def __init__(self, relay: RelayControl, lcd: LCDDisplay):
        self.relay = relay
        self.lcd = lcd
        self._triggered = False
        self._trigger_time: int = None

    def is_triggered(self) -> bool:
        """Check if failsafe has been triggered."""
        return self._triggered

    async def trigger(self):
        """Trigger failsafe - stop generator immediately."""
        if self._triggered:
            return  # Already triggered

        print("FAILSAFE TRIGGERED - Stopping generator")
        self._triggered = True
        self._trigger_time = int(time.time())

        # Stop the generator
        was_running = self.relay.get_state()
        self.relay.turn_off()

        # Update database
        db = SessionLocal()
        try:
            state = SystemState.get_instance(db)
            state.relay_state = False
            state.failsafe_triggered = True
            state.failsafe_time = self._trigger_time
            state.master_connection_status = "disconnected"
            db.commit()
        finally:
            db.close()

        # Update LCD
        self.lcd.show_failsafe()

        # Send webhook notification
        await send_failsafe_webhook(was_running)

    async def clear(self):
        """Clear failsafe state when communication is restored."""
        if not self._triggered:
            return

        print("Failsafe cleared - communication restored")
        self._triggered = False
        self._trigger_time = None

        # Update database
        db = SessionLocal()
        try:
            state = SystemState.get_instance(db)
            state.failsafe_triggered = False
            state.failsafe_time = None
            state.master_connection_status = "connected"
            db.commit()
        finally:
            db.close()

        # LCD will be updated by normal status update
```

### Webhook Service

```python
# genslave/app/services/webhook.py
import httpx
import time
import hashlib
import hmac
from typing import Optional

from app.database import SessionLocal
from app.models import Config


async def send_failsafe_webhook(was_running: bool):
    """Send webhook notification when failsafe is triggered."""
    db = SessionLocal()
    try:
        config = Config.get_instance(db)
        webhook_url = config.webhook_base_url
        webhook_secret = config.webhook_secret

        if not webhook_url:
            print("No webhook URL configured, skipping notification")
            return
    finally:
        db.close()

    payload = {
        "event": "generator.stopped.comm_loss",
        "timestamp": int(time.time()),
        "source": "genslave",
        "data": {
            "generator_state": "stopped",
            "reason": "communication_loss",
            "was_running": was_running,
            "failsafe_triggered": True
        },
        "meta": {
            "version": "1.0.0"
        }
    }

    headers = {"Content-Type": "application/json"}

    # Add signature if secret configured
    if webhook_secret:
        import json
        signature = hmac.new(
            webhook_secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = signature

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(webhook_url, json=payload, headers=headers)
            print(f"Failsafe webhook sent: {response.status_code}")
    except Exception as e:
        print(f"Failed to send failsafe webhook: {e}")
```

---

## Utilities

### Authentication

```python
# genslave/app/utils/auth.py
from fastapi import Header, HTTPException
from app.config import settings


async def verify_api_key(
    x_gencontrol_secret: str = Header(..., alias="X-GenControl-Secret")
) -> bool:
    """Verify API key from request header."""
    if x_gencontrol_secret != settings.api_secret:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True
```

### System Info

```python
# genslave/app/utils/system_info.py
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

    # Temperature
    temperature = get_cpu_temperature()

    # Uptime
    import time
    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)

    # Health status
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

## Database Models

See `02-database-schema.md` for complete GenSlave database schema.

The GenSlave uses simpler tables:
- `system_state` - Relay state, heartbeat tracking, failsafe status
- `config` - Settings pushed from GenMaster

---

## Requirements

```
# /opt/genslave/requirements.txt
# Core Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database (SQLite - no external server needed)
sqlalchemy>=2.0.0
aiosqlite>=0.19.0

# Data Validation
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Hardware Control (Automation Hat Mini)
automationhat>=0.4.0
RPi.GPIO>=0.7.0
spidev>=3.5

# LCD Display
Pillow>=10.0.0
ST7735>=0.0.4

# HTTP Client (for webhooks)
httpx>=0.26.0

# System Monitoring
psutil>=5.9.0

# Configuration
python-dotenv>=1.0.0
```

### Development Requirements (Optional)

```
# /opt/genslave/requirements-dev.txt
# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0

# Type checking
mypy>=1.7.0

# Linting
ruff>=0.1.0
```

---

## Hardware Testing

### Test Relay

**IMPORTANT**: The Automation Hat Mini relay has **no `is_on()` method** for state readback. You must listen for the relay click or use a multimeter to verify.

```python
# test_relay.py - Run on Pi Zero with Automation Hat Mini
import automationhat
import time

print("Testing relay on Automation Hat Mini...")
print("NOTE: No state readback available - listen for relay click!")

print("\nTurning ON... (listen for click)")
automationhat.relay.one.on()
time.sleep(2)

print("Turning OFF... (listen for click)")
automationhat.relay.one.off()
time.sleep(1)

print("\nCycling 3 times...")
for i in range(3):
    print(f"  Cycle {i+1}: ON")
    automationhat.relay.one.on()
    time.sleep(0.5)
    print(f"  Cycle {i+1}: OFF")
    automationhat.relay.one.off()
    time.sleep(0.5)

print("\nTest complete!")
print("If you heard clicks, the relay is working correctly.")
```

### Test LCD

```python
# test_lcd.py - Run on Pi Zero with Automation Hat Mini
from PIL import Image, ImageDraw, ImageFont
from ST7735 import ST7735

display = ST7735(
    port=0,
    cs=1,
    dc=9,
    backlight=13,
    rotation=270,
    spi_speed_hz=10000000
)

display.set_backlight(1)

image = Image.new('RGB', (160, 80), (0, 0, 0))
draw = ImageDraw.Draw(image)

draw.text((80, 40), "GenSlave Test", fill=(255, 255, 255), anchor="mm")

display.display(image)

print("LCD test complete - check display")
```

---

## Native Installation

GenSlave runs natively (no Docker) to conserve RAM on the Pi Zero 2W.

### Directory Structure

```bash
# Create installation directories
sudo mkdir -p /opt/genslave/{app,data,logs}
sudo chown -R pi:pi /opt/genslave

# Create Python virtual environment
python3 -m venv /opt/genslave/venv
source /opt/genslave/venv/bin/activate

# Install dependencies
pip install -r /opt/genslave/requirements.txt
```

### Environment Configuration

```bash
# /opt/genslave/.env
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Database (auto-created, no configuration needed)
DATABASE_PATH=/opt/genslave/data/genslave.db

# API Authentication (must match GenMaster)
API_SECRET=<shared-secret-with-genmaster>

# Heartbeat defaults (can be updated by GenMaster)
HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# Webhook (optional, for failsafe notifications)
WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
WEBHOOK_SECRET=<webhook-secret>

# GenMaster reference
MASTER_API_URL=http://genmaster:8000

# LCD Display
LCD_ENABLED=true
LCD_BRIGHTNESS=100

# Logging
LOG_PATH=/opt/genslave/logs/genslave.log
LOG_LEVEL=INFO
```

### .env.example Template

```bash
# /opt/genslave/.env.example
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=change-me-generate-with-openssl

DATABASE_PATH=/opt/genslave/data/genslave.db

API_SECRET=change-me-must-match-genmaster

HEARTBEAT_INTERVAL_SECONDS=60
HEARTBEAT_FAILURE_THRESHOLD=3

# WEBHOOK_BASE_URL=http://n8n:5678/webhook/generator
# WEBHOOK_SECRET=

# MASTER_API_URL=http://genmaster:8000

LCD_ENABLED=true
LCD_BRIGHTNESS=100

LOG_PATH=/opt/genslave/logs/genslave.log
LOG_LEVEL=INFO
```

---

## Boot Behavior / Power Loss Recovery

GenSlave follows a "fail-safe on boot" philosophy. After any power loss or unexpected reboot:

### Startup Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│                    GenSlave Boot Sequence                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. systemd starts genslave.service                            │
│                                                                 │
│  2. RelayService.initialize()                                  │
│     └─► Relay forced OFF (safety)                              │
│     └─► State tracked internally (no hardware readback)        │
│                                                                 │
│  3. FailsafeService initializes                                │
│     └─► failsafe_triggered = False                             │
│                                                                 │
│  4. HeartbeatMonitor starts                                    │
│     └─► Waits for first heartbeat from GenMaster               │
│                                                                 │
│  5. First heartbeat received                                   │
│     └─► GenSlave sends relay_state=False to GenMaster          │
│     └─► GenMaster reconciles state                             │
│     └─► If automation is armed, GenMaster may send relay ON    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Safety Behaviors

| Scenario | GenSlave Behavior |
|----------|-------------------|
| Power loss while relay ON | Relay returns to OFF (hardware default), state reset |
| GenMaster heartbeat lost | Failsafe triggers → relay forced OFF |
| Both devices reboot | Both start with relay OFF, GenMaster re-arms if needed |
| GenSlave reboots, GenMaster running | GenMaster sends armed state, GenSlave responds |

### No State Restoration

Unlike GenMaster, GenSlave does **NOT** restore relay state from database on boot. This is intentional:

1. **Hardware state is authoritative** - On power loss, relay physically opens (OFF)
2. **GenMaster is source of truth** - Only GenMaster decides when to start generator
3. **Fail-safe principle** - Generator should never auto-start without explicit command

---

## Systemd Service

**NOTE**: GenSlave runs on port **8001** (GenMaster runs on 8000).

```ini
# /etc/systemd/system/genslave.service
[Unit]
Description=GenSlave Generator Controller
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/genslave
Environment="PATH=/opt/genslave/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/genslave/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

# Resource limits for Pi Zero 2W
MemoryMax=200M
MemoryHigh=150M

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/opt/genslave/data /opt/genslave/logs

# GPIO access
SupplementaryGroups=gpio i2c spi

# Logging
StandardOutput=append:/opt/genslave/logs/genslave.log
StandardError=append:/opt/genslave/logs/genslave.log

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable genslave

# Start service
sudo systemctl start genslave

# Check status
sudo systemctl status genslave

# View logs
journalctl -u genslave -f
# Or:
tail -f /opt/genslave/logs/genslave.log
```

---

## Log Rotation

```bash
# /etc/logrotate.d/genslave
/opt/genslave/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 pi pi
    postrotate
        systemctl restart genslave > /dev/null 2>&1 || true
    endscript
}
```

---

## Tailscale Integration

GenSlave connects to GenMaster via Tailscale VPN.

```bash
# Install Tailscale (native, not Docker)
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate with auth key
sudo tailscale up --authkey=tskey-auth-xxxxx --hostname=genslave

# Verify connection
tailscale status
tailscale ping genmaster
```

### Configure GenMaster URL

Once Tailscale is running, update the MASTER_API_URL to use the Tailscale hostname:

```bash
# /opt/genslave/.env
MASTER_API_URL=http://genmaster:8000
```

---

## Database Backup

SQLite database can be backed up with a simple file copy:

```bash
# Manual backup
cp /opt/genslave/data/genslave.db /opt/genslave/data/genslave.db.backup

# Automated backup script
#!/bin/bash
# /opt/genslave/backup.sh
BACKUP_DIR="/opt/genslave/backups"
mkdir -p "$BACKUP_DIR"
cp /opt/genslave/data/genslave.db "$BACKUP_DIR/genslave-$(date +%Y%m%d-%H%M%S).db"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/genslave-*.db | tail -n +8 | xargs -r rm
```

Add to crontab:
```bash
# Backup daily at 2am
0 2 * * * /opt/genslave/backup.sh
```

---

## Health Check Script

```bash
#!/bin/bash
# /opt/genslave/health-check.sh

set -e

echo "=== GenSlave Health Check ==="

# Check service status
if systemctl is-active --quiet genslave; then
    echo "✓ Service: running"
else
    echo "✗ Service: not running"
    exit 1
fi

# Check API health
if curl -s http://localhost:8001/api/health | grep -q "healthy"; then
    echo "✓ API: healthy"
else
    echo "✗ API: not responding"
    exit 1
fi

# Check database
if [ -f /opt/genslave/data/genslave.db ]; then
    DB_SIZE=$(du -h /opt/genslave/data/genslave.db | cut -f1)
    echo "✓ Database: $DB_SIZE"
else
    echo "✗ Database: missing"
    exit 1
fi

# Check memory usage
MEM_USED=$(free -m | awk 'NR==2{printf "%.0f%%", $3*100/$2}')
echo "• Memory: $MEM_USED"

# Check Tailscale
if tailscale status &>/dev/null; then
    echo "✓ Tailscale: connected"
else
    echo "✗ Tailscale: not connected"
fi

echo "=== Health Check Complete ==="
```

---

## Agent Implementation Checklist

### Phase 1: Core Setup
- [ ] Create `/opt/genslave/` directory structure
- [ ] Create `requirements.txt`
- [ ] Create `.env.example`
- [ ] Create `app/config.py` with settings
- [ ] Create `app/database.py` with SQLite setup
- [ ] Create database models in `app/models/`
- [ ] Test SQLite database initialization

### Phase 2: API Implementation
- [ ] Create `app/main.py` with FastAPI app and lifespan
- [ ] Create Pydantic schemas in `app/schemas/`
- [ ] Create all routers in `app/routers/`
- [ ] Create `app/utils/auth.py`
- [ ] Create `app/utils/system_info.py`
- [ ] Test API endpoints (without hardware)

### Phase 3: Hardware Services
- [ ] Create `app/services/relay_control.py`
- [ ] Create `app/services/lcd_display.py`
- [ ] Test relay hardware control
- [ ] Test LCD display

### Phase 4: Communication Services
- [ ] Create `app/services/heartbeat_monitor.py`
- [ ] Create `app/services/failsafe.py`
- [ ] Create `app/services/webhook.py`
- [ ] Test heartbeat monitoring
- [ ] Test failsafe trigger
- [ ] Test webhook notifications

### Phase 5: Deployment
- [ ] Create systemd service file
- [ ] Configure log rotation
- [ ] Test service startup/restart
- [ ] Install and configure Tailscale
- [ ] Test GenMaster ↔ GenSlave connectivity
- [ ] Create backup script
- [ ] Create health check script

---

## Related Documents

- `01-project-structure.md` - Conventions and patterns
- `02-database-schema.md` - GenSlave database tables (SQLite section)
- `03-genmaster-backend.md` - GenMaster that sends commands
- `08-setup-scripts.md` - GenSlave setup automation
