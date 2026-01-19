# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/generator_runs.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Generator runs model - history of all generator run sessions."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.scheduled_runs import ScheduledRun


class GeneratorRun(Base):
    """Stores history of all generator run sessions."""

    __tablename__ = "generator_runs"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN ('victron', 'manual', 'scheduled', 'exercise')",
            name="chk_trigger_type",
        ),
        CheckConstraint(
            "stop_reason IS NULL OR stop_reason IN "
            "('victron', 'manual', 'scheduled_end', 'exercise_end', 'comm_loss', 'override', 'error')",
            name="chk_stop_reason",
        ),
        Index("idx_generator_runs_start_time", "start_time"),
        Index("idx_generator_runs_trigger_type", "trigger_type"),
        Index("idx_generator_runs_created_at", "created_at"),
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

    # Fuel tracking - snapshot of fuel configuration at run time
    fuel_type_at_run: Mapped[Optional[str]] = mapped_column(nullable=True)  # 'lpg', 'natural_gas', 'diesel'
    load_at_run: Mapped[Optional[int]] = mapped_column(nullable=True)  # 50 or 100
    fuel_consumption_rate: Mapped[Optional[float]] = mapped_column(nullable=True)  # gal/hr rate used
    estimated_fuel_used: Mapped[Optional[float]] = mapped_column(nullable=True)  # calculated total gallons

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
