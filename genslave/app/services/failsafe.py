# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/failsafe.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Failsafe monitor for GenSlave - stops generator if GenMaster communication lost."""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.config import settings
from app.services.notification import notification_service

logger = logging.getLogger(__name__)


class FailsafeMonitor:
    """
    Independent failsafe monitor that stops the generator if GenMaster
    communication is lost.

    This runs as a background task and:
    1. Tracks the last heartbeat received from GenMaster
    2. If no heartbeat for FAILSAFE_TIMEOUT_SECONDS, triggers failsafe
    3. Failsafe action: Turn relay OFF and send backup webhook

    The failsafe only triggers when automation is armed. When disarmed,
    the monitor still tracks heartbeats but does not take action.
    """

    def __init__(self):
        """Initialize failsafe monitor."""
        self._last_heartbeat: Optional[int] = None
        self._heartbeat_count: int = 0
        self._failsafe_triggered: bool = False
        self._failsafe_triggered_at: Optional[int] = None
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._relay_service = None  # Set by set_relay_service
        # Dynamic timeout: updated from GenMaster's heartbeat_interval * 3
        # Falls back to settings.FAILSAFE_TIMEOUT_SECONDS if not received
        self._dynamic_timeout: Optional[int] = None
        self._heartbeat_interval: Optional[int] = None

    def set_relay_service(self, relay_service) -> None:
        """Set the relay service for failsafe actions."""
        self._relay_service = relay_service

    def record_heartbeat(self, data: dict) -> dict:
        """
        Record a heartbeat from GenMaster.

        Args:
            data: Heartbeat data from GenMaster

        Returns:
            Response with current state
        """
        now = int(time.time())
        self._last_heartbeat = now
        self._heartbeat_count += 1

        # Update dynamic timeout from GenMaster's heartbeat interval
        heartbeat_interval = data.get("heartbeat_interval")
        if heartbeat_interval is not None and heartbeat_interval > 0:
            new_timeout = heartbeat_interval * 3
            if new_timeout != self._dynamic_timeout:
                logger.info(
                    f"Failsafe timeout updated: {self._dynamic_timeout or settings.FAILSAFE_TIMEOUT_SECONDS}s -> "
                    f"{new_timeout}s (heartbeat_interval={heartbeat_interval}s)"
                )
                self._dynamic_timeout = new_timeout
                self._heartbeat_interval = heartbeat_interval

        # Clear failsafe if it was triggered
        if self._failsafe_triggered:
            logger.info("Heartbeat received - clearing failsafe state")
            self._failsafe_triggered = False
            self._failsafe_triggered_at = None

            # Check if relay needs to be re-armed and send notification
            if self._relay_service and not self._relay_service.is_armed:
                logger.info("Relay is disarmed after failsafe recovery - sending reminder notification")
                asyncio.create_task(notification_service.send_heartbeat_restored_alert())

        # Process command if present and armed
        command = data.get("command", "none")
        if command != "none" and self._relay_service:
            if self._relay_service.is_armed:
                if command == "start":
                    self._relay_service.relay_on()
                elif command == "stop":
                    self._relay_service.relay_off()
            else:
                logger.info(f"Command '{command}' received but not armed - ignoring")

        relay_state = self._relay_service.get_state() if self._relay_service else False

        return {
            "relay_state": relay_state,
            "uptime": self._get_uptime(),
            "failsafe_active": self._failsafe_triggered,
            "heartbeat_count": self._heartbeat_count,
            "armed": self._relay_service.is_armed if self._relay_service else False,
        }

    def _get_uptime(self) -> int:
        """Get system uptime in seconds."""
        try:
            with open("/proc/uptime", "r") as f:
                return int(float(f.read().split()[0]))
        except Exception:
            return 0

    async def start(self) -> None:
        """Start the failsafe monitor background task."""
        if self._running:
            logger.warning("Failsafe monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Failsafe monitor started (timeout: {settings.FAILSAFE_TIMEOUT_SECONDS}s)"
        )

    async def stop(self) -> None:
        """Stop the failsafe monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Failsafe monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        check_interval = 5  # Check every 5 seconds

        while self._running:
            try:
                await asyncio.sleep(check_interval)
                await self._check_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in failsafe monitor: {e}")

    def _get_effective_timeout(self) -> int:
        """Get the effective failsafe timeout.

        Returns dynamic timeout if set from GenMaster, otherwise falls back
        to settings.FAILSAFE_TIMEOUT_SECONDS.
        """
        if self._dynamic_timeout is not None:
            return self._dynamic_timeout
        return settings.FAILSAFE_TIMEOUT_SECONDS

    async def _check_heartbeat(self) -> None:
        """Check if heartbeat has timed out."""
        if self._last_heartbeat is None:
            # No heartbeat received yet - still in startup grace period
            return

        if self._failsafe_triggered:
            # Already in failsafe state
            return

        # Check if automation is armed
        if self._relay_service and not self._relay_service.is_armed:
            # Not armed - don't trigger failsafe
            return

        elapsed = int(time.time()) - self._last_heartbeat
        timeout = self._get_effective_timeout()

        if elapsed > timeout:
            await self._trigger_failsafe()

    async def _trigger_failsafe(self) -> None:
        """Trigger failsafe action - stop the generator."""
        timeout = self._get_effective_timeout()
        logger.warning(
            f"FAILSAFE TRIGGERED - No heartbeat for {timeout}s"
        )

        self._failsafe_triggered = True
        self._failsafe_triggered_at = int(time.time())

        # Turn off relay (force=True to bypass armed check)
        if self._relay_service:
            success = self._relay_service.relay_off(force=True)
            logger.info(f"Failsafe relay OFF: {'success' if success else 'failed'}")

        # Send notifications via Apprise (primary method)
        await notification_service.send_failsafe_alert(settings.FAILSAFE_TIMEOUT_SECONDS)

        # Send legacy webhook notification (if configured)
        await self._send_failsafe_webhook()

    async def _send_failsafe_webhook(self) -> None:
        """Send legacy webhook notification about failsafe trigger.

        This is kept for backwards compatibility. New installations
        should use Apprise notifications instead.
        """
        if not settings.WEBHOOK_URL:
            logger.debug("No webhook URL configured for failsafe notification")
            return

        payload = {
            "event": "genslave.failsafe.triggered",
            "timestamp": int(time.time()),
            "data": {
                "last_heartbeat": self._last_heartbeat,
                "timeout_seconds": self._get_effective_timeout(),
                "heartbeat_interval": self._heartbeat_interval,
            },
            "source": "genslave",
        }

        if settings.WEBHOOK_SECRET:
            payload["secret"] = settings.WEBHOOK_SECRET

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(settings.WEBHOOK_URL, json=payload)
                if response.status_code == 200:
                    logger.info("Failsafe webhook sent successfully")
                else:
                    logger.warning(
                        f"Failsafe webhook returned status {response.status_code}"
                    )
        except Exception as e:
            logger.error(f"Failed to send failsafe webhook: {e}")

    def get_status(self) -> dict:
        """Get failsafe monitor status."""
        now = int(time.time())
        seconds_since_heartbeat = None
        if self._last_heartbeat:
            seconds_since_heartbeat = now - self._last_heartbeat

        return {
            "running": self._running,
            "last_heartbeat": self._last_heartbeat,
            "seconds_since_heartbeat": seconds_since_heartbeat,
            "heartbeat_count": self._heartbeat_count,
            "failsafe_triggered": self._failsafe_triggered,
            "failsafe_triggered_at": self._failsafe_triggered_at,
            "timeout_seconds": self._get_effective_timeout(),
            "heartbeat_interval": self._heartbeat_interval,
            "timeout_source": "genmaster" if self._dynamic_timeout else "config",
        }


# Global failsafe monitor instance
failsafe_monitor = FailsafeMonitor()
