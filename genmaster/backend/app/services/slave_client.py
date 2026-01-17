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
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"X-GenControl-Secret": self.secret},
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

    async def heartbeat(
        self,
        timestamp: int,
        generator_running: bool,
        armed: bool,
        command: str = "none",
    ) -> SlaveResponse:
        """
        Send heartbeat to GenSlave.

        Args:
            timestamp: Current Unix timestamp
            generator_running: Whether generator is currently running
            armed: Whether automation is armed
            command: Command to execute ("start", "stop", or "none")

        Returns:
            Response with GenSlave status
        """
        return await self._request(
            "POST",
            "/api/heartbeat",
            json={
                "timestamp": timestamp,
                "generator_running": generator_running,
                "command": command,
                "armed": armed,
            },
        )

    async def get_system_health(self) -> SlaveResponse:
        """Get GenSlave system health metrics."""
        return await self._request("GET", "/api/system")

    async def push_config(self, config: dict[str, Any]) -> SlaveResponse:
        """
        Push configuration to GenSlave.

        Args:
            config: Configuration values to push

        Returns:
            Response indicating success/failure
        """
        return await self._request("POST", "/api/config", json=config)
