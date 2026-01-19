# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/scheduler.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Scheduler service for scheduled generator runs."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.future import select

from app.database import AsyncSessionLocal
from app.models import ScheduledRun

if TYPE_CHECKING:
    from app.services.state_machine import StateMachine

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Manages scheduled generator runs using APScheduler.

    Supports:
    - One-time scheduled runs
    - Recurring runs (daily, weekly, cron)
    - Auto-stop after duration
    """

    def __init__(self, state_machine: "StateMachine"):
        """
        Initialize scheduler service.

        Args:
            state_machine: StateMachine to trigger generator starts/stops
        """
        self.state_machine = state_machine
        self._scheduler = AsyncIOScheduler()
        self._running = False
        self._auto_stop_jobs: dict[int, str] = {}  # run_id -> job_id

    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._scheduler.start()
        self._running = True
        logger.info("Scheduler service started")

        # Load existing schedules
        asyncio.create_task(self._load_schedules())

    def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        self._scheduler.shutdown(wait=False)
        self._running = False
        logger.info("Scheduler service stopped")

    async def _load_schedules(self) -> None:
        """Load enabled schedules from database."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScheduledRun).where(ScheduledRun.enabled == True)
            )
            schedules = result.scalars().all()

            for schedule in schedules:
                await self.add_schedule(schedule)

            logger.info(f"Loaded {len(schedules)} scheduled runs")

    async def add_schedule(self, schedule: ScheduledRun) -> None:
        """
        Add a schedule to the scheduler.

        Args:
            schedule: ScheduledRun model instance
        """
        job_id = f"schedule_{schedule.id}"

        # Remove existing job if any
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        if not schedule.enabled:
            logger.debug(f"Schedule {schedule.id} is disabled, not scheduling")
            return

        # Determine trigger
        if schedule.recurring and schedule.recurrence_pattern:
            trigger = self._create_recurring_trigger(schedule)
        else:
            # One-time schedule
            run_time = datetime.fromtimestamp(
                schedule.scheduled_start, tz=timezone.utc
            )

            # Skip if in the past
            if run_time <= datetime.now(timezone.utc):
                logger.debug(
                    f"Schedule {schedule.id} is in the past, not scheduling"
                )
                return

            trigger = DateTrigger(run_date=run_time)

        # Add job
        self._scheduler.add_job(
            self._execute_scheduled_run,
            trigger,
            args=[schedule.id],
            id=job_id,
            name=schedule.name or f"Schedule {schedule.id}",
            replace_existing=True,
        )

        logger.info(f"Added schedule {schedule.id} to scheduler")

    def _create_recurring_trigger(self, schedule: ScheduledRun) -> CronTrigger:
        """Create APScheduler trigger for recurring schedule."""
        pattern = schedule.recurrence_pattern.lower()

        # Get the time from scheduled_start
        dt = datetime.fromtimestamp(schedule.scheduled_start, tz=timezone.utc)
        hour = dt.hour
        minute = dt.minute

        if pattern == "daily":
            return CronTrigger(hour=hour, minute=minute)
        elif pattern == "weekly":
            # Run on same day of week as scheduled_start
            day_of_week = dt.strftime("%a").lower()[:3]
            return CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        else:
            # Assume it's a cron expression
            try:
                return CronTrigger.from_crontab(pattern)
            except Exception as e:
                logger.error(
                    f"Invalid cron pattern '{pattern}' for schedule {schedule.id}: {e}"
                )
                # Fall back to daily
                return CronTrigger(hour=hour, minute=minute)

    async def _execute_scheduled_run(self, schedule_id: int) -> None:
        """
        Execute a scheduled generator run.

        Args:
            schedule_id: ID of the schedule to execute
        """
        logger.info(f"Executing scheduled run {schedule_id}")

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ScheduledRun).where(ScheduledRun.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return

            if not schedule.enabled:
                logger.warning(f"Schedule {schedule_id} is disabled, skipping")
                return

            # Start the generator
            try:
                run = await self.state_machine.start_generator(
                    trigger="scheduled",
                    scheduled_run_id=schedule_id,
                    notes=f"Scheduled run: {schedule.name or schedule_id}",
                )

                # Update schedule execution info
                schedule.increment_execution(int(time.time()))
                await db.commit()

                # Schedule auto-stop if duration specified
                if schedule.duration_minutes:
                    await self.schedule_auto_stop(
                        run.id, schedule.duration_minutes
                    )

            except ValueError as e:
                logger.warning(
                    f"Could not start scheduled run {schedule_id}: {e}"
                )

    async def schedule_auto_stop(
        self, run_id: int, duration_minutes: int
    ) -> None:
        """
        Schedule automatic stop after duration.

        Args:
            run_id: ID of the generator run
            duration_minutes: Minutes until auto-stop
        """
        job_id = f"auto_stop_{run_id}"

        stop_time = datetime.now(timezone.utc).timestamp() + (
            duration_minutes * 60
        )
        run_date = datetime.fromtimestamp(stop_time, tz=timezone.utc)

        self._scheduler.add_job(
            self._execute_auto_stop,
            DateTrigger(run_date=run_date),
            args=[run_id],
            id=job_id,
            name=f"Auto-stop run {run_id}",
            replace_existing=True,
        )

        self._auto_stop_jobs[run_id] = job_id
        logger.info(
            f"Scheduled auto-stop for run {run_id} in {duration_minutes} minutes"
        )

    async def _execute_auto_stop(self, run_id: int) -> None:
        """
        Execute automatic stop for a run.

        Args:
            run_id: ID of the run to stop
        """
        logger.info(f"Executing auto-stop for run {run_id}")

        # Clean up job tracking
        self._auto_stop_jobs.pop(run_id, None)

        # Check if this run is still active
        status = await self.state_machine.get_generator_status()
        if status.current_run_id != run_id:
            logger.debug(
                f"Run {run_id} is no longer active, skipping auto-stop"
            )
            return

        # Stop the generator
        await self.state_machine.stop_generator("scheduled_end")

    def cancel_auto_stop(self, run_id: int) -> bool:
        """
        Cancel scheduled auto-stop for a run.

        Args:
            run_id: ID of the run

        Returns:
            True if cancelled, False if not found
        """
        job_id = self._auto_stop_jobs.pop(run_id, None)
        if job_id and self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info(f"Cancelled auto-stop for run {run_id}")
            return True
        return False

    async def update_schedule(self, schedule: ScheduledRun) -> None:
        """Update or add a schedule."""
        await self.add_schedule(schedule)

    def remove_schedule(self, schedule_id: int) -> None:
        """Remove a schedule from the scheduler."""
        job_id = f"schedule_{schedule_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed schedule {schedule_id} from scheduler")

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
