# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/heartbeat.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Heartbeat service for GenSlave communication."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from app.config import settings
from app.services.slave_client import SlaveClient

if TYPE_CHECKING:
    from app.services.state_machine import StateMachine

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatResult:
    """Result of a heartbeat attempt."""

    success: bool
    latency_ms: Optional[float] = None
    slave_status: Optional[dict] = None
    error: Optional[str] = None


class HeartbeatService:
    """
    Sends periodic heartbeats to GenSlave.

    Heartbeats serve to:
    - Verify GenSlave is reachable
    - Synchronize state between master and slave
    - Detect communication failures
    """

    def __init__(
        self,
        state_machine: "StateMachine",
        interval_seconds: Optional[int] = None,
    ):
        """
        Initialize heartbeat service.

        Args:
            state_machine: StateMachine to update with heartbeat status
            interval_seconds: Seconds between heartbeats (default from settings)
        """
        self.state_machine = state_machine
        self.interval = interval_seconds or settings.heartbeat_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._sequence = 0
        self._client = SlaveClient()

    async def start(self) -> None:
        """Start the heartbeat loop."""
        if self._running:
            logger.warning("Heartbeat service already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat service started (interval: {self.interval}s)")

    async def stop(self) -> None:
        """Stop the heartbeat loop."""
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        await self._client.close()
        logger.info("Heartbeat service stopped")

    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def _send_heartbeat(self) -> HeartbeatResult:
        """Send a single heartbeat."""
        self._sequence += 1
        timestamp = int(time.time())

        # Get current master state to send
        generator_status = await self.state_machine.get_generator_status()
        is_armed = await self.state_machine.is_armed()

        # Send heartbeat with armed state
        response = await self._client.heartbeat(
            timestamp=timestamp,
            generator_running=generator_status.running,
            armed=is_armed,
            command="none",  # Commands are sent separately, not via heartbeat
        )

        # Build result
        result = HeartbeatResult(
            success=response.success,
            latency_ms=response.latency_ms,
            slave_status=response.data,
            error=response.error,
        )

        # Update state machine
        await self.state_machine.update_heartbeat_status(
            success=result.success,
            slave_status=result.slave_status,
            latency_ms=result.latency_ms,
        )

        if result.success:
            logger.debug(
                f"Heartbeat #{self._sequence} successful "
                f"(latency: {result.latency_ms:.1f}ms)"
            )
        else:
            logger.warning(f"Heartbeat #{self._sequence} failed: {result.error}")

        return result

    async def send_test_heartbeat(self) -> HeartbeatResult:
        """Send a single test heartbeat (doesn't affect sequence)."""
        timestamp = int(time.time())

        generator_status = await self.state_machine.get_generator_status()
        is_armed = await self.state_machine.is_armed()

        response = await self._client.heartbeat(
            timestamp=timestamp,
            generator_running=generator_status.running,
            armed=is_armed,
            command="none",
        )

        return HeartbeatResult(
            success=response.success,
            latency_ms=response.latency_ms,
            slave_status=response.data,
            error=response.error,
        )

    @property
    def is_running(self) -> bool:
        """Check if heartbeat service is running."""
        return self._running

    @property
    def sequence(self) -> int:
        """Get current sequence number."""
        return self._sequence
