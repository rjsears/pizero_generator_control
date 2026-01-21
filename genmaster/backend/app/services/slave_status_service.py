# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/slave_status_service.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 20th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Background polling service for GenSlave status caching."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import settings
from app.services.redis_cache import get_cached_config
from app.services.slave_client import SlaveClient

logger = logging.getLogger(__name__)


async def _create_slave_client() -> SlaveClient:
    """Create a SlaveClient with config from Redis cache (or database fallback)."""
    config = await get_cached_config()

    if config:
        if config.get("genslave_ip"):
            base_url = f"http://{config['genslave_ip']}:8001"
        else:
            base_url = config.get("slave_api_url", settings.slave_api_url)
        return SlaveClient(
            base_url=base_url,
            secret=config.get("slave_api_secret", settings.slave_api_secret),
            timeout=5.0,  # Short timeout for status polling
        )
    else:
        return SlaveClient(
            base_url=settings.slave_api_url,
            secret=settings.slave_api_secret,
            timeout=5.0,
        )


@dataclass
class SlaveStatusCache:
    """Cached status data from GenSlave."""

    # Timestamps
    last_update: int = 0
    last_successful_fetch: int = 0

    # Connection status
    is_online: bool = False
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_latency_ms: Optional[float] = None

    # Cached data from GenSlave endpoints
    health: dict[str, Any] = field(default_factory=dict)
    relay_state: dict[str, Any] = field(default_factory=dict)
    failsafe: dict[str, Any] = field(default_factory=dict)
    system_info: dict[str, Any] = field(default_factory=dict)

    # Timestamps for individual data types
    health_updated: int = 0
    relay_state_updated: int = 0
    failsafe_updated: int = 0
    system_info_updated: int = 0


class SlaveStatusService:
    """
    Background service that polls GenSlave and caches results.

    This provides instant responses to the frontend by reading from cache,
    while keeping the cache fresh via background polling.
    """

    # Polling intervals
    FAST_POLL_INTERVAL = 1.0  # Health, relay state, failsafe
    SLOW_POLL_INTERVAL = 30.0  # System info (CPU, RAM, disk, etc.)

    # Offline detection
    OFFLINE_THRESHOLD = 3  # Consecutive failures before marking offline
    STALE_THRESHOLD = 5  # Seconds before data is considered stale

    def __init__(self):
        """Initialize the slave status service."""
        self._running = False
        self._fast_task: Optional[asyncio.Task] = None
        self._slow_task: Optional[asyncio.Task] = None
        self._cache = SlaveStatusCache()
        self._lock = asyncio.Lock()

    @property
    def cache(self) -> SlaveStatusCache:
        """Get the current cache."""
        return self._cache

    async def start(self) -> None:
        """Start the background polling loops."""
        if self._running:
            logger.warning("SlaveStatusService already running")
            return

        self._running = True
        self._fast_task = asyncio.create_task(self._fast_poll_loop())
        self._slow_task = asyncio.create_task(self._slow_poll_loop())
        logger.info(
            f"SlaveStatusService started "
            f"(fast: {self.FAST_POLL_INTERVAL}s, slow: {self.SLOW_POLL_INTERVAL}s)"
        )

    async def stop(self) -> None:
        """Stop the background polling loops."""
        if not self._running:
            return

        self._running = False

        for task in [self._fast_task, self._slow_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._fast_task = None
        self._slow_task = None
        logger.info("SlaveStatusService stopped")

    async def _fast_poll_loop(self) -> None:
        """Poll health, relay state, and failsafe every 1 second."""
        while self._running:
            try:
                await self._poll_fast_endpoints()
            except Exception as e:
                logger.error(f"Error in fast poll loop: {e}")

            await asyncio.sleep(self.FAST_POLL_INTERVAL)

    async def _slow_poll_loop(self) -> None:
        """Poll system info every 30 seconds."""
        while self._running:
            try:
                await self._poll_slow_endpoints()
            except Exception as e:
                logger.error(f"Error in slow poll loop: {e}")

            await asyncio.sleep(self.SLOW_POLL_INTERVAL)

    async def _poll_fast_endpoints(self) -> None:
        """Fetch health, relay state, and failsafe from GenSlave."""
        client = await _create_slave_client()
        now = int(time.time())

        try:
            # Poll all fast endpoints concurrently
            health_resp, relay_resp, failsafe_resp = await asyncio.gather(
                client.get_health_status(),
                client.get_relay_state(),
                client.get_failsafe_status(),
                return_exceptions=True,
            )

            async with self._lock:
                self._cache.last_update = now

                # Process health response
                if isinstance(health_resp, Exception):
                    self._handle_failure(str(health_resp))
                elif health_resp.success:
                    self._cache.health = health_resp.data or {}
                    self._cache.health_updated = now
                    self._cache.last_latency_ms = health_resp.latency_ms
                    self._mark_success(now)
                else:
                    self._handle_failure(health_resp.error)

                # Process relay state response
                if isinstance(relay_resp, Exception):
                    logger.debug(f"Relay state poll exception: {relay_resp}")
                elif relay_resp.success:
                    self._cache.relay_state = relay_resp.data or {}
                    self._cache.relay_state_updated = now
                else:
                    logger.debug(f"Relay state poll failed: {relay_resp.error}")

                # Process failsafe response
                if isinstance(failsafe_resp, Exception):
                    logger.debug(f"Failsafe poll exception: {failsafe_resp}")
                elif failsafe_resp.success:
                    self._cache.failsafe = failsafe_resp.data or {}
                    self._cache.failsafe_updated = now
                else:
                    logger.debug(f"Failsafe poll failed: {failsafe_resp.error}")

        finally:
            await client.close()

    async def _poll_slow_endpoints(self) -> None:
        """Fetch system info from GenSlave."""
        client = await _create_slave_client()
        now = int(time.time())

        try:
            response = await client.get_system_health()

            async with self._lock:
                if response.success:
                    self._cache.system_info = response.data or {}
                    self._cache.system_info_updated = now
                else:
                    logger.debug(f"System info poll failed: {response.error}")

        finally:
            await client.close()

    def _mark_success(self, timestamp: int) -> None:
        """Mark a successful fetch (must be called with lock held)."""
        self._cache.last_successful_fetch = timestamp
        self._cache.is_online = True
        self._cache.consecutive_failures = 0
        self._cache.last_error = None

    def _handle_failure(self, error: Optional[str]) -> None:
        """Handle a failed fetch (must be called with lock held)."""
        self._cache.consecutive_failures += 1
        self._cache.last_error = error

        if self._cache.consecutive_failures >= self.OFFLINE_THRESHOLD:
            if self._cache.is_online:
                logger.warning(
                    f"GenSlave marked offline after {self._cache.consecutive_failures} "
                    f"consecutive failures: {error}"
                )
            self._cache.is_online = False

    # =========================================================================
    # Public Cache Access Methods
    # =========================================================================

    def get_health(self) -> dict[str, Any]:
        """Get cached health data."""
        return self._cache.health.copy()

    def get_relay_state(self) -> dict[str, Any]:
        """Get cached relay state."""
        return self._cache.relay_state.copy()

    def get_failsafe(self) -> dict[str, Any]:
        """Get cached failsafe data."""
        return self._cache.failsafe.copy()

    def get_system_info(self) -> dict[str, Any]:
        """Get cached system info."""
        return self._cache.system_info.copy()

    def get_combined_status(self) -> dict[str, Any]:
        """Get all cached data in one response."""
        now = int(time.time())
        cache_age = now - self._cache.last_successful_fetch if self._cache.last_successful_fetch else None

        return {
            "is_online": self._cache.is_online,
            "is_stale": cache_age is not None and cache_age > self.STALE_THRESHOLD,
            "cache_age_seconds": cache_age,
            "last_error": self._cache.last_error,
            "last_latency_ms": self._cache.last_latency_ms,
            "consecutive_failures": self._cache.consecutive_failures,
            "data": {
                "health": self._cache.health,
                "relay_state": self._cache.relay_state,
                "failsafe": self._cache.failsafe,
                "system_info": self._cache.system_info,
            },
            "timestamps": {
                "last_update": self._cache.last_update,
                "last_successful_fetch": self._cache.last_successful_fetch,
                "health_updated": self._cache.health_updated,
                "relay_state_updated": self._cache.relay_state_updated,
                "failsafe_updated": self._cache.failsafe_updated,
                "system_info_updated": self._cache.system_info_updated,
            },
        }

    def is_online(self) -> bool:
        """Check if GenSlave is online."""
        return self._cache.is_online

    def is_stale(self) -> bool:
        """Check if cached data is stale."""
        if not self._cache.last_successful_fetch:
            return True
        age = int(time.time()) - self._cache.last_successful_fetch
        return age > self.STALE_THRESHOLD

    async def update_relay_state(
        self,
        relay_on: Optional[bool] = None,
        armed: Optional[bool] = None,
    ) -> None:
        """
        Immediately update the cached relay state after an action.

        Call this after successful arm/disarm or start/stop operations
        to update the cache immediately without waiting for next poll.

        Args:
            relay_on: New relay_on state (if changed)
            armed: New armed state (if changed)
        """
        async with self._lock:
            if relay_on is not None:
                self._cache.relay_state["relay_on"] = relay_on
            if armed is not None:
                self._cache.relay_state["armed"] = armed
            self._cache.relay_state_updated = int(time.time())

    async def force_refresh(self) -> dict[str, Any]:
        """
        Force an immediate refresh of all cached data.

        Returns the refreshed combined status.
        """
        await asyncio.gather(
            self._poll_fast_endpoints(),
            self._poll_slow_endpoints(),
        )
        return self.get_combined_status()


# =========================================================================
# Singleton Instance
# =========================================================================

_service_instance: Optional[SlaveStatusService] = None


def get_slave_status_service() -> SlaveStatusService:
    """Get or create the singleton SlaveStatusService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = SlaveStatusService()
    return _service_instance
