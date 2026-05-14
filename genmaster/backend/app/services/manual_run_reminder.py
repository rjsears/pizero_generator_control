# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/manual_run_reminder.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - May 14th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Background timer that reminds the operator about long manual runs.

While a manual (web Start button) or HOA-Run-switch generator run is
active, this service fires the `manual_run_reminder` notification at each
N-hour milestone — N being the operator-configured interval
(`config.manual_run_reminder_interval_hours`, failsafe.md decision #1
default 2h). The point is to catch the "operator started the generator
and forgot about it" case.

Only operator-initiated runs are tracked: `manual` and
`local_switch_genmaster`. Automation runs (Victron / scheduled /
exercise) have their own runtime-limit handling and aren't subject to
this reminder.

Milestone tracking is in-memory, keyed by run_id. A GenMaster restart
resets it — so the first check after a restart can re-send a reminder
for the current milestone of an in-progress run. That's acceptable: a
stale "still running" nudge after a restart is harmless and arguably
useful.
"""

import asyncio
import logging
import time
from typing import Optional

from app.database import AsyncSessionLocal
from app.models import Config, SystemState

logger = logging.getLogger(__name__)


class ManualRunReminderService:
    """Periodic reminder timer for long-running manual generator runs."""

    # How often to check. Coarse on purpose — the reminder is a "you
    # forgot" nudge, not a precise alarm, so checking every 5 minutes is
    # plenty and keeps DB load negligible.
    CHECK_INTERVAL_SEC = 300

    # Run triggers this reminder applies to — operator-initiated runs
    # with no built-in end time, where the operator could genuinely
    # forget the generator is running.
    MANUAL_TRIGGERS = ("manual", "local_switch_genmaster")

    def __init__(self, state_machine):
        self._state_machine = state_machine
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        # run_id -> highest N-hour milestone already notified for that run
        self._last_reminded: dict[int, int] = {}

    async def start(self) -> None:
        """Start the background reminder loop. Idempotent."""
        if self._running:
            logger.warning("Manual run reminder service already running")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            f"Manual run reminder service started "
            f"(check interval: {self.CHECK_INTERVAL_SEC}s)"
        )

    async def stop(self) -> None:
        """Stop the background reminder loop. Idempotent."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Manual run reminder service stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.CHECK_INTERVAL_SEC)
                await self._check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in manual run reminder loop: {e}")

    async def _check(self) -> None:
        """One reminder-check cycle."""
        async with AsyncSessionLocal() as db:
            config = await Config.get_instance(db)
            state = await SystemState.get_instance(db)

            if not config.manual_run_reminder_enabled:
                return

            if not state.generator_running:
                # Run ended (or never started) — drop stale milestone state.
                self._last_reminded.clear()
                return

            if state.run_trigger not in self.MANUAL_TRIGGERS:
                # Automation-triggered run — not our concern.
                return

            if state.generator_start_time is None or state.current_run_id is None:
                return

            interval_hours = max(1, config.manual_run_reminder_interval_hours)
            run_id = state.current_run_id
            elapsed_hours = (
                int(time.time()) - state.generator_start_time
            ) / 3600.0
            milestone = int(elapsed_hours // interval_hours)

        # Haven't crossed the first interval boundary yet.
        if milestone < 1:
            return

        # Already reminded for this milestone (or a later one).
        if self._last_reminded.get(run_id, 0) >= milestone:
            return

        # New milestone crossed — fire the reminder, record it, and prune
        # tracking down to just this run.
        self._last_reminded = {run_id: milestone}
        hours = milestone * interval_hours
        await self._state_machine._trigger_system_notification(
            "manual_run_reminder", {"hours": hours}
        )
        logger.info(
            f"Manual run reminder fired: run {run_id} active "
            f"~{hours}h (milestone {milestone}, interval {interval_hours}h)"
        )
