# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/event_log.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Event log model - JSONB event logging for system events."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import CheckConstraint, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EventLog(Base):
    """Stores system events with flexible JSONB data."""

    __tablename__ = "event_log"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')",
            name="chk_severity",
        ),
        Index("idx_event_log_created_at", "created_at"),
        Index("idx_event_log_event_type", "event_type"),
        Index("idx_event_log_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Event Information
    event_type: Mapped[str] = mapped_column(nullable=False)
    event_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str] = mapped_column(default="INFO")

    # Source
    source: Mapped[str] = mapped_column(default="genmaster")

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    @classmethod
    async def log(
        cls,
        db: AsyncSession,
        event_type: str,
        data: Optional[dict[str, Any]] = None,
        severity: str = "INFO",
        source: str = "genmaster",
    ) -> "EventLog":
        """Create and persist a new event log entry."""
        event = cls(
            event_type=event_type,
            event_data=data,
            severity=severity,
            source=source,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event
