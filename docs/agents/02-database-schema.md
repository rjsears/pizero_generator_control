# Agent Handoff: Database Schema & Models

## Purpose
This document defines the complete database schema for both GenMaster and GenSlave, including SQLAlchemy models, Alembic migrations, and data access patterns.

---

## Database Technology

| Component | Technology |
|-----------|------------|
| Database | MariaDB 10.11 |
| ORM | SQLAlchemy 2.0+ |
| Migrations | Alembic |
| Driver | PyMySQL |

**Why MariaDB over SQLite?**
- Better concurrent access handling
- Built-in replication capabilities (future)
- More robust for continuous operation
- Configurable write buffering (SSD longevity)

---

## GenMaster Database Schema

### Entity Relationship Diagram

```
┌─────────────────────┐     ┌─────────────────────┐
│    system_state     │     │       config        │
│   (single row)      │     │   (single row)      │
├─────────────────────┤     ├─────────────────────┤
│ id = 1 (always)     │     │ id = 1 (always)     │
│ generator_running   │     │ heartbeat_interval  │
│ generator_start_time│     │ failure_threshold   │
│ run_trigger         │     │ webhook_base_url    │
│ override_enabled    │     │ slave_api_url       │
│ victron_signal_state│     │ ...                 │
│ heartbeat_status    │     └─────────────────────┘
│ ...                 │
└─────────────────────┘
           │
           │ References current run
           ▼
┌─────────────────────┐     ┌─────────────────────┐
│   generator_runs    │     │   scheduled_runs    │
├─────────────────────┤     ├─────────────────────┤
│ id (PK)             │     │ id (PK)             │
│ start_time          │     │ scheduled_start     │
│ stop_time           │     │ duration_minutes    │
│ duration_seconds    │     │ recurring           │
│ trigger_type        │     │ recurrence_pattern  │
│ stop_reason         │     │ enabled             │
└─────────────────────┘     │ last_executed       │
                            └─────────────────────┘

┌─────────────────────┐
│     event_log       │
├─────────────────────┤
│ id (PK)             │
│ event_type          │
│ event_data (JSON)   │
│ created_at          │
└─────────────────────┘
```

### Table: system_state

Stores the current operational state. **Always exactly one row with id=1.**

```sql
CREATE TABLE system_state (
    id INT PRIMARY KEY DEFAULT 1,

    -- Generator State
    generator_running BOOLEAN NOT NULL DEFAULT FALSE,
    generator_start_time BIGINT NULL,
    current_run_id INT NULL,
    run_trigger ENUM('idle', 'victron', 'manual', 'scheduled') NOT NULL DEFAULT 'idle',

    -- Override Control
    override_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    override_type ENUM('none', 'force_run', 'force_stop') NOT NULL DEFAULT 'none',

    -- Victron Input
    victron_signal_state BOOLEAN NOT NULL DEFAULT FALSE,
    victron_last_change BIGINT NULL,

    -- GenSlave Communication
    last_heartbeat_sent BIGINT NULL,
    last_heartbeat_received BIGINT NULL,
    missed_heartbeat_count INT NOT NULL DEFAULT 0,
    slave_connection_status ENUM('connected', 'disconnected', 'unknown') NOT NULL DEFAULT 'unknown',
    slave_relay_state BOOLEAN NULL,

    -- Metadata
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_single_row CHECK (id = 1),
    CONSTRAINT fk_current_run FOREIGN KEY (current_run_id) REFERENCES generator_runs(id)
);
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/system_state.py
from datetime import datetime
from typing import Optional
from sqlalchemy import Enum, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from app.models.base import Base

class TriggerType(str, Enum):
    IDLE = "idle"
    VICTRON = "victron"
    MANUAL = "manual"
    SCHEDULED = "scheduled"

class OverrideType(str, Enum):
    NONE = "none"
    FORCE_RUN = "force_run"
    FORCE_STOP = "force_stop"

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNKNOWN = "unknown"

class SystemState(Base):
    __tablename__ = "system_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_row"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Generator State
    generator_running: Mapped[bool] = mapped_column(default=False)
    generator_start_time: Mapped[Optional[int]] = mapped_column(nullable=True)
    current_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("generator_runs.id"), nullable=True
    )
    run_trigger: Mapped[str] = mapped_column(default="idle")

    # Override Control
    override_enabled: Mapped[bool] = mapped_column(default=False)
    override_type: Mapped[str] = mapped_column(default="none")

    # Victron Input
    victron_signal_state: Mapped[bool] = mapped_column(default=False)
    victron_last_change: Mapped[Optional[int]] = mapped_column(nullable=True)

    # GenSlave Communication
    last_heartbeat_sent: Mapped[Optional[int]] = mapped_column(nullable=True)
    last_heartbeat_received: Mapped[Optional[int]] = mapped_column(nullable=True)
    missed_heartbeat_count: Mapped[int] = mapped_column(default=0)
    slave_connection_status: Mapped[str] = mapped_column(default="unknown")
    slave_relay_state: Mapped[Optional[bool]] = mapped_column(nullable=True)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    current_run: Mapped[Optional["GeneratorRun"]] = relationship(
        "GeneratorRun", foreign_keys=[current_run_id]
    )

    @classmethod
    def get_instance(cls, db: Session) -> "SystemState":
        """Get or create the singleton state row."""
        state = db.query(cls).filter(cls.id == 1).first()
        if not state:
            state = cls(id=1)
            db.add(state)
            db.commit()
            db.refresh(state)
        return state

    def is_generator_running(self) -> bool:
        """Check if generator is currently running."""
        return self.generator_running and self.run_trigger != "idle"

    def can_start_generator(self) -> bool:
        """Check if generator can be started."""
        if self.generator_running:
            return False
        if self.override_enabled and self.override_type == "force_stop":
            return False
        if self.slave_connection_status == "disconnected":
            return False
        return True
```

### Table: config

Stores system configuration. **Always exactly one row with id=1.**

```sql
CREATE TABLE config (
    id INT PRIMARY KEY DEFAULT 1,

    -- Heartbeat Settings
    heartbeat_interval_seconds INT NOT NULL DEFAULT 60,
    heartbeat_failure_threshold INT NOT NULL DEFAULT 3,

    -- GenSlave Connection
    slave_api_url VARCHAR(255) NOT NULL,
    slave_api_secret VARCHAR(255) NOT NULL,

    -- Webhook Settings
    webhook_base_url VARCHAR(255) NULL,
    webhook_secret VARCHAR(255) NULL,
    webhook_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Health Thresholds
    temp_warning_celsius INT NOT NULL DEFAULT 70,
    temp_critical_celsius INT NOT NULL DEFAULT 80,
    disk_warning_percent INT NOT NULL DEFAULT 80,
    disk_critical_percent INT NOT NULL DEFAULT 90,
    ram_warning_percent INT NOT NULL DEFAULT 85,

    -- Networking
    tailscale_hostname VARCHAR(50) NULL,
    tailscale_ip VARCHAR(45) NULL,
    cloudflare_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    cloudflare_hostname VARCHAR(255) NULL,

    -- Event Log Retention
    event_log_retention_days INT NOT NULL DEFAULT 30,

    -- Metadata
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_single_row CHECK (id = 1)
);
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/config.py
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.models.base import Base

class Config(Base):
    __tablename__ = "config"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_row"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Heartbeat Settings
    heartbeat_interval_seconds: Mapped[int] = mapped_column(default=60)
    heartbeat_failure_threshold: Mapped[int] = mapped_column(default=3)

    # GenSlave Connection
    slave_api_url: Mapped[str] = mapped_column(nullable=False)
    slave_api_secret: Mapped[str] = mapped_column(nullable=False)

    # Webhook Settings
    webhook_base_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(nullable=True)
    webhook_enabled: Mapped[bool] = mapped_column(default=True)

    # Health Thresholds
    temp_warning_celsius: Mapped[int] = mapped_column(default=70)
    temp_critical_celsius: Mapped[int] = mapped_column(default=80)
    disk_warning_percent: Mapped[int] = mapped_column(default=80)
    disk_critical_percent: Mapped[int] = mapped_column(default=90)
    ram_warning_percent: Mapped[int] = mapped_column(default=85)

    # Networking
    tailscale_hostname: Mapped[Optional[str]] = mapped_column(nullable=True)
    tailscale_ip: Mapped[Optional[str]] = mapped_column(nullable=True)
    cloudflare_enabled: Mapped[bool] = mapped_column(default=False)
    cloudflare_hostname: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Event Log Retention
    event_log_retention_days: Mapped[int] = mapped_column(default=30)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @classmethod
    def get_instance(cls, db: Session) -> "Config":
        """Get or create the singleton config row."""
        config = db.query(cls).filter(cls.id == 1).first()
        if not config:
            # This should be created by migration with default values
            raise RuntimeError("Config row not found - run migrations first")
        return config
```

### Table: generator_runs

Stores history of all generator run sessions.

```sql
CREATE TABLE generator_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Timing
    start_time BIGINT NOT NULL,
    stop_time BIGINT NULL,
    duration_seconds INT NULL,

    -- Trigger/Stop Information
    trigger_type ENUM('victron', 'manual', 'scheduled') NOT NULL,
    stop_reason ENUM('victron', 'manual', 'scheduled_end', 'comm_loss', 'override', 'error') NULL,

    -- Scheduled Run Reference (if applicable)
    scheduled_run_id INT NULL,

    -- Notes
    notes TEXT NULL,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_start_time (start_time),
    INDEX idx_trigger_type (trigger_type),
    INDEX idx_created_at (created_at),

    -- Foreign Keys
    CONSTRAINT fk_scheduled_run FOREIGN KEY (scheduled_run_id)
        REFERENCES scheduled_runs(id) ON DELETE SET NULL
);
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/generator_runs.py
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class GeneratorRun(Base):
    __tablename__ = "generator_runs"
    __table_args__ = (
        Index("idx_start_time", "start_time"),
        Index("idx_trigger_type", "trigger_type"),
        Index("idx_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Timing
    start_time: Mapped[int] = mapped_column(nullable=False)
    stop_time: Mapped[Optional[int]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Trigger/Stop Information
    trigger_type: Mapped[str] = mapped_column(nullable=False)  # victron, manual, scheduled
    stop_reason: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Scheduled Run Reference
    scheduled_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scheduled_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    scheduled_run: Mapped[Optional["ScheduledRun"]] = relationship(
        "ScheduledRun", back_populates="runs"
    )

    @property
    def is_active(self) -> bool:
        """Check if this run is currently active (no stop time)."""
        return self.stop_time is None

    def complete(self, stop_time: int, stop_reason: str) -> None:
        """Mark this run as complete."""
        self.stop_time = stop_time
        self.duration_seconds = stop_time - self.start_time
        self.stop_reason = stop_reason
```

### Table: scheduled_runs

Stores scheduled generator run configurations.

```sql
CREATE TABLE scheduled_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Schedule Configuration
    name VARCHAR(100) NULL,
    scheduled_start BIGINT NOT NULL,
    duration_minutes INT NOT NULL,

    -- Recurrence
    recurring BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_pattern VARCHAR(100) NULL,  -- Cron expression or simple pattern
    recurrence_end_date BIGINT NULL,

    -- State
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_executed BIGINT NULL,
    next_execution BIGINT NULL,
    execution_count INT NOT NULL DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_next_execution (next_execution),
    INDEX idx_enabled (enabled)
);
```

**Recurrence Pattern Examples**:
- One-time: `recurrence_pattern = NULL`
- Daily at same time: `"daily"`
- Weekly on same day: `"weekly"`
- Custom cron: `"0 6 * * 1,3,5"` (6am on Mon, Wed, Fri)

**SQLAlchemy Model**:

```python
# genmaster/app/models/scheduled_runs.py
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class ScheduledRun(Base):
    __tablename__ = "scheduled_runs"
    __table_args__ = (
        Index("idx_next_execution", "next_execution"),
        Index("idx_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Schedule Configuration
    name: Mapped[Optional[str]] = mapped_column(nullable=True)
    scheduled_start: Mapped[int] = mapped_column(nullable=False)
    duration_minutes: Mapped[int] = mapped_column(nullable=False)

    # Recurrence
    recurring: Mapped[bool] = mapped_column(default=False)
    recurrence_pattern: Mapped[Optional[str]] = mapped_column(nullable=True)
    recurrence_end_date: Mapped[Optional[int]] = mapped_column(nullable=True)

    # State
    enabled: Mapped[bool] = mapped_column(default=True)
    last_executed: Mapped[Optional[int]] = mapped_column(nullable=True)
    next_execution: Mapped[Optional[int]] = mapped_column(nullable=True)
    execution_count: Mapped[int] = mapped_column(default=0)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    runs: Mapped[List["GeneratorRun"]] = relationship(
        "GeneratorRun", back_populates="scheduled_run"
    )

    def calculate_next_execution(self, from_time: int) -> Optional[int]:
        """Calculate the next execution time based on recurrence pattern."""
        if not self.recurring or not self.recurrence_pattern:
            return None

        # Implementation depends on recurrence_pattern format
        # Simple patterns: daily, weekly, monthly
        # Complex: cron expressions
        pass  # Implemented in scheduler service
```

### Table: event_log

Stores system events for auditing and debugging.

```sql
CREATE TABLE event_log (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Event Information
    event_type VARCHAR(50) NOT NULL,
    event_data JSON NULL,
    severity ENUM('INFO', 'WARNING', 'ERROR', 'CRITICAL') NOT NULL DEFAULT 'INFO',

    -- Source
    source VARCHAR(50) NOT NULL DEFAULT 'genmaster',

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_created_at (created_at),
    INDEX idx_event_type (event_type),
    INDEX idx_severity (severity)
);
```

**Event Types**:
| Event Type | Severity | Description |
|------------|----------|-------------|
| `SYSTEM_BOOT` | INFO | System startup complete |
| `SYSTEM_SHUTDOWN` | INFO | Graceful shutdown initiated |
| `GENERATOR_START` | INFO | Generator started |
| `GENERATOR_STOP` | INFO | Generator stopped |
| `HEARTBEAT_SENT` | INFO | Heartbeat sent to GenSlave |
| `HEARTBEAT_RECEIVED` | INFO | Heartbeat response received |
| `HEARTBEAT_MISSED` | WARNING | Heartbeat timeout |
| `COMM_LOST` | ERROR | Communication lost with GenSlave |
| `COMM_RESTORED` | INFO | Communication restored |
| `OVERRIDE_ENABLED` | WARNING | Manual override activated |
| `OVERRIDE_DISABLED` | INFO | Override deactivated |
| `VICTRON_SIGNAL_CHANGE` | INFO | GPIO17 state changed |
| `CONFIG_CHANGED` | INFO | Configuration updated |
| `WEBHOOK_SENT` | INFO | Webhook notification sent |
| `WEBHOOK_FAILED` | ERROR | Webhook delivery failed |
| `HEALTH_WARNING` | WARNING | Health threshold exceeded |
| `FAILSAFE_TRIGGERED` | CRITICAL | Failsafe shutdown executed |
| `ERROR` | ERROR | General error |

**SQLAlchemy Model**:

```python
# genmaster/app/models/event_log.py
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import Index, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = (
        Index("idx_created_at", "created_at"),
        Index("idx_event_type", "event_type"),
        Index("idx_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Event Information
    event_type: Mapped[str] = mapped_column(nullable=False)
    event_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    severity: Mapped[str] = mapped_column(default="INFO")

    # Source
    source: Mapped[str] = mapped_column(default="genmaster")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    @classmethod
    def log(cls, db, event_type: str, data: dict = None,
            severity: str = "INFO", source: str = "genmaster") -> "EventLog":
        """Create and persist a new event log entry."""
        event = cls(
            event_type=event_type,
            event_data=data,
            severity=severity,
            source=source
        )
        db.add(event)
        db.commit()
        return event
```

---

## GenSlave Database Schema

GenSlave has a minimal database - just state tracking and config mirror.

### Table: system_state

```sql
CREATE TABLE system_state (
    id INT PRIMARY KEY DEFAULT 1,

    -- Relay State
    relay_state BOOLEAN NOT NULL DEFAULT FALSE,
    relay_on_time BIGINT NULL,
    relay_off_time BIGINT NULL,

    -- GenMaster Communication
    last_heartbeat_received BIGINT NULL,
    missed_heartbeat_count INT NOT NULL DEFAULT 0,
    master_connection_status ENUM('connected', 'disconnected', 'unknown') NOT NULL DEFAULT 'unknown',

    -- Last Command
    last_command VARCHAR(20) NULL,
    last_command_time BIGINT NULL,
    last_command_source VARCHAR(50) NULL,

    -- Failsafe
    failsafe_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    failsafe_time BIGINT NULL,

    -- Metadata
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_single_row CHECK (id = 1)
);
```

**SQLAlchemy Model**:

```python
# genslave/app/models/system_state.py
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.models.base import Base

class SystemState(Base):
    __tablename__ = "system_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_row"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Relay State
    relay_state: Mapped[bool] = mapped_column(default=False)
    relay_on_time: Mapped[Optional[int]] = mapped_column(nullable=True)
    relay_off_time: Mapped[Optional[int]] = mapped_column(nullable=True)

    # GenMaster Communication
    last_heartbeat_received: Mapped[Optional[int]] = mapped_column(nullable=True)
    missed_heartbeat_count: Mapped[int] = mapped_column(default=0)
    master_connection_status: Mapped[str] = mapped_column(default="unknown")

    # Last Command
    last_command: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_command_time: Mapped[Optional[int]] = mapped_column(nullable=True)
    last_command_source: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Failsafe
    failsafe_triggered: Mapped[bool] = mapped_column(default=False)
    failsafe_time: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @classmethod
    def get_instance(cls, db: Session) -> "SystemState":
        """Get or create the singleton state row."""
        state = db.query(cls).filter(cls.id == 1).first()
        if not state:
            state = cls(id=1)
            db.add(state)
            db.commit()
            db.refresh(state)
        return state
```

### Table: config

```sql
CREATE TABLE config (
    id INT PRIMARY KEY DEFAULT 1,

    -- Heartbeat Settings (pushed from GenMaster)
    heartbeat_interval_seconds INT NOT NULL DEFAULT 60,
    heartbeat_failure_threshold INT NOT NULL DEFAULT 3,

    -- GenMaster Connection
    master_api_url VARCHAR(255) NULL,

    -- Webhook (for direct failsafe notification)
    webhook_base_url VARCHAR(255) NULL,
    webhook_secret VARCHAR(255) NULL,

    -- LCD Display
    lcd_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lcd_brightness INT NOT NULL DEFAULT 100,

    -- Metadata
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_single_row CHECK (id = 1)
);
```

---

## Database Initialization

### Base Model

```python
# app/models/base.py (same for both GenMaster and GenSlave)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

### Database Connection

```python
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Create engine with connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=settings.app_debug  # Log SQL in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Models __init__.py

```python
# genmaster/app/models/__init__.py
from app.models.base import Base
from app.models.system_state import SystemState
from app.models.config import Config
from app.models.generator_runs import GeneratorRun
from app.models.scheduled_runs import ScheduledRun
from app.models.event_log import EventLog

__all__ = [
    "Base",
    "SystemState",
    "Config",
    "GeneratorRun",
    "ScheduledRun",
    "EventLog",
]
```

```python
# genslave/app/models/__init__.py
from app.models.base import Base
from app.models.system_state import SystemState
from app.models.config import Config

__all__ = [
    "Base",
    "SystemState",
    "Config",
]
```

---

## Alembic Migrations

### Setup

```bash
# Initialize Alembic (run once)
cd genmaster
alembic init alembic
```

### alembic/env.py Configuration

```python
# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your models
from app.models import Base
from app.config import settings

config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Initial Migration

```python
# alembic/versions/001_initial_schema.py
"""Initial schema

Revision ID: 001
Create Date: 2024-01-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create generator_runs first (referenced by system_state)
    op.create_table(
        'generator_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('start_time', sa.BigInteger(), nullable=False),
        sa.Column('stop_time', sa.BigInteger(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('trigger_type', sa.String(20), nullable=False),
        sa.Column('stop_reason', sa.String(20), nullable=True),
        sa.Column('scheduled_run_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_start_time', 'generator_runs', ['start_time'])
    op.create_index('idx_trigger_type', 'generator_runs', ['trigger_type'])
    op.create_index('idx_created_at', 'generator_runs', ['created_at'])

    # Create scheduled_runs
    op.create_table(
        'scheduled_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('scheduled_start', sa.BigInteger(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('recurring', sa.Boolean(), default=False),
        sa.Column('recurrence_pattern', sa.String(100), nullable=True),
        sa.Column('recurrence_end_date', sa.BigInteger(), nullable=True),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('last_executed', sa.BigInteger(), nullable=True),
        sa.Column('next_execution', sa.BigInteger(), nullable=True),
        sa.Column('execution_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Add FK to generator_runs
    op.create_foreign_key(
        'fk_scheduled_run', 'generator_runs', 'scheduled_runs',
        ['scheduled_run_id'], ['id'], ondelete='SET NULL'
    )

    # Create system_state
    op.create_table(
        'system_state',
        sa.Column('id', sa.Integer(), nullable=False, default=1),
        sa.Column('generator_running', sa.Boolean(), default=False),
        sa.Column('generator_start_time', sa.BigInteger(), nullable=True),
        sa.Column('current_run_id', sa.Integer(), nullable=True),
        sa.Column('run_trigger', sa.String(20), default='idle'),
        sa.Column('override_enabled', sa.Boolean(), default=False),
        sa.Column('override_type', sa.String(20), default='none'),
        sa.Column('victron_signal_state', sa.Boolean(), default=False),
        sa.Column('victron_last_change', sa.BigInteger(), nullable=True),
        sa.Column('last_heartbeat_sent', sa.BigInteger(), nullable=True),
        sa.Column('last_heartbeat_received', sa.BigInteger(), nullable=True),
        sa.Column('missed_heartbeat_count', sa.Integer(), default=0),
        sa.Column('slave_connection_status', sa.String(20), default='unknown'),
        sa.Column('slave_relay_state', sa.Boolean(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['current_run_id'], ['generator_runs.id']),
        sa.CheckConstraint('id = 1', name='chk_single_row')
    )

    # Insert initial row
    op.execute("INSERT INTO system_state (id) VALUES (1)")

    # Create config
    op.create_table(
        'config',
        sa.Column('id', sa.Integer(), nullable=False, default=1),
        sa.Column('heartbeat_interval_seconds', sa.Integer(), default=60),
        sa.Column('heartbeat_failure_threshold', sa.Integer(), default=3),
        sa.Column('slave_api_url', sa.String(255), nullable=False),
        sa.Column('slave_api_secret', sa.String(255), nullable=False),
        sa.Column('webhook_base_url', sa.String(255), nullable=True),
        sa.Column('webhook_secret', sa.String(255), nullable=True),
        sa.Column('webhook_enabled', sa.Boolean(), default=True),
        sa.Column('temp_warning_celsius', sa.Integer(), default=70),
        sa.Column('temp_critical_celsius', sa.Integer(), default=80),
        sa.Column('disk_warning_percent', sa.Integer(), default=80),
        sa.Column('disk_critical_percent', sa.Integer(), default=90),
        sa.Column('ram_warning_percent', sa.Integer(), default=85),
        sa.Column('tailscale_hostname', sa.String(50), nullable=True),
        sa.Column('tailscale_ip', sa.String(45), nullable=True),
        sa.Column('cloudflare_enabled', sa.Boolean(), default=False),
        sa.Column('cloudflare_hostname', sa.String(255), nullable=True),
        sa.Column('event_log_retention_days', sa.Integer(), default=30),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('id = 1', name='chk_single_row')
    )

    # Insert initial config (slave_api_url and secret will be updated during setup)
    op.execute("""
        INSERT INTO config (id, slave_api_url, slave_api_secret)
        VALUES (1, 'http://genslave:8000', 'CHANGE_ME')
    """)

    # Create event_log
    op.create_table(
        'event_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_data', mysql.JSON(), nullable=True),
        sa.Column('severity', sa.String(20), default='INFO'),
        sa.Column('source', sa.String(50), default='genmaster'),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_event_created_at', 'event_log', ['created_at'])
    op.create_index('idx_event_type', 'event_log', ['event_type'])
    op.create_index('idx_severity', 'event_log', ['severity'])

def downgrade() -> None:
    op.drop_table('event_log')
    op.drop_table('config')
    op.drop_table('system_state')
    op.drop_constraint('fk_scheduled_run', 'generator_runs', type_='foreignkey')
    op.drop_table('scheduled_runs')
    op.drop_table('generator_runs')
```

---

## MariaDB Configuration for SSD Longevity

```ini
# my.cnf additions for reduced writes
[mysqld]
# Reduce sync frequency (data may be lost on crash, acceptable for this use case)
innodb_flush_log_at_trx_commit = 2
sync_binlog = 0

# Direct I/O to bypass filesystem cache
innodb_flush_method = O_DIRECT

# Reduce checkpoint frequency
innodb_log_file_size = 256M
innodb_log_buffer_size = 16M

# Disable binary logging (not needed for single-instance)
skip-log-bin

# Reduce general logging
general_log = 0
slow_query_log = 0
```

---

## Data Access Patterns

### Repository Pattern Example

```python
# genmaster/app/repositories/generator_runs.py
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import GeneratorRun

class GeneratorRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, start_time: int, trigger_type: str,
               scheduled_run_id: int = None) -> GeneratorRun:
        """Create a new generator run record."""
        run = GeneratorRun(
            start_time=start_time,
            trigger_type=trigger_type,
            scheduled_run_id=scheduled_run_id
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_id(self, run_id: int) -> Optional[GeneratorRun]:
        """Get a run by ID."""
        return self.db.query(GeneratorRun).filter(GeneratorRun.id == run_id).first()

    def get_active(self) -> Optional[GeneratorRun]:
        """Get the currently active run (no stop time)."""
        return self.db.query(GeneratorRun).filter(
            GeneratorRun.stop_time.is_(None)
        ).first()

    def complete(self, run_id: int, stop_time: int, stop_reason: str) -> GeneratorRun:
        """Mark a run as complete."""
        run = self.get_by_id(run_id)
        if run:
            run.complete(stop_time, stop_reason)
            self.db.commit()
            self.db.refresh(run)
        return run

    def get_recent(self, limit: int = 10) -> List[GeneratorRun]:
        """Get recent runs ordered by start time."""
        return self.db.query(GeneratorRun).order_by(
            GeneratorRun.start_time.desc()
        ).limit(limit).all()

    def get_by_date_range(self, start: int, end: int) -> List[GeneratorRun]:
        """Get runs within a date range."""
        return self.db.query(GeneratorRun).filter(
            GeneratorRun.start_time >= start,
            GeneratorRun.start_time <= end
        ).order_by(GeneratorRun.start_time).all()

    def get_total_runtime_seconds(self, since: int) -> int:
        """Get total runtime in seconds since a timestamp."""
        result = self.db.query(func.sum(GeneratorRun.duration_seconds)).filter(
            GeneratorRun.start_time >= since,
            GeneratorRun.duration_seconds.isnot(None)
        ).scalar()
        return result or 0

    def get_run_count(self, since: int) -> int:
        """Get count of runs since a timestamp."""
        return self.db.query(GeneratorRun).filter(
            GeneratorRun.start_time >= since
        ).count()

    def get_stats_by_trigger(self, since: int) -> dict:
        """Get run statistics grouped by trigger type."""
        results = self.db.query(
            GeneratorRun.trigger_type,
            func.count(GeneratorRun.id).label('count'),
            func.sum(GeneratorRun.duration_seconds).label('total_seconds')
        ).filter(
            GeneratorRun.start_time >= since
        ).group_by(GeneratorRun.trigger_type).all()

        return {
            row.trigger_type: {
                'count': row.count,
                'total_seconds': row.total_seconds or 0
            }
            for row in results
        }
```

---

## Agent Implementation Checklist

When implementing the database layer:

- [ ] Create `app/models/base.py` with Base class
- [ ] Create all model files in `app/models/`
- [ ] Create `app/models/__init__.py` exporting all models
- [ ] Create `app/database.py` with engine and session
- [ ] Initialize Alembic in `alembic/` directory
- [ ] Configure `alembic/env.py` to use models
- [ ] Create initial migration for all tables
- [ ] Create repository classes in `app/repositories/`
- [ ] Test migrations with `alembic upgrade head`
- [ ] Verify single-row constraints work correctly
- [ ] Test repository CRUD operations

---

## Related Documents

- `01-project-structure.md` - Project conventions
- `03-genmaster-backend.md` - Uses these models
- `05-genslave-backend.md` - Uses GenSlave models
- `06-docker-infrastructure.md` - MariaDB container config
