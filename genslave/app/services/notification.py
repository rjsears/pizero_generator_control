# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/services/notification.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 18th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Notification service using Apprise for multi-platform alerts."""

import json
import logging
from typing import Optional

import apprise

from app.services.database import db_service

logger = logging.getLogger(__name__)


class NotificationService:
    """Handles notifications via Apprise.

    Supports 80+ notification services including:
    - SMS: Twilio, Nexmo, etc.
    - Push: Pushover, Pushbullet, etc.
    - Chat: Telegram, Slack, Discord, etc.
    - Email: SMTP, Gmail, etc.

    Configuration is stored in the database and can be updated
    at runtime without container restarts.
    """

    # Database key for storing Apprise URLs
    DB_KEY = "apprise_urls"

    def __init__(self):
        self._apprise: Optional[apprise.Apprise] = None

    def _get_apprise_instance(self) -> Optional[apprise.Apprise]:
        """Get a configured Apprise instance.

        Reads URLs from database and creates a fresh instance.
        This ensures any config changes are picked up.

        Returns:
            Configured Apprise instance or None if no URLs configured.
        """
        urls = self.get_urls()
        if not urls:
            return None

        apobj = apprise.Apprise()
        for url in urls:
            url = url.strip()
            if url:
                result = apobj.add(url)
                if not result:
                    logger.warning(f"Failed to add Apprise URL: {url[:30]}...")

        if len(apobj) == 0:
            logger.warning("No valid Apprise URLs configured")
            return None

        return apobj

    def get_urls(self) -> list[str]:
        """Get configured Apprise URLs from database.

        Returns:
            List of Apprise URL strings.
        """
        urls_json = db_service.get_setting(self.DB_KEY)
        if not urls_json:
            return []

        try:
            urls = json.loads(urls_json)
            if isinstance(urls, list):
                return urls
            return []
        except json.JSONDecodeError:
            logger.error("Failed to parse Apprise URLs from database")
            return []

    def set_urls(self, urls: list[str]) -> bool:
        """Store Apprise URLs in database.

        Args:
            urls: List of Apprise URL strings.

        Returns:
            True if successful.
        """
        # Filter out empty strings
        urls = [url.strip() for url in urls if url.strip()]

        try:
            urls_json = json.dumps(urls)
            success = db_service.set_setting(self.DB_KEY, urls_json)
            if success:
                logger.info(f"Updated Apprise URLs: {len(urls)} configured")
            return success
        except Exception as e:
            logger.error(f"Failed to save Apprise URLs: {e}")
            return False

    def is_configured(self) -> bool:
        """Check if any notification URLs are configured.

        Returns:
            True if at least one URL is configured.
        """
        urls = self.get_urls()
        return len(urls) > 0

    async def send(
        self,
        title: str,
        body: str,
        notify_type: apprise.NotifyType = apprise.NotifyType.WARNING,
    ) -> bool:
        """Send a notification via all configured services.

        Args:
            title: Notification title/subject.
            body: Notification body/message.
            notify_type: Type of notification (INFO, SUCCESS, WARNING, FAILURE).

        Returns:
            True if at least one notification was sent successfully.
        """
        apobj = self._get_apprise_instance()
        if not apobj:
            logger.debug("No Apprise URLs configured - skipping notification")
            return False

        try:
            # Apprise.notify() is synchronous, but fast for most services
            result = apobj.notify(
                title=title,
                body=body,
                notify_type=notify_type,
            )

            if result:
                logger.info(f"Notification sent: {title}")
            else:
                logger.warning(f"Notification may have failed: {title}")

            return result

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def send_failsafe_alert(self, timeout_seconds: int) -> bool:
        """Send a failsafe trigger notification.

        Args:
            timeout_seconds: The failsafe timeout that was exceeded.

        Returns:
            True if notification was sent.
        """
        title = "GenSlave FAILSAFE TRIGGERED"
        body = (
            f"Generator relay has been turned OFF due to lost communication "
            f"with GenMaster.\n\n"
            f"No heartbeat received for {timeout_seconds} seconds.\n\n"
            f"Please check GenMaster connectivity and restart automation "
            f"when communication is restored."
        )

        return await self.send(
            title=title,
            body=body,
            notify_type=apprise.NotifyType.FAILURE,
        )

    async def send_test(self) -> bool:
        """Send a test notification.

        Returns:
            True if test notification was sent successfully.
        """
        title = "GenSlave Test Notification"
        body = (
            "This is a test notification from GenSlave.\n\n"
            "If you received this, your notification configuration is working correctly."
        )

        return await self.send(
            title=title,
            body=body,
            notify_type=apprise.NotifyType.INFO,
        )


# Global notification service instance
notification_service = NotificationService()
