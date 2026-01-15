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
| Python | 3.11+ | Runtime |
| FastAPI | 0.109+ | Web framework |
| Uvicorn | 0.27+ | ASGI server |
| SQLAlchemy | 2.0+ | ORM |
| automationhat | 0.4+ | HAT control library |
| Pillow | 10.0+ | LCD image generation |
| ST7735 | - | LCD driver (via automationhat) |
| httpx | 0.26+ | Async HTTP for webhooks |

---

## Project Structure

```
genslave/app/
├── __init__.py
├── main.py              # FastAPI app & lifespan
├── config.py            # Settings
├── database.py          # SQLAlchemy setup
├── dependencies.py      # FastAPI dependencies
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


class Settings(BaseSettings):
    # Application
    app_env: str = "production"
    app_debug: bool = False
    app_secret_key: str = "change-me"

    # Database
    database_url: str = "mysql+pymysql://genslave:password@db:3306/genslave"

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

    # LCD
    lcd_enabled: bool = True
    lcd_brightness: int = 100

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
    master_state: dict
    sequence: int


class HeartbeatResponse(BaseModel):
    """Response to heartbeat."""
    timestamp: int
    slave_state: dict
    relay_state: bool
    sequence_ack: int
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

```python
# genslave/app/services/relay_control.py
import time
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import SystemState

# Try to import automationhat, fallback for development
try:
    import automationhat
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("WARNING: automationhat not available, running in simulation mode")


class RelayControl:
    """Controls the Automation Hat Mini relay."""

    def __init__(self):
        self._state: bool = False
        self._on_time: Optional[int] = None
        self._initialized: bool = False

    def initialize(self):
        """Initialize relay hardware."""
        if HARDWARE_AVAILABLE:
            # Small delay for HAT initialization
            time.sleep(0.1)

            # Ensure relay is OFF on startup
            automationhat.relay.one.off()

        self._state = False
        self._initialized = True
        print("Relay control initialized")

    def cleanup(self):
        """Cleanup on shutdown."""
        if HARDWARE_AVAILABLE and self._initialized:
            # Ensure relay is OFF
            automationhat.relay.one.off()
        self._initialized = False

    async def sync_from_database(self):
        """Sync relay state from database on startup."""
        db = SessionLocal()
        try:
            state = SystemState.get_instance(db)

            # Check if relay was ON before restart
            if state.relay_state:
                # Check how long ago it was turned on
                if state.relay_on_time:
                    elapsed = int(time.time()) - state.relay_on_time
                    # If it's been less than 5 minutes, restore state
                    if elapsed < 300:
                        print(f"Restoring relay state: ON (was on for {elapsed}s)")
                        self.turn_on()
                        self._on_time = state.relay_on_time
                    else:
                        # Too long ago, assume it should be off
                        print("Relay was ON but too long ago, keeping OFF")
                        state.relay_state = False
                        state.relay_on_time = None
                        db.commit()
        finally:
            db.close()

    def turn_on(self) -> bool:
        """Turn relay ON (close contact)."""
        if not self._initialized:
            return False

        try:
            if HARDWARE_AVAILABLE:
                automationhat.relay.one.on()
                # Verify state
                self._state = automationhat.relay.one.is_on()
            else:
                self._state = True

            if self._state:
                self._on_time = int(time.time())

            return self._state
        except Exception as e:
            print(f"Error turning relay ON: {e}")
            return False

    def turn_off(self) -> bool:
        """Turn relay OFF (open contact)."""
        if not self._initialized:
            return False

        try:
            if HARDWARE_AVAILABLE:
                automationhat.relay.one.off()
                # Verify state
                self._state = automationhat.relay.one.is_on()
            else:
                self._state = False

            if not self._state:
                self._on_time = None

            return not self._state  # Return True if successfully OFF
        except Exception as e:
            print(f"Error turning relay OFF: {e}")
            return False

    def get_state(self) -> bool:
        """Get current relay state."""
        if HARDWARE_AVAILABLE and self._initialized:
            try:
                self._state = automationhat.relay.one.is_on()
            except Exception:
                pass
        return self._state

    def get_on_time(self) -> Optional[int]:
        """Get timestamp when relay was turned on."""
        return self._on_time if self._state else None

    def get_runtime_seconds(self) -> Optional[int]:
        """Get runtime in seconds if relay is on."""
        if self._state and self._on_time:
            return int(time.time()) - self._on_time
        return None
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
# genslave/requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
pymysql>=1.1.0
alembic>=1.13.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
automationhat>=0.4.0
Pillow>=10.0.0
ST7735>=0.0.4
httpx>=0.26.0
psutil>=5.9.0
python-dotenv>=1.0.0
RPi.GPIO>=0.7.0
spidev>=3.5
```

---

## Hardware Testing

### Test Relay

```python
# test_relay.py - Run on Pi Zero with Automation Hat Mini
import automationhat
import time

print("Testing relay...")
print(f"Initial state: {automationhat.relay.one.is_on()}")

print("Turning ON...")
automationhat.relay.one.on()
time.sleep(1)
print(f"State after ON: {automationhat.relay.one.is_on()}")

print("Turning OFF...")
automationhat.relay.one.off()
time.sleep(1)
print(f"State after OFF: {automationhat.relay.one.is_on()}")

print("Test complete!")
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

## Agent Implementation Checklist

- [ ] Create `app/config.py` with settings
- [ ] Create `app/main.py` with FastAPI app and lifespan
- [ ] Create database models in `app/models/`
- [ ] Create Pydantic schemas in `app/schemas/`
- [ ] Create all routers in `app/routers/`
- [ ] Create `app/services/relay_control.py`
- [ ] Create `app/services/lcd_display.py`
- [ ] Create `app/services/heartbeat_monitor.py`
- [ ] Create `app/services/failsafe.py`
- [ ] Create `app/services/webhook.py`
- [ ] Create `app/utils/auth.py`
- [ ] Create `app/utils/system_info.py`
- [ ] Create `requirements.txt`
- [ ] Create `.env.example`
- [ ] Set up Alembic migrations
- [ ] Test relay hardware control
- [ ] Test LCD display
- [ ] Test heartbeat monitoring
- [ ] Test failsafe trigger
- [ ] Test API authentication

---

## Related Documents

- `01-project-structure.md` - Conventions and patterns
- `02-database-schema.md` - GenSlave database tables
- `03-genmaster-backend.md` - GenMaster that sends commands
- `06-docker-infrastructure.md` - Container configuration
