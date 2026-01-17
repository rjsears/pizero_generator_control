# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/notification_service.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Notification service for sending via Apprise and Email."""

import logging
import re
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.notifications import (
    NotificationChannel,
    NotificationGroup,
    NotificationHistory,
)

logger = logging.getLogger(__name__)


@dataclass
class SendResult:
    """Result of sending a notification."""

    channel_id: int
    channel_name: str
    success: bool
    error: Optional[str] = None


class NotificationService:
    """Service for sending notifications via Apprise and Email."""

    def __init__(self):
        """Initialize the notification service."""
        self._apprise = None

    def _get_apprise(self):
        """Lazy-load apprise library."""
        if self._apprise is None:
            try:
                import apprise
                self._apprise = apprise
            except ImportError:
                logger.warning("Apprise library not installed")
                self._apprise = False
        return self._apprise

    async def send_to_channel(
        self,
        db: AsyncSession,
        channel: NotificationChannel,
        title: str,
        message: str,
        event_type: str,
    ) -> SendResult:
        """Send notification to a single channel."""
        result = SendResult(
            channel_id=channel.id,
            channel_name=channel.name,
            success=False,
        )

        try:
            if channel.channel_type == "apprise":
                result = await self._send_apprise(channel, title, message)
            elif channel.channel_type == "email":
                result = await self._send_email(channel, title, message)
            else:
                result.error = f"Unknown channel type: {channel.channel_type}"

            # Log to history
            history = NotificationHistory(
                channel_id=channel.id,
                event_type=event_type,
                title=title,
                message=message,
                success=result.success,
                error_message=result.error,
            )
            db.add(history)
            await db.commit()

        except Exception as e:
            logger.error(f"Failed to send to channel {channel.name}: {e}")
            result.error = str(e)

            # Log failure to history
            try:
                history = NotificationHistory(
                    channel_id=channel.id,
                    event_type=event_type,
                    title=title,
                    message=message,
                    success=False,
                    error_message=str(e),
                )
                db.add(history)
                await db.commit()
            except Exception:
                pass

        return result

    async def _send_apprise(
        self,
        channel: NotificationChannel,
        title: str,
        message: str,
    ) -> SendResult:
        """Send notification via Apprise."""
        result = SendResult(
            channel_id=channel.id,
            channel_name=channel.name,
            success=False,
        )

        apprise = self._get_apprise()
        if apprise is False:
            result.error = "Apprise library not installed"
            return result

        try:
            # Get URL from config
            url = channel.config.get("url")
            if not url:
                result.error = "No Apprise URL configured"
                return result

            # Create Apprise instance and add URL
            apobj = apprise.Apprise()
            apobj.add(url)

            # Send notification
            success = apobj.notify(
                title=title,
                body=message,
            )

            result.success = success
            if not success:
                result.error = "Apprise notification failed"

        except Exception as e:
            logger.error(f"Apprise send error: {e}")
            result.error = str(e)

        return result

    async def _send_email(
        self,
        channel: NotificationChannel,
        title: str,
        message: str,
    ) -> SendResult:
        """Send notification via Email."""
        result = SendResult(
            channel_id=channel.id,
            channel_name=channel.name,
            success=False,
        )

        try:
            config = channel.config

            # Validate required fields
            required = ["smtp_host", "smtp_port", "username", "password", "from_address", "to_addresses"]
            for field in required:
                if field not in config:
                    result.error = f"Missing email config field: {field}"
                    return result

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = title
            msg["From"] = config["from_address"]
            msg["To"] = ", ".join(config["to_addresses"])

            # Plain text version
            text_part = MIMEText(message, "plain")
            msg.attach(text_part)

            # HTML version (simple)
            html_message = f"""
            <html>
            <body>
                <h2>{title}</h2>
                <p>{message.replace(chr(10), '<br>')}</p>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    Sent by GenMaster Notification System
                </p>
            </body>
            </html>
            """
            html_part = MIMEText(html_message, "html")
            msg.attach(html_part)

            # Send email
            use_tls = config.get("use_tls", True)
            smtp_host = config["smtp_host"]
            smtp_port = config["smtp_port"]

            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(smtp_host, smtp_port)

            server.login(config["username"], config["password"])
            server.sendmail(
                config["from_address"],
                config["to_addresses"],
                msg.as_string(),
            )
            server.quit()

            result.success = True

        except Exception as e:
            logger.error(f"Email send error: {e}")
            result.error = str(e)

        return result

    async def send_notification(
        self,
        db: AsyncSession,
        event_type: str,
        title: str,
        message: str,
        channel_ids: Optional[List[int]] = None,
        group_ids: Optional[List[int]] = None,
    ) -> List[SendResult]:
        """Send notification to specified channels/groups or all enabled channels."""
        results = []
        channels_to_send: List[NotificationChannel] = []

        if channel_ids:
            # Send to specific channels
            for channel_id in channel_ids:
                channel = await NotificationChannel.get_by_id(db, channel_id)
                if channel and channel.enabled:
                    channels_to_send.append(channel)

        if group_ids:
            # Send to all channels in specified groups
            for group_id in group_ids:
                result = await db.execute(
                    select(NotificationGroup)
                    .options(selectinload(NotificationGroup.channels))
                    .where(NotificationGroup.id == group_id)
                )
                group = result.scalar_one_or_none()
                if group and group.enabled:
                    for channel in group.channels:
                        if channel.enabled and channel not in channels_to_send:
                            channels_to_send.append(channel)

        if not channel_ids and not group_ids:
            # Send to all enabled channels
            channels_to_send = await NotificationChannel.get_all(db, enabled_only=True)

        # Send to each channel
        for channel in channels_to_send:
            result = await self.send_to_channel(db, channel, title, message, event_type)
            results.append(result)

        return results

    async def test_channel(
        self,
        db: AsyncSession,
        channel: NotificationChannel,
        title: str = "Test Notification",
        message: str = "This is a test notification from GenMaster.",
    ) -> SendResult:
        """Test a notification channel."""
        return await self.send_to_channel(db, channel, title, message, "test")


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with underscores
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "_", text)
    # Remove leading/trailing underscores
    text = text.strip("_")
    return text


# Singleton instance
notification_service = NotificationService()
