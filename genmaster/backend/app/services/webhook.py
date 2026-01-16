# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/webhook.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Webhook service for sending notifications to n8n."""

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Config, EventLog

logger = logging.getLogger(__name__)


@dataclass
class WebhookResult:
    """Result of a webhook send attempt."""

    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


class WebhookService:
    """
    Sends webhook notifications to external services (n8n).

    Webhooks are signed with HMAC-SHA256 if a secret is configured.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        secret: Optional[str] = None,
        timeout: float = 10.0,
    ):
        """
        Initialize webhook service.

        Args:
            base_url: Webhook destination URL (default from settings)
            secret: HMAC secret for signing (default from settings)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.webhook_base_url
        self.secret = secret or settings.webhook_secret
        self.timeout = timeout
        self._sequence = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _is_enabled(self) -> bool:
        """Check if webhooks are enabled."""
        if not self.base_url:
            return False

        # Check database config
        async with AsyncSessionLocal() as db:
            config = await Config.get_instance(db)
            return config.webhook_enabled

    def _sign_payload(self, payload: str) -> Optional[str]:
        """
        Sign payload with HMAC-SHA256.

        Args:
            payload: JSON payload string

        Returns:
            Hex signature or None if no secret
        """
        if not self.secret:
            return None

        signature = hmac.new(
            self.secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return f"sha256={signature}"

    async def send(
        self,
        event: str,
        data: dict[str, Any],
        source: str = "genmaster",
    ) -> WebhookResult:
        """
        Send a webhook notification.

        Args:
            event: Event type identifier
            data: Event-specific data
            source: Source of the event

        Returns:
            WebhookResult with success/failure info
        """
        # Check if enabled
        if not await self._is_enabled():
            logger.debug(f"Webhook not sent (disabled): {event}")
            return WebhookResult(success=True, error="Webhooks disabled")

        self._sequence += 1
        timestamp = int(time.time())

        # Build payload
        payload = {
            "event": event,
            "timestamp": timestamp,
            "source": source,
            "data": data,
            "meta": {
                "sequence": self._sequence,
                "version": "1.0.0",
            },
        }

        payload_json = json.dumps(payload)

        # Build headers
        headers = {"Content-Type": "application/json"}
        signature = self._sign_payload(payload_json)
        if signature:
            headers["X-GenControl-Signature"] = signature

        # Send request
        start = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.post(
                self.base_url,
                content=payload_json,
                headers=headers,
            )
            response_time = (time.perf_counter() - start) * 1000

            if response.status_code >= 400:
                error = f"HTTP {response.status_code}"
                logger.warning(f"Webhook failed: {event} -> {error}")

                # Log failure
                await self._log_webhook(event, False, error)

                return WebhookResult(
                    success=False,
                    status_code=response.status_code,
                    response_time_ms=response_time,
                    error=error,
                )

            logger.info(
                f"Webhook sent: {event} ({response_time:.1f}ms)"
            )

            # Log success
            await self._log_webhook(event, True)

            return WebhookResult(
                success=True,
                status_code=response.status_code,
                response_time_ms=response_time,
            )

        except httpx.TimeoutException:
            response_time = (time.perf_counter() - start) * 1000
            error = "Request timed out"
            logger.warning(f"Webhook timeout: {event}")

            await self._log_webhook(event, False, error)

            return WebhookResult(
                success=False,
                response_time_ms=response_time,
                error=error,
            )

        except Exception as e:
            response_time = (time.perf_counter() - start) * 1000
            error = str(e)
            logger.error(f"Webhook error: {event} -> {error}")

            await self._log_webhook(event, False, error)

            return WebhookResult(
                success=False,
                response_time_ms=response_time,
                error=error,
            )

    async def send_test(self) -> WebhookResult:
        """Send a test webhook."""
        return await self.send(
            "test",
            {"message": "Test webhook from GenMaster"},
        )

    async def _log_webhook(
        self,
        event: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log webhook send attempt to database."""
        async with AsyncSessionLocal() as db:
            await EventLog.log(
                db,
                "WEBHOOK_SENT" if success else "WEBHOOK_FAILED",
                {
                    "event": event,
                    "success": success,
                    "error": error,
                    "url": self.base_url,
                },
                severity="INFO" if success else "WARNING",
            )

    @property
    def sequence(self) -> int:
        """Get current sequence number."""
        return self._sequence
