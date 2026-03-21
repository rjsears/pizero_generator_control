# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/reboot_scheduler.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - March 2026
#
# Scheduled reboot service for GenSlave
# Configurable via GenMaster UI
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Scheduled reboot service for GenSlave maintenance."""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from typing import Optional

from app.services.database import db_service

logger = logging.getLogger(__name__)


# Day name to weekday number mapping (Monday=0, Sunday=6)
DAY_MAP = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "daily": -1,  # Special value for daily
}


class RebootScheduler:
    """Handles scheduled maintenance reboots.

    Runs as a background asyncio task, checking every minute if
    it's time to perform a scheduled reboot. Only reboots if
    the generator relay is OFF (safe to reboot).

    Configuration is stored in the SQLite database and can be
    updated via API without container restart.
    """

    # Database keys
    DB_KEY = "reboot_schedule"

    # Check interval (seconds)
    CHECK_INTERVAL = 60

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._relay_service = None  # Set during start()
        self._last_reboot_date: Optional[str] = None  # Prevent multiple reboots same day

    def get_schedule(self) -> dict:
        """Get current reboot schedule configuration.

        Returns:
            dict with keys: enabled, day, hour, minute
        """
        raw = db_service.get_setting(self.DB_KEY)
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                logger.error(f"Invalid reboot schedule JSON: {raw}")

        # Default: disabled, Sunday 4:00 AM
        return {
            "enabled": False,
            "day": "sunday",
            "hour": 4,
            "minute": 0,
        }

    def set_schedule(
        self,
        enabled: bool,
        day: str,
        hour: int,
        minute: int,
    ) -> bool:
        """Set reboot schedule configuration.

        Args:
            enabled: Whether scheduled reboots are enabled
            day: Day of week (monday-sunday) or "daily"
            hour: Hour (0-23)
            minute: Minute (0-59)

        Returns:
            True if successful
        """
        # Validate day
        day_lower = day.lower()
        if day_lower not in DAY_MAP:
            logger.error(f"Invalid day: {day}")
            return False

        # Validate hour/minute
        if not (0 <= hour <= 23):
            logger.error(f"Invalid hour: {hour}")
            return False
        if not (0 <= minute <= 59):
            logger.error(f"Invalid minute: {minute}")
            return False

        schedule = {
            "enabled": enabled,
            "day": day_lower,
            "hour": hour,
            "minute": minute,
        }

        success = db_service.set_setting(self.DB_KEY, json.dumps(schedule))
        if success:
            logger.info(
                f"Reboot schedule updated: enabled={enabled}, "
                f"day={day_lower}, time={hour:02d}:{minute:02d}"
            )
        return success

    def set_enabled(self, enabled: bool) -> bool:
        """Enable or disable scheduled reboots.

        Args:
            enabled: True to enable, False to disable

        Returns:
            True if successful
        """
        schedule = self.get_schedule()
        schedule["enabled"] = enabled
        success = db_service.set_setting(self.DB_KEY, json.dumps(schedule))
        if success:
            logger.info(f"Scheduled reboot {'enabled' if enabled else 'disabled'}")
        return success

    def _is_reboot_time(self) -> bool:
        """Check if current time matches the scheduled reboot time.

        Returns:
            True if it's time to reboot
        """
        schedule = self.get_schedule()

        if not schedule.get("enabled"):
            return False

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Already rebooted today?
        if self._last_reboot_date == today_str:
            return False

        # Check day
        scheduled_day = schedule.get("day", "sunday")
        if scheduled_day != "daily":
            target_weekday = DAY_MAP.get(scheduled_day, 6)
            if now.weekday() != target_weekday:
                return False

        # Check time (within the check interval window)
        scheduled_hour = schedule.get("hour", 4)
        scheduled_minute = schedule.get("minute", 0)

        if now.hour != scheduled_hour:
            return False

        if now.minute != scheduled_minute:
            return False

        return True

    def _is_safe_to_reboot(self) -> bool:
        """Check if it's safe to reboot (generator not running).

        Returns:
            True if relay is OFF (safe to reboot)
        """
        if self._relay_service is None:
            logger.warning("Relay service not available - assuming unsafe")
            return False

        relay_state = self._relay_service.get_state()
        if relay_state:
            logger.info("Generator relay is ON - not safe to reboot")
            return False

        return True

    def _execute_reboot(self) -> None:
        """Execute the system reboot."""
        logger.warning("Executing scheduled maintenance reboot")

        # Turn off relay as safety measure
        if self._relay_service:
            self._relay_service.relay_off(force=True)
            logger.info("Relay turned OFF before reboot")

        # Mark that we're rebooting today (prevents duplicate attempts)
        self._last_reboot_date = datetime.now().strftime("%Y-%m-%d")

        # Schedule reboot with delay to allow logging
        try:
            subprocess.Popen(
                ["sudo", "reboot"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as e:
            logger.error(f"Failed to execute reboot: {e}")

    async def start(self, relay_service) -> None:
        """Start the reboot scheduler background task.

        Args:
            relay_service: The relay service instance for safety checks
        """
        if self._running:
            logger.warning("Reboot scheduler already running")
            return

        self._relay_service = relay_service
        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Reboot scheduler started")

    async def stop(self) -> None:
        """Stop the reboot scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Reboot scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop - checks every minute."""
        logger.info("Reboot scheduler loop started")

        while self._running:
            try:
                if self._is_reboot_time():
                    if self._is_safe_to_reboot():
                        self._execute_reboot()
                        # Exit loop - system is rebooting
                        break
                    else:
                        logger.info(
                            "Scheduled reboot time reached but generator is running - skipping"
                        )
                        # Mark as attempted so we don't keep trying
                        self._last_reboot_date = datetime.now().strftime("%Y-%m-%d")

            except Exception as e:
                logger.error(f"Error in reboot scheduler loop: {e}")

            await asyncio.sleep(self.CHECK_INTERVAL)

    def get_status(self) -> dict:
        """Get scheduler status for API.

        Returns:
            dict with schedule config and runtime status
        """
        schedule = self.get_schedule()
        return {
            **schedule,
            "running": self._running,
            "last_reboot_date": self._last_reboot_date,
            "next_reboot": self._get_next_reboot_time(),
        }

    def _get_next_reboot_time(self) -> Optional[str]:
        """Calculate the next scheduled reboot time.

        Returns:
            ISO format datetime string or None if disabled
        """
        schedule = self.get_schedule()
        if not schedule.get("enabled"):
            return None

        now = datetime.now()
        hour = schedule.get("hour", 4)
        minute = schedule.get("minute", 0)
        day = schedule.get("day", "sunday")

        # Start with today at the scheduled time
        next_reboot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if day == "daily":
            # If time already passed today, next is tomorrow
            if next_reboot <= now:
                next_reboot = next_reboot.replace(day=next_reboot.day + 1)
        else:
            # Find next occurrence of the scheduled day
            target_weekday = DAY_MAP.get(day, 6)
            days_ahead = target_weekday - now.weekday()
            if days_ahead < 0:  # Target day already passed this week
                days_ahead += 7
            elif days_ahead == 0 and next_reboot <= now:
                # Same day but time passed
                days_ahead = 7

            from datetime import timedelta
            next_reboot = next_reboot + timedelta(days=days_ahead)

        return next_reboot.isoformat()


# Global scheduler instance
reboot_scheduler = RebootScheduler()
