# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/slave_client.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""HTTP client for GenSlave API communication."""

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SlaveResponse:
    """Response from GenSlave API."""

    success: bool
    status_code: Optional[int] = None
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class SlaveClient:
    """
    HTTP client for communicating with GenSlave API.

    All requests include the X-GenControl-Secret header for authentication.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize GenSlave client.

        Args:
            base_url: GenSlave API URL (default from settings)
            secret: API secret (default from settings)
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or settings.slave_api_url).rstrip("/")
        self.secret = secret or settings.slave_api_secret
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            # Use explicit timeout configuration to prevent event loop blocking.
            # connect=2.0 ensures we fail fast if GenSlave is unreachable.
            # The total timeout (self.timeout) is the overall request limit.
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    timeout=self.timeout,  # Total timeout for entire request
                    connect=2.0,  # Strict connect timeout - fail fast on network issues
                ),
                headers={"X-API-Key": self.secret},
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict] = None,
    ) -> SlaveResponse:
        """Make HTTP request to GenSlave."""
        url = f"{self.base_url}{path}"
        start = time.perf_counter()

        try:
            client = await self._get_client()
            response = await client.request(method, url, json=json)
            latency = (time.perf_counter() - start) * 1000

            if response.status_code >= 400:
                return SlaveResponse(
                    success=False,
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}: {response.text}",
                    latency_ms=latency,
                )

            return SlaveResponse(
                success=True,
                status_code=response.status_code,
                data=response.json() if response.text else None,
                latency_ms=latency,
            )

        except httpx.TimeoutException:
            latency = (time.perf_counter() - start) * 1000
            logger.warning(f"Request to {url} timed out after {latency:.1f}ms")
            return SlaveResponse(
                success=False,
                error="Request timed out",
                latency_ms=latency,
            )

        except httpx.RequestError as e:
            latency = (time.perf_counter() - start) * 1000
            logger.warning(f"Request to {url} failed: {e}")
            return SlaveResponse(
                success=False,
                error=str(e),
                latency_ms=latency,
            )

        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            logger.error(f"Unexpected error requesting {url}: {e}")
            return SlaveResponse(
                success=False,
                error=str(e),
                latency_ms=latency,
            )

    # =========================================================================
    # API Methods
    # =========================================================================

    async def get_status(self) -> SlaveResponse:
        """Get GenSlave status."""
        return await self._request("GET", "/api/status")

    async def relay_on(self) -> SlaveResponse:
        """Turn relay ON (start generator)."""
        logger.info("Sending relay ON command to GenSlave")
        return await self._request("POST", "/api/relay/on")

    async def relay_off(self) -> SlaveResponse:
        """Turn relay OFF (stop generator)."""
        logger.info("Sending relay OFF command to GenSlave")
        return await self._request("POST", "/api/relay/off")

    async def get_relay_state(self) -> SlaveResponse:
        """Get current relay state."""
        return await self._request("GET", "/api/relay/state")

    async def arm_relay(self) -> SlaveResponse:
        """Arm the relay (enable remote generator control)."""
        logger.info("Sending ARM command to GenSlave")
        return await self._request("POST", "/api/relay/arm")

    async def disarm_relay(self) -> SlaveResponse:
        """Disarm the relay (disable remote generator control)."""
        logger.info("Sending DISARM command to GenSlave")
        return await self._request("POST", "/api/relay/disarm")

    async def heartbeat(
        self,
        timestamp: int,
        generator_running: bool,
        armed: bool,
        heartbeat_interval: int = 60,
        command: str = "none",
    ) -> SlaveResponse:
        """
        Send heartbeat to GenSlave.

        Args:
            timestamp: Current Unix timestamp
            generator_running: Whether generator is currently running
            armed: Whether automation is armed
            heartbeat_interval: Interval between heartbeats in seconds
            command: Command to execute ("start", "stop", or "none")

        Returns:
            Response with GenSlave status
        """
        return await self._request(
            "POST",
            "/api/heartbeat",
            json={
                "timestamp": timestamp,
                "heartbeat_interval": heartbeat_interval,
                "generator_running": generator_running,
                "command": command,
                "armed": armed,
            },
        )

    async def get_system_health(self) -> SlaveResponse:
        """Get GenSlave system health metrics."""
        return await self._request("GET", "/api/system")

    async def get_health_status(self) -> SlaveResponse:
        """Get GenSlave quick health check."""
        return await self._request("GET", "/api/health")

    async def get_failsafe_status(self) -> SlaveResponse:
        """Get GenSlave failsafe status."""
        return await self._request("GET", "/api/failsafe")

    async def push_config(self, config: dict[str, Any]) -> SlaveResponse:
        """
        Push configuration to GenSlave.

        Args:
            config: Configuration values to push

        Returns:
            Response indicating success/failure
        """
        return await self._request("POST", "/api/config", json=config)

    async def rotate_api_key(self, new_key: str) -> SlaveResponse:
        """
        Rotate the API key on GenSlave.

        Args:
            new_key: New API key (minimum 16 characters)

        Returns:
            Response indicating success/failure
        """
        return await self._request("POST", "/api/system/rotate-key", json={"new_key": new_key})

    # =========================================================================
    # Notification Management
    # =========================================================================

    async def get_notifications(self) -> SlaveResponse:
        """
        Get GenSlave notification configuration.

        Returns:
            Response with notification config (apprise_urls, configured, enabled).
        """
        return await self._request("GET", "/api/system/notifications")

    async def set_notifications(self, apprise_urls: list[str]) -> SlaveResponse:
        """
        Update GenSlave Apprise notification URLs.

        Args:
            apprise_urls: List of Apprise URL strings.

        Returns:
            Response indicating success/failure.
        """
        logger.info(f"Updating GenSlave notification URLs: {len(apprise_urls)} URLs")
        return await self._request(
            "POST",
            "/api/system/notifications",
            json={"apprise_urls": apprise_urls},
        )

    async def get_notification_settings(self) -> SlaveResponse:
        """
        Get GenSlave notification cooldown settings.

        Returns:
            Response with cooldown settings (failsafe_cooldown_minutes,
            restored_cooldown_minutes, last notification timestamps).
        """
        return await self._request("GET", "/api/system/notifications/settings")

    async def set_notification_settings(
        self,
        failsafe_cooldown_minutes: Optional[int] = None,
        restored_cooldown_minutes: Optional[int] = None,
    ) -> SlaveResponse:
        """
        Update GenSlave notification cooldown settings.

        Args:
            failsafe_cooldown_minutes: Cooldown for failsafe notifications (1-60 min).
            restored_cooldown_minutes: Cooldown for restored notifications (1-60 min).

        Returns:
            Response indicating success/failure.
        """
        payload = {}
        if failsafe_cooldown_minutes is not None:
            payload["failsafe_cooldown_minutes"] = failsafe_cooldown_minutes
        if restored_cooldown_minutes is not None:
            payload["restored_cooldown_minutes"] = restored_cooldown_minutes

        logger.info(f"Updating GenSlave notification settings: {payload}")
        return await self._request(
            "POST",
            "/api/system/notifications/settings",
            json=payload,
        )

    async def test_notifications(self) -> SlaveResponse:
        """
        Send a test notification from GenSlave.

        Returns:
            Response indicating success/failure.
        """
        logger.info("Sending test notification request to GenSlave")
        return await self._request("POST", "/api/system/notifications/test")

    async def set_notifications_enabled(self, enabled: bool) -> SlaveResponse:
        """
        Enable or disable GenSlave notifications.

        Args:
            enabled: True to enable, False to disable.

        Returns:
            Response indicating success/failure.
        """
        state = "enabled" if enabled else "disabled"
        logger.info(f"Setting GenSlave notifications {state}")
        return await self._request(
            "POST",
            "/api/system/notifications/enable",
            json={"enabled": enabled},
        )

    async def clear_notification_cooldown(
        self, event_type: Optional[str] = None
    ) -> SlaveResponse:
        """
        Clear GenSlave notification cooldown state.

        Args:
            event_type: "failsafe", "restored", or None for both.

        Returns:
            Response indicating success/failure.
        """
        logger.info(f"Clearing GenSlave notification cooldown: {event_type or 'all'}")
        return await self._request(
            "POST",
            "/api/system/notifications/clear-cooldown",
            json={"event_type": event_type},
        )

    # =========================================================================
    # WiFi Configuration
    # =========================================================================

    async def scan_wifi_networks(self) -> SlaveResponse:
        """
        Scan for available WiFi networks on GenSlave.

        Returns:
            Response with list of networks (ssid, signal_percent, security).
        """
        return await self._request("GET", "/api/system/wifi/networks")

    async def connect_wifi(self, ssid: str, password: Optional[str] = None) -> SlaveResponse:
        """
        Connect GenSlave to a WiFi network.

        Args:
            ssid: WiFi network SSID.
            password: WiFi password (None for open networks).

        Returns:
            Response indicating success/failure.
        """
        # Don't log password
        logger.info(f"Requesting GenSlave WiFi connection to: {ssid}")
        return await self._request(
            "POST",
            "/api/system/wifi/connect",
            json={"ssid": ssid, "password": password},
        )

    async def list_saved_wifi_networks(self) -> SlaveResponse:
        """
        List saved WiFi network profiles on GenSlave.

        Returns:
            Response with list of saved networks.
        """
        return await self._request("GET", "/api/system/wifi/saved")

    async def add_wifi_network(self, ssid: str, password: str, auto_connect: bool = True) -> SlaveResponse:
        """
        Add a known WiFi network to GenSlave for auto-connect.

        Args:
            ssid: WiFi network SSID.
            password: WiFi password.
            auto_connect: Whether to auto-connect when available.

        Returns:
            Response indicating success/failure.
        """
        # Don't log password
        logger.info(f"Adding known WiFi network to GenSlave: {ssid}")
        return await self._request(
            "POST",
            "/api/system/wifi/add",
            json={"ssid": ssid, "password": password, "auto_connect": auto_connect},
        )

    async def delete_wifi_network(self, name: str) -> SlaveResponse:
        """
        Delete a saved WiFi network from GenSlave.

        Args:
            name: Connection profile name to delete.

        Returns:
            Response indicating success/failure.
        """
        logger.info(f"Deleting WiFi network from GenSlave: {name}")
        return await self._request(
            "POST",
            "/api/system/wifi/delete",
            json={"name": name},
        )

    # =========================================================================
    # System Power Control
    # =========================================================================

    async def shutdown(self) -> SlaveResponse:
        """
        Shutdown GenSlave (Raspberry Pi).

        This will shut down the Raspberry Pi running GenSlave.
        The relay will be turned off for safety before shutdown.

        Returns:
            Response indicating success/failure.
        """
        logger.warning("Sending SHUTDOWN command to GenSlave")
        return await self._request("POST", "/api/system/shutdown")

    async def reboot(self) -> SlaveResponse:
        """
        Reboot GenSlave (Raspberry Pi).

        This will reboot the Raspberry Pi running GenSlave.
        The relay will be turned off for safety during the reboot.

        Returns:
            Response indicating success/failure.
        """
        logger.warning("Sending REBOOT command to GenSlave")
        return await self._request("POST", "/api/system/reboot")
