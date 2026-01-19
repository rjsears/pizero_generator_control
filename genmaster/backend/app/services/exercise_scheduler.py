# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/exercise_scheduler.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Exercise scheduler service for automatic generator exercise runs."""

import asyncio
import logging
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional

from app.database import AsyncSessionLocal
from app.models import ExerciseSchedule, SystemState

if TYPE_CHECKING:
    from app.services.scheduler import SchedulerService
    from app.services.state_machine import StateMachine

logger = logging.getLogger(__name__)


class ExerciseSchedulerService:
    """
    Background service that monitors and triggers scheduled exercise runs.

    Checks every minute if an exercise should be started based on:
    - Exercise schedule is enabled
    - Current date >= next_exercise_date
    - Current time >= start_time
    - Generator is not already running
    - Relay is armed
    """

    def __init__(
        self,
        state_machine: "StateMachine",
        scheduler_service: "SchedulerService",
    ):
        """
        Initialize exercise scheduler service.

        Args:
            state_machine: StateMachine for generator control
            scheduler_service: SchedulerService for auto-stop scheduling
        """
        self.state_machine = state_machine
        self.scheduler_service = scheduler_service
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 60  # Check every minute

    async def start(self) -> None:
        """Start the exercise scheduler background task."""
        if self._running:
            logger.warning("Exercise scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Exercise scheduler service started")

    async def stop(self) -> None:
        """Stop the exercise scheduler background task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Exercise scheduler service stopped")

    async def _run_loop(self) -> None:
        """Main loop that checks for exercise runs."""
        while self._running:
            try:
                await self._check_and_trigger_exercise()
            except Exception as e:
                logger.error(f"Error in exercise scheduler loop: {e}")

            # Wait before next check
            await asyncio.sleep(self._check_interval)

    async def _check_and_trigger_exercise(self) -> None:
        """Check if an exercise should be triggered and start it if so."""
        async with AsyncSessionLocal() as db:
            # Get exercise schedule
            schedule = await ExerciseSchedule.get_instance(db)

            # Skip if not enabled
            if not schedule.enabled:
                return

            # Skip if no next exercise date set
            if not schedule.next_exercise_date:
                # Calculate and set it
                schedule.next_exercise_date = schedule.calculate_next_exercise()
                await db.commit()
                return

            # Check if today is the exercise day
            today = date.today()
            if today < schedule.next_exercise_date:
                return

            # Check if current time is past the start time
            now = datetime.now().time()
            try:
                parts = schedule.start_time.split(":")
                start_time = time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                logger.error(f"Invalid start_time format: {schedule.start_time}")
                return

            if now < start_time:
                return

            # Check if generator is already running
            status = await self.state_machine.get_generator_status()
            if status.running:
                logger.debug("Generator already running, skipping exercise")
                return

            # Check if relay is armed
            state = await SystemState.get_instance(db)
            if not state.slave_relay_armed:
                logger.debug("Relay not armed, skipping exercise")
                return

            # All conditions met - start exercise
            logger.info("Starting scheduled exercise run")
            try:
                run = await self.state_machine.start_generator(
                    trigger="exercise",
                    notes=f"Scheduled exercise ({schedule.duration_minutes} minutes)",
                )

                # Schedule auto-stop
                await self.scheduler_service.schedule_auto_stop(
                    run.id, schedule.duration_minutes, stop_reason="exercise_end"
                )

                # Update exercise tracking
                schedule.update_after_exercise()
                await db.commit()

                logger.info(
                    f"Exercise run {run.id} started, "
                    f"next exercise scheduled for {schedule.next_exercise_date}"
                )

            except ValueError as e:
                logger.warning(f"Could not start exercise: {e}")

    @property
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running
