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

import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.generator_runs import GeneratorRun


class ScheduledRun(Base):
    """Stores scheduled generator run configurations.

    Uses weekly schedule format with days_of_week and start_time.
    """

    __tablename__ = "scheduled_runs"
    __table_args__ = (
        Index("idx_scheduled_runs_next_execution", "next_execution"),
        Index("idx_scheduled_runs_enabled", "enabled"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Schedule Configuration
    name: Mapped[Optional[str]] = mapped_column(nullable=True)
    start_time: Mapped[str] = mapped_column(nullable=False, default="09:00")
    duration_minutes: Mapped[int] = mapped_column(nullable=False)
    # Days stored as JSON string: "[0,1,2,3,4,5,6]"
    _days_of_week: Mapped[str] = mapped_column("days_of_week", nullable=False, default="[]")

    # State
    enabled: Mapped[bool] = mapped_column(default=True)
    last_executed: Mapped[Optional[int]] = mapped_column(nullable=True)
    next_execution: Mapped[Optional[int]] = mapped_column(nullable=True)
    execution_count: Mapped[int] = mapped_column(default=0)

    @property
    def days_of_week(self) -> List[int]:
        """Get days_of_week as a list."""
        try:
            return json.loads(self._days_of_week)
        except (json.JSONDecodeError, TypeError):
            return []

    @days_of_week.setter
    def days_of_week(self, value: List[int]) -> None:
        """Set days_of_week from a list."""
        self._days_of_week = json.dumps(sorted(set(value)))

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
