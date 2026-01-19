# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/system_state.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System state model - singleton table for current operational state."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.generator_runs import GeneratorRun


class SystemState(Base):
    """
    Stores the current operational state.

    Always exactly one row with id=1.
    """

    __tablename__ = "system_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_single_row"),
        CheckConstraint(
            "run_trigger IN ('idle', 'victron', 'manual', 'scheduled', 'exercise')",
            name="chk_run_trigger",
        ),
        CheckConstraint(
            "override_type IN ('none', 'force_run', 'force_stop')",
            name="chk_override_type",
        ),
        CheckConstraint(
            "slave_connection_status IN ('connected', 'disconnected', 'unknown')",
            name="chk_connection_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Automation Arming (must be enabled before any automation actions)
    automation_armed: Mapped[bool] = mapped_column(default=False)
    automation_armed_at: Mapped[Optional[int]] = mapped_column(nullable=True)
    automation_armed_by: Mapped[Optional[str]] = mapped_column(nullable=True)

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
    slave_relay_armed: Mapped[Optional[bool]] = mapped_column(nullable=True)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    current_run: Mapped[Optional["GeneratorRun"]] = relationship(
        "GeneratorRun", foreign_keys=[current_run_id]
    )

    @classmethod
    async def get_instance(cls, db: AsyncSession) -> "SystemState":
        """Get or create the singleton state row."""
        result = await db.execute(select(cls).where(cls.id == 1))
        state = result.scalar_one_or_none()
        if not state:
            state = cls(id=1)
            db.add(state)
            await db.commit()
            await db.refresh(state)
        return state

    def is_generator_running(self) -> bool:
        """Check if generator is currently running."""
        return self.generator_running and self.run_trigger != "idle"

    def can_start_generator(self) -> bool:
        """Check if generator can be started.

        Note: We don't check slave_relay_armed here because GenSlave
        is the source of truth for armed state. If not armed, GenSlave
        will reject the relay_on() request directly.
        """
        if self.generator_running:
            return False
        if self.override_enabled and self.override_type == "force_stop":
            return False
        if self.slave_connection_status == "disconnected":
            return False
        return True

    def is_armed(self) -> bool:
        """Check if relay is armed (cached from last heartbeat)."""
        return self.slave_relay_armed or False
