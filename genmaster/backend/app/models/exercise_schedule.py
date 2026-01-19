# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/exercise_schedule.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Exercise schedule model - singleton table for generator exercise configuration."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExerciseSchedule(Base):
    """
    Stores generator exercise schedule configuration.

    Always exactly one row with id=1 (singleton pattern).
    Exercise runs the generator at configured intervals for maintenance.
    """

    __tablename__ = "exercise_schedule"
    __table_args__ = (
        CheckConstraint("id = 1", name="chk_exercise_schedule_single_row"),
        CheckConstraint(
            "frequency_days >= 1 AND frequency_days <= 365",
            name="chk_frequency_days_range",
        ),
        CheckConstraint(
            "duration_minutes >= 1 AND duration_minutes <= 480",
            name="chk_duration_minutes_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Schedule configuration
    enabled: Mapped[bool] = mapped_column(default=False)
    frequency_days: Mapped[int] = mapped_column(default=7)  # How often to exercise (e.g., 7 = weekly)
    start_time: Mapped[str] = mapped_column(default="10:00")  # Time of day to start (HH:MM)
    duration_minutes: Mapped[int] = mapped_column(default=15)  # How long to run

    # Tracking
    last_exercise_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    next_exercise_date: Mapped[Optional[date]] = mapped_column(nullable=True)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    async def get_instance(cls, db: AsyncSession) -> "ExerciseSchedule":
        """Get or create the singleton exercise schedule row."""
        result = await db.execute(select(cls).where(cls.id == 1))
        schedule = result.scalar_one_or_none()
        if not schedule:
            schedule = cls(id=1)
            db.add(schedule)
            await db.commit()
            await db.refresh(schedule)
        return schedule

    def calculate_next_exercise(self) -> Optional[date]:
        """Calculate the next exercise date based on last exercise and frequency."""
        from datetime import timedelta

        if not self.enabled:
            return None

        if self.last_exercise_date:
            return self.last_exercise_date + timedelta(days=self.frequency_days)
        else:
            # If never run, schedule for today or tomorrow
            today = date.today()
            return today

    def update_after_exercise(self) -> None:
        """Update tracking fields after an exercise run completes."""
        from datetime import timedelta

        self.last_exercise_date = date.today()
        self.next_exercise_date = self.last_exercise_date + timedelta(days=self.frequency_days)
