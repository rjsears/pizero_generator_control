# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/scheduled_runs.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Scheduled runs model - scheduled generator run configurations."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.generator_runs import GeneratorRun


class ScheduledRun(Base):
    """Stores scheduled generator run configurations."""

    __tablename__ = "scheduled_runs"
    __table_args__ = (
        Index("idx_scheduled_runs_next_execution", "next_execution"),
        Index("idx_scheduled_runs_enabled", "enabled"),
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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    runs: Mapped[List["GeneratorRun"]] = relationship(
        "GeneratorRun", back_populates="scheduled_run"
    )

    def increment_execution(self, execution_time: int) -> None:
        """Record an execution of this schedule."""
        self.last_executed = execution_time
        self.execution_count += 1
