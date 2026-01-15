# Agent Handoff: Database Schema & Models

## Purpose
This document defines the complete database schema for both GenMaster and GenSlave, including SQLAlchemy models, Alembic migrations, and data access patterns.

---

## Database Technology

### GenMaster (RPi 5 8GB + NVMe)

| Component | Technology |
|-----------|------------|
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0+ |
| Migrations | Alembic |
| Driver | asyncpg / psycopg2 |

**Why PostgreSQL?**
- Matches existing n8n stack for consistency
- Excellent JSON support for event data
- Superior concurrent access handling
- Built-in NOTIFY/LISTEN for real-time updates
- Better performance on NVMe storage
- Robust for continuous operation

### GenSlave (Pi Zero 2W)

| Component | Technology |
|-----------|------------|
| Database | SQLite 3 |
| ORM | SQLAlchemy 2.0+ |
| Migrations | Alembic |
| Driver | aiosqlite |

**Why SQLite for GenSlave?**
- Zero additional memory overhead (no server process)
- Perfect for single-row state storage
- Embedded - no network dependency
- Reliable on constrained hardware
- Saves ~80MB RAM vs PostgreSQL/MariaDB

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
│ event_data (JSONB)  │
│ created_at          │
└─────────────────────┘
```

### Table: system_state

Stores the current operational state. **Always exactly one row with id=1.**

```sql
-- PostgreSQL
CREATE TABLE system_state (
    id INTEGER PRIMARY KEY DEFAULT 1,

    -- Generator State
    generator_running BOOLEAN NOT NULL DEFAULT FALSE,
    generator_start_time BIGINT NULL,
    current_run_id INTEGER NULL,
    run_trigger VARCHAR(20) NOT NULL DEFAULT 'idle',

    -- Override Control
    override_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    override_type VARCHAR(20) NOT NULL DEFAULT 'none',

    -- Victron Input
    victron_signal_state BOOLEAN NOT NULL DEFAULT FALSE,
    victron_last_change BIGINT NULL,

    -- GenSlave Communication
    last_heartbeat_sent BIGINT NULL,
    last_heartbeat_received BIGINT NULL,
    missed_heartbeat_count INTEGER NOT NULL DEFAULT 0,
    slave_connection_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    slave_relay_state BOOLEAN NULL,

    -- Metadata
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_single_row CHECK (id = 1),
    CONSTRAINT chk_run_trigger CHECK (run_trigger IN ('idle', 'victron', 'manual', 'scheduled')),
    CONSTRAINT chk_override_type CHECK (override_type IN ('none', 'force_run', 'force_stop')),
    CONSTRAINT chk_connection_status CHECK (slave_connection_status IN ('connected', 'disconnected', 'unknown'))
);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_system_state_updated_at
    BEFORE UPDATE ON system_state
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/system_state.py
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from app.models.base import Base


class SystemState(Base):
    __tablename__ = "system_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_row"),
        CheckConstraint(
            "run_trigger IN ('idle', 'victron', 'manual', 'scheduled')",
            name="chk_run_trigger"
        ),
        CheckConstraint(
            "override_type IN ('none', 'force_run', 'force_stop')",
            name="chk_override_type"
        ),
        CheckConstraint(
            "slave_connection_status IN ('connected', 'disconnected', 'unknown')",
            name="chk_connection_status"
        ),
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
        server_default=func.now(),
        onupdate=func.now()
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
-- PostgreSQL
CREATE TABLE config (
    id INTEGER PRIMARY KEY DEFAULT 1,

    -- Heartbeat Settings
    heartbeat_interval_seconds INTEGER NOT NULL DEFAULT 60,
    heartbeat_failure_threshold INTEGER NOT NULL DEFAULT 3,

    -- GenSlave Connection
    slave_api_url VARCHAR(255) NOT NULL,
    slave_api_secret VARCHAR(255) NOT NULL,

    -- Webhook Settings
    webhook_base_url VARCHAR(255) NULL,
    webhook_secret VARCHAR(255) NULL,
    webhook_enabled BOOLEAN NOT NULL DEFAULT TRUE,

    -- Health Thresholds
    temp_warning_celsius INTEGER NOT NULL DEFAULT 70,
    temp_critical_celsius INTEGER NOT NULL DEFAULT 80,
    disk_warning_percent INTEGER NOT NULL DEFAULT 80,
    disk_critical_percent INTEGER NOT NULL DEFAULT 90,
    ram_warning_percent INTEGER NOT NULL DEFAULT 85,

    -- Networking
    tailscale_hostname VARCHAR(50) NULL,
    tailscale_ip VARCHAR(45) NULL,
    cloudflare_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    cloudflare_hostname VARCHAR(255) NULL,

    -- SSL Configuration
    ssl_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ssl_domain VARCHAR(255) NULL,
    ssl_email VARCHAR(255) NULL,
    ssl_dns_provider VARCHAR(50) NULL,

    -- Event Log Retention
    event_log_retention_days INTEGER NOT NULL DEFAULT 30,

    -- Metadata
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_single_row CHECK (id = 1)
);

CREATE TRIGGER update_config_updated_at
    BEFORE UPDATE ON config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/config.py
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint, func
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

    # SSL Configuration
    ssl_enabled: Mapped[bool] = mapped_column(default=False)
    ssl_domain: Mapped[Optional[str]] = mapped_column(nullable=True)
    ssl_email: Mapped[Optional[str]] = mapped_column(nullable=True)
    ssl_dns_provider: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Event Log Retention
    event_log_retention_days: Mapped[int] = mapped_column(default=30)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now()
    )

    @classmethod
    def get_instance(cls, db: Session) -> "Config":
        """Get or create the singleton config row."""
        config = db.query(cls).filter(cls.id == 1).first()
        if not config:
            raise RuntimeError("Config row not found - run migrations first")
        return config
```

### Table: generator_runs

Stores history of all generator run sessions.

```sql
-- PostgreSQL
CREATE TABLE generator_runs (
    id SERIAL PRIMARY KEY,

    -- Timing
    start_time BIGINT NOT NULL,
    stop_time BIGINT NULL,
    duration_seconds INTEGER NULL,

    -- Trigger/Stop Information
    trigger_type VARCHAR(20) NOT NULL,
    stop_reason VARCHAR(20) NULL,

    -- Scheduled Run Reference (if applicable)
    scheduled_run_id INTEGER NULL,

    -- Notes
    notes TEXT NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_trigger_type CHECK (trigger_type IN ('victron', 'manual', 'scheduled')),
    CONSTRAINT chk_stop_reason CHECK (stop_reason IS NULL OR stop_reason IN
        ('victron', 'manual', 'scheduled_end', 'comm_loss', 'override', 'error')),

    -- Foreign Keys
    CONSTRAINT fk_scheduled_run FOREIGN KEY (scheduled_run_id)
        REFERENCES scheduled_runs(id) ON DELETE SET NULL
);

-- Indexes for common queries
CREATE INDEX idx_generator_runs_start_time ON generator_runs(start_time);
CREATE INDEX idx_generator_runs_trigger_type ON generator_runs(trigger_type);
CREATE INDEX idx_generator_runs_created_at ON generator_runs(created_at);
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/generator_runs.py
from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class GeneratorRun(Base):
    __tablename__ = "generator_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('victron', 'manual', 'scheduled')",
            name="chk_trigger_type"
        ),
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
    trigger_type: Mapped[str] = mapped_column(nullable=False)
    stop_reason: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Scheduled Run Reference
    scheduled_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("scheduled_runs.id", ondelete="SET NULL"), nullable=True
    )

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

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

```sql
-- PostgreSQL
CREATE TABLE scheduled_runs (
    id SERIAL PRIMARY KEY,

    -- Schedule Configuration
    name VARCHAR(100) NULL,
    scheduled_start BIGINT NOT NULL,
    duration_minutes INTEGER NOT NULL,

    -- Recurrence
    recurring BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_pattern VARCHAR(100) NULL,
    recurrence_end_date BIGINT NULL,

    -- State
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_executed BIGINT NULL,
    next_execution BIGINT NULL,
    execution_count INTEGER NOT NULL DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduled_runs_next_execution ON scheduled_runs(next_execution);
CREATE INDEX idx_scheduled_runs_enabled ON scheduled_runs(enabled);

CREATE TRIGGER update_scheduled_runs_updated_at
    BEFORE UPDATE ON scheduled_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Table: event_log

```sql
-- PostgreSQL with JSONB for efficient JSON queries
CREATE TABLE event_log (
    id SERIAL PRIMARY KEY,

    -- Event Information
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',

    -- Source
    source VARCHAR(50) NOT NULL DEFAULT 'genmaster',

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_severity CHECK (severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

-- Indexes for common queries
CREATE INDEX idx_event_log_created_at ON event_log(created_at);
CREATE INDEX idx_event_log_event_type ON event_log(event_type);
CREATE INDEX idx_event_log_severity ON event_log(severity);

-- GIN index for JSONB queries
CREATE INDEX idx_event_log_data ON event_log USING GIN (event_data);
```

**SQLAlchemy Model**:

```python
# genmaster/app/models/event_log.py
from datetime import datetime
from typing import Optional
from sqlalchemy import Index, CheckConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class EventLog(Base):
    __tablename__ = "event_log"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="chk_severity"
        ),
        Index("idx_created_at", "created_at"),
        Index("idx_event_type", "event_type"),
        Index("idx_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Event Information
    event_type: Mapped[str] = mapped_column(nullable=False)
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(default="INFO")

    # Source
    source: Mapped[str] = mapped_column(default="genmaster")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

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

## GenSlave Database Schema (SQLite)

GenSlave uses SQLite for minimal resource usage. Only two tables needed.

### Database File Location

```
/opt/genslave/data/genslave.db
```

### Table: system_state

```sql
-- SQLite
CREATE TABLE system_state (
    id INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,

    -- Relay State
    relay_state INTEGER NOT NULL DEFAULT 0,  -- SQLite uses INTEGER for BOOLEAN
    relay_on_time INTEGER NULL,
    relay_off_time INTEGER NULL,

    -- GenMaster Communication
    last_heartbeat_received INTEGER NULL,
    missed_heartbeat_count INTEGER NOT NULL DEFAULT 0,
    master_connection_status TEXT NOT NULL DEFAULT 'unknown',

    -- Last Command
    last_command TEXT NULL,
    last_command_time INTEGER NULL,
    last_command_source TEXT NULL,

    -- Failsafe
    failsafe_triggered INTEGER NOT NULL DEFAULT 0,
    failsafe_time INTEGER NULL,

    -- Metadata
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Initialize with single row
INSERT OR IGNORE INTO system_state (id) VALUES (1);
```

**SQLAlchemy Model (SQLite)**:

```python
# genslave/app/models/system_state.py
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, Session
from app.models.base import Base


class SystemState(Base):
    __tablename__ = "system_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_row"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Relay State (SQLite stores as INTEGER 0/1)
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
    updated_at: Mapped[str] = mapped_column(default=lambda: datetime.utcnow().isoformat())

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
-- SQLite
CREATE TABLE config (
    id INTEGER PRIMARY KEY CHECK (id = 1) DEFAULT 1,

    -- Heartbeat Settings (pushed from GenMaster)
    heartbeat_interval_seconds INTEGER NOT NULL DEFAULT 60,
    heartbeat_failure_threshold INTEGER NOT NULL DEFAULT 3,

    -- GenMaster Connection
    master_api_url TEXT NULL,

    -- Webhook (for direct failsafe notification)
    webhook_base_url TEXT NULL,
    webhook_secret TEXT NULL,

    -- LCD Display
    lcd_enabled INTEGER NOT NULL DEFAULT 1,
    lcd_brightness INTEGER NOT NULL DEFAULT 100,

    -- Metadata
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Initialize with single row
INSERT OR IGNORE INTO config (id) VALUES (1);
```

---

## Database Connection Configuration

### GenMaster (PostgreSQL)

```python
# genmaster/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Sync engine for migrations
sync_engine = create_engine(
    settings.database_url.replace("postgresql+asyncpg", "postgresql"),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.app_debug
)

# Async engine for application
async_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.app_debug
)

# Sync session for migrations
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Async session for application
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession,
    autocommit=False, autoflush=False
)


def get_db() -> Session:
    """Sync database session dependency."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Async database session dependency."""
    async with AsyncSessionLocal() as session:
        yield session
```

### GenSlave (SQLite)

```python
# genslave/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# SQLite engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=settings.app_debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with tables."""
    from app.models import Base
    Base.metadata.create_all(bind=engine)
```

---

## Environment Configuration

### GenMaster .env

```bash
# PostgreSQL connection
DATABASE_URL=postgresql+asyncpg://genmaster:password@db:5432/genmaster

# For migrations (sync driver)
DATABASE_URL_SYNC=postgresql://genmaster:password@db:5432/genmaster
```

### GenSlave .env

```bash
# SQLite connection
DATABASE_URL=sqlite:////opt/genslave/data/genslave.db
```

---

## Alembic Configuration

### GenMaster (PostgreSQL)

```python
# genmaster/alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import Base
from app.config import settings

config = context.config

# Use sync database URL for migrations
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

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

### GenSlave (No Alembic - Direct Creation)

For GenSlave's simple schema, we use direct table creation instead of migrations:

```python
# genslave/app/models/__init__.py
from app.models.base import Base
from app.models.system_state import SystemState
from app.models.config import Config

__all__ = ["Base", "SystemState", "Config"]


def init_database(engine):
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

    # Ensure singleton rows exist
    from sqlalchemy.orm import Session
    with Session(engine) as session:
        if not session.query(SystemState).first():
            session.add(SystemState(id=1))
        if not session.query(Config).first():
            session.add(Config(id=1))
        session.commit()
```

---

## PostgreSQL Docker Configuration

```yaml
# genmaster/docker-compose.yml (database service)
services:
  db:
    image: postgres:16-alpine
    container_name: genmaster-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=genmaster
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=genmaster
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - genmaster-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U genmaster -d genmaster"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    # Performance tuning for NVMe
    command: >
      postgres
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=128MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
```

---

## Agent Implementation Checklist

### GenMaster (PostgreSQL)
- [ ] Create `app/models/base.py` with Base class
- [ ] Create all model files in `app/models/`
- [ ] Create `app/models/__init__.py` exporting all models
- [ ] Create `app/database.py` with async PostgreSQL engine
- [ ] Initialize Alembic in `alembic/` directory
- [ ] Configure `alembic/env.py` for PostgreSQL
- [ ] Create initial migration for all tables
- [ ] Create repository classes in `app/repositories/`
- [ ] Test migrations with `alembic upgrade head`
- [ ] Test async database operations

### GenSlave (SQLite)
- [ ] Create `app/models/base.py` with Base class
- [ ] Create system_state and config models
- [ ] Create `app/database.py` with SQLite engine
- [ ] Create `init_database()` function
- [ ] Test database initialization
- [ ] Test singleton row creation

---

## Related Documents

- `01-project-structure.md` - Project conventions
- `03-genmaster-backend.md` - Uses PostgreSQL models
- `05-genslave-backend.md` - Uses SQLite models
- `06-docker-infrastructure.md` - PostgreSQL container config
