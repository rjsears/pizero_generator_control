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


async def _get_config_from_db():
    """Get config from database."""
    from app.database import AsyncSessionLocal
    from app.models import Config
    from sqlalchemy.future import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Config).where(Config.id == 1))
        return result.scalar_one_or_none()


async def _create_slave_client() -> SlaveClient:
    """Create a SlaveClient with config from database."""
    config = await _get_config_from_db()

    if config:
        # Use IP directly in URL if available
        if config.genslave_ip:
            base_url = f"http://{config.genslave_ip}:8001"
        else:
            base_url = config.slave_api_url
        return SlaveClient(
            base_url=base_url,
            secret=config.slave_api_secret,
        )
    else:
        # Fallback to settings
        return SlaveClient(
            base_url=settings.slave_api_url,
            secret=settings.slave_api_secret,
        )


async def _get_heartbeat_interval() -> int:
    """Get heartbeat interval from database config."""
    config = await _get_config_from_db()
    if config and config.heartbeat_interval_seconds:
        return config.heartbeat_interval_seconds
    return settings.heartbeat_interval_seconds


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
        self._client: Optional[SlaveClient] = None

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

        logger.info("Heartbeat service stopped")

    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                # Get current interval from database (allows dynamic updates)
                self.interval = await _get_heartbeat_interval()
                await self._send_heartbeat()
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def _send_heartbeat(self) -> HeartbeatResult:
        """Send a single heartbeat."""
        self._sequence += 1
        timestamp = int(time.time())

        # Create fresh client with current database config
        client = await _create_slave_client()

        # Get current master state to send
        generator_status = await self.state_machine.get_generator_status()
        is_armed = await self.state_machine.is_armed()

        # Send heartbeat with armed state and interval
        response = await client.heartbeat(
            timestamp=timestamp,
            generator_running=generator_status.running,
            armed=is_armed,
            heartbeat_interval=self.interval,
            command="none",  # Commands are sent separately, not via heartbeat
        )

        # Close the client after use
        await client.close()

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

        # Create fresh client with current database config
        client = await _create_slave_client()

        # Get current interval from database
        interval = await _get_heartbeat_interval()

        generator_status = await self.state_machine.get_generator_status()
        is_armed = await self.state_machine.is_armed()

        response = await client.heartbeat(
            timestamp=timestamp,
            generator_running=generator_status.running,
            armed=is_armed,
            heartbeat_interval=interval,
            command="none",
        )

        await client.close()

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
