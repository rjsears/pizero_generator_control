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
import time
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

    Includes cooldown support to prevent notification flapping.
    """

    # Database keys
    DB_KEY = "apprise_urls"
    DB_ENABLED_KEY = "notifications_enabled"

    # Cooldown settings keys
    DB_FAILSAFE_COOLDOWN_KEY = "failsafe_cooldown_minutes"
    DB_RESTORED_COOLDOWN_KEY = "restored_cooldown_minutes"
    DB_LAST_FAILSAFE_SENT_KEY = "last_failsafe_notification_at"
    DB_LAST_RESTORED_SENT_KEY = "last_restored_notification_at"

    # Default cooldown values (in minutes)
    DEFAULT_FAILSAFE_COOLDOWN = 5
    DEFAULT_RESTORED_COOLDOWN = 5

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

    def is_enabled(self) -> bool:
        """Check if notifications are enabled.

        Returns:
            True if notifications are enabled (default: True).
        """
        enabled = db_service.get_setting(self.DB_ENABLED_KEY)
        # Default to enabled if not set
        if enabled is None:
            return True
        return enabled.lower() == "true"

    def set_enabled(self, enabled: bool) -> bool:
        """Enable or disable notifications.

        Args:
            enabled: True to enable, False to disable.

        Returns:
            True if successful.
        """
        try:
            success = db_service.set_setting(self.DB_ENABLED_KEY, str(enabled).lower())
            if success:
                state = "enabled" if enabled else "disabled"
                logger.info(f"Notifications {state}")
            return success
        except Exception as e:
            logger.error(f"Failed to set notification enabled state: {e}")
            return False

    # =========================================================================
    # Cooldown Settings
    # =========================================================================

    def get_cooldown_settings(self) -> dict:
        """Get cooldown settings for notifications.

        Returns:
            Dictionary with cooldown settings:
            - failsafe_cooldown_minutes: Cooldown for failsafe notifications
            - restored_cooldown_minutes: Cooldown for restored notifications
            - last_failsafe_notification_at: Unix timestamp of last failsafe notification
            - last_restored_notification_at: Unix timestamp of last restored notification
        """
        failsafe_cooldown = db_service.get_setting(self.DB_FAILSAFE_COOLDOWN_KEY)
        restored_cooldown = db_service.get_setting(self.DB_RESTORED_COOLDOWN_KEY)
        last_failsafe = db_service.get_setting(self.DB_LAST_FAILSAFE_SENT_KEY)
        last_restored = db_service.get_setting(self.DB_LAST_RESTORED_SENT_KEY)

        return {
            "failsafe_cooldown_minutes": int(failsafe_cooldown) if failsafe_cooldown else self.DEFAULT_FAILSAFE_COOLDOWN,
            "restored_cooldown_minutes": int(restored_cooldown) if restored_cooldown else self.DEFAULT_RESTORED_COOLDOWN,
            "last_failsafe_notification_at": int(last_failsafe) if last_failsafe else None,
            "last_restored_notification_at": int(last_restored) if last_restored else None,
        }

    def set_cooldown_settings(
        self,
        failsafe_cooldown_minutes: Optional[int] = None,
        restored_cooldown_minutes: Optional[int] = None,
    ) -> bool:
        """Update cooldown settings for notifications.

        Args:
            failsafe_cooldown_minutes: Cooldown period for failsafe notifications (minutes).
            restored_cooldown_minutes: Cooldown period for restored notifications (minutes).

        Returns:
            True if successful.
        """
        try:
            if failsafe_cooldown_minutes is not None:
                # Minimum 1 minute, maximum 60 minutes
                failsafe_cooldown_minutes = max(1, min(60, failsafe_cooldown_minutes))
                db_service.set_setting(
                    self.DB_FAILSAFE_COOLDOWN_KEY, str(failsafe_cooldown_minutes)
                )
                logger.info(f"Failsafe cooldown set to {failsafe_cooldown_minutes} minutes")

            if restored_cooldown_minutes is not None:
                # Minimum 1 minute, maximum 60 minutes
                restored_cooldown_minutes = max(1, min(60, restored_cooldown_minutes))
                db_service.set_setting(
                    self.DB_RESTORED_COOLDOWN_KEY, str(restored_cooldown_minutes)
                )
                logger.info(f"Restored cooldown set to {restored_cooldown_minutes} minutes")

            return True
        except Exception as e:
            logger.error(f"Failed to set cooldown settings: {e}")
            return False

    def _check_cooldown(self, event_type: str) -> tuple[bool, Optional[int]]:
        """Check if a notification is within cooldown period.

        Args:
            event_type: Either "failsafe" or "restored".

        Returns:
            Tuple of (can_send, remaining_seconds).
            - can_send: True if notification can be sent (not in cooldown).
            - remaining_seconds: Seconds remaining in cooldown, or None if can send.
        """
        settings = self.get_cooldown_settings()
        now = int(time.time())

        if event_type == "failsafe":
            cooldown_minutes = settings["failsafe_cooldown_minutes"]
            last_sent = settings["last_failsafe_notification_at"]
        elif event_type == "restored":
            cooldown_minutes = settings["restored_cooldown_minutes"]
            last_sent = settings["last_restored_notification_at"]
        else:
            # Unknown event type - allow sending
            return (True, None)

        if last_sent is None:
            # Never sent before - allow
            return (True, None)

        cooldown_seconds = cooldown_minutes * 60
        elapsed = now - last_sent
        remaining = cooldown_seconds - elapsed

        if remaining > 0:
            # Still in cooldown
            return (False, remaining)

        # Cooldown expired - allow sending
        return (True, None)

    def _record_notification_sent(self, event_type: str) -> None:
        """Record that a notification was sent.

        Args:
            event_type: Either "failsafe" or "restored".
        """
        now = str(int(time.time()))

        if event_type == "failsafe":
            db_service.set_setting(self.DB_LAST_FAILSAFE_SENT_KEY, now)
        elif event_type == "restored":
            db_service.set_setting(self.DB_LAST_RESTORED_SENT_KEY, now)

    def clear_cooldown(self, event_type: Optional[str] = None) -> bool:
        """Clear cooldown state for notifications.

        This allows forcing a notification to be sent immediately.

        Args:
            event_type: "failsafe", "restored", or None for both.

        Returns:
            True if successful.
        """
        try:
            if event_type is None or event_type == "failsafe":
                db_service.set_setting(self.DB_LAST_FAILSAFE_SENT_KEY, "")
                logger.info("Cleared failsafe notification cooldown")

            if event_type is None or event_type == "restored":
                db_service.set_setting(self.DB_LAST_RESTORED_SENT_KEY, "")
                logger.info("Cleared restored notification cooldown")

            return True
        except Exception as e:
            logger.error(f"Failed to clear cooldown: {e}")
            return False

    async def send(
        self,
        title: str,
        body: str,
        notify_type: apprise.NotifyType = apprise.NotifyType.WARNING,
        force: bool = False,
    ) -> bool:
        """Send a notification via all configured services.

        Args:
            title: Notification title/subject.
            body: Notification body/message.
            notify_type: Type of notification (INFO, SUCCESS, WARNING, FAILURE).
            force: If True, send even if notifications are disabled (for testing).

        Returns:
            True if at least one notification was sent successfully.
        """
        # Check if notifications are enabled (unless forced)
        if not force and not self.is_enabled():
            logger.debug("Notifications disabled - skipping")
            return False

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
            True if notification was sent, False if skipped (cooldown or disabled).
        """
        # Check cooldown before sending
        can_send, remaining = self._check_cooldown("failsafe")
        if not can_send:
            logger.info(
                f"Failsafe notification skipped - cooldown active "
                f"({remaining}s remaining)"
            )
            return False

        title = "GenSlave FAILSAFE TRIGGERED"
        body = (
            f"Generator relay has been turned OFF and DISARMED due to lost "
            f"communication with GenMaster.\n\n"
            f"No heartbeat received for {timeout_seconds} seconds.\n\n"
            f"Please check GenMaster connectivity. You must manually re-arm "
            f"from the GenMaster dashboard to resume generator control."
        )

        result = await self.send(
            title=title,
            body=body,
            notify_type=apprise.NotifyType.FAILURE,
        )

        # Record that we sent (or attempted to send) the notification
        if result:
            self._record_notification_sent("failsafe")

        return result

    async def send_heartbeat_restored_alert(self) -> bool:
        """Send a notification when heartbeat is restored but relay needs re-arming.

        This is sent after a failsafe event when communication with GenMaster
        is restored, but the relay is still disarmed and needs manual re-arming.

        Returns:
            True if notification was sent, False if skipped (cooldown or disabled).
        """
        # Check cooldown before sending
        can_send, remaining = self._check_cooldown("restored")
        if not can_send:
            logger.info(
                f"Restored notification skipped - cooldown active "
                f"({remaining}s remaining)"
            )
            return False

        title = "GenSlave Communication Restored"
        body = (
            "Communication with GenMaster has been restored.\n\n"
            "The relay is currently DISARMED after the failsafe event.\n\n"
            "Please re-arm the relay from the GenMaster dashboard to "
            "resume generator control."
        )

        result = await self.send(
            title=title,
            body=body,
            notify_type=apprise.NotifyType.WARNING,
        )

        # Record that we sent (or attempted to send) the notification
        if result:
            self._record_notification_sent("restored")

        return result

    async def send_test(self) -> bool:
        """Send a test notification.

        Test notifications are always sent, even if notifications are disabled.
        This allows testing the configuration without enabling notifications.

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
            force=True,  # Test notifications always send
        )


# Global notification service instance
notification_service = NotificationService()
