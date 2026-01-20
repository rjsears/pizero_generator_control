# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/system_notification_engine.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""
System Notification Engine - Event-driven notification dispatch with:
- Per-event configuration and templates
- Rate limiting (global and per-event)
- Flapping detection
- Quiet hours and blackout periods
- L1/L2 escalation with timeouts
- Maintenance mode
- Daily digest batching
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.notifications import NotificationChannel, NotificationGroup
from app.models.system_notifications import (
    SystemNotificationContainerConfig,
    SystemNotificationEvent,
    SystemNotificationGlobalSettings,
    SystemNotificationHistory,
    SystemNotificationState,
    SystemNotificationTarget,
)
from app.services.notification_service import notification_service, SendResult

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """Result of dispatching a system notification."""

    success: bool
    history_id: Optional[int] = None
    status: str = "sent"  # sent, failed, suppressed, batched
    suppression_reason: Optional[str] = None
    channels_sent: List[Dict[str, Any]] = field(default_factory=list)
    escalation_level: int = 1
    error_message: Optional[str] = None


class SystemNotificationEngine:
    """
    Core engine for dispatching system notifications.

    Handles all notification logic including rate limiting, flapping detection,
    quiet hours, escalation, and template rendering.
    """

    # Frequency to minutes mapping
    FREQUENCY_MINUTES = {
        "every_time": 0,
        "once_per_15m": 15,
        "once_per_30m": 30,
        "once_per_hour": 60,
        "once_per_4h": 240,
        "once_per_12h": 720,
        "once_per_day": 1440,
    }

    async def trigger_notification(
        self,
        db: AsyncSession,
        event_type: str,
        target_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        skip_rate_limiting: bool = False,
        force_escalation_level: Optional[int] = None,
    ) -> DispatchResult:
        """
        Trigger a system notification for the given event type.

        Args:
            db: Database session
            event_type: The event type (e.g., "generator_started")
            target_id: Optional target identifier (e.g., container name)
            event_data: Data to use for template variable substitution
            skip_rate_limiting: Skip rate limiting checks (for testing)
            force_escalation_level: Force a specific escalation level

        Returns:
            DispatchResult with status and details
        """
        event_data = event_data or {}
        result = DispatchResult(success=False)

        try:
            # Get event configuration
            event = await SystemNotificationEvent.get_by_event_type(db, event_type)
            if not event:
                logger.warning(f"Unknown event type: {event_type}")
                result.status = "failed"
                result.error_message = f"Unknown event type: {event_type}"
                return result

            # Check if event is enabled
            if not event.enabled:
                result.status = "suppressed"
                result.suppression_reason = "event_disabled"
                await self._record_history(db, event, target_id, event_data, result)
                return result

            # Get global settings
            global_settings = await SystemNotificationGlobalSettings.get_instance(db)

            # Check maintenance mode
            if global_settings.maintenance_mode:
                if (
                    global_settings.maintenance_until is None
                    or global_settings.maintenance_until > datetime.utcnow()
                ):
                    result.status = "suppressed"
                    result.suppression_reason = "maintenance_mode"
                    await self._record_history(db, event, target_id, event_data, result)
                    return result

            # Check blackout hours (complete suppression)
            if self._is_in_blackout(global_settings):
                result.status = "suppressed"
                result.suppression_reason = "blackout_hours"
                await self._record_history(db, event, target_id, event_data, result)
                return result

            # Check global rate limit
            if not skip_rate_limiting:
                if not await self._check_global_rate_limit(db, global_settings):
                    result.status = "suppressed"
                    result.suppression_reason = "global_rate_limit_exceeded"
                    await self._record_history(db, event, target_id, event_data, result)
                    # Optionally notify emergency contact
                    await self._notify_emergency_contact(db, global_settings)
                    return result

            # Get or create state for this event/target
            state_target_id = target_id or "global"
            state = await SystemNotificationState.get_or_create(db, event_type, state_target_id)

            # Check per-event rate limiting (cooldown)
            if not skip_rate_limiting:
                cooldown_active, cooldown_remaining = self._check_cooldown(event, state)
                if cooldown_active:
                    result.status = "suppressed"
                    result.suppression_reason = f"cooldown_active ({cooldown_remaining}m remaining)"
                    await self._record_history(db, event, target_id, event_data, result)
                    return result

            # Check flapping
            if event.flapping_enabled:
                is_flapping, should_send_summary = await self._check_flapping(db, event, state)
                if is_flapping and not should_send_summary:
                    result.status = "suppressed"
                    result.suppression_reason = "flapping_detected"
                    await self._record_history(db, event, target_id, event_data, result)
                    return result

            # Check daily digest eligibility
            if event.include_in_digest and global_settings.digest_enabled:
                if event.severity in global_settings.digest_severity_levels:
                    # Batch for digest instead of immediate send
                    result.status = "batched"
                    result.suppression_reason = "batched_for_digest"
                    await self._record_history(db, event, target_id, event_data, result)
                    return result

            # Check quiet hours (reduce priority or suppress based on setting)
            is_quiet = self._is_in_quiet_hours(global_settings)
            if is_quiet and not global_settings.quiet_hours_reduce_priority:
                # Suppress mode during quiet hours
                if event.severity != "critical":  # Critical always goes through
                    result.status = "suppressed"
                    result.suppression_reason = "quiet_hours"
                    await self._record_history(db, event, target_id, event_data, result)
                    return result

            # Render notification content
            title, message = self._render_templates(event, event_data)

            # Determine escalation level
            escalation_level = force_escalation_level or 1

            # Check if we need to escalate to L2
            if event.escalation_enabled and escalation_level == 1:
                if event.severity == "critical":
                    # Critical events also go to L2 immediately
                    escalation_level = 2

            # Get targets for this escalation level
            targets = await self._get_targets_for_level(db, event, escalation_level)
            if not targets:
                # Fall back to all enabled channels if no targets configured
                targets = await self._get_default_targets(db)

            if not targets:
                result.status = "failed"
                result.error_message = "No notification targets configured"
                await self._record_history(db, event, target_id, event_data, result)
                return result

            # Send notifications
            result.escalation_level = escalation_level
            send_results = await self._send_to_targets(db, targets, title, message, event_type)

            # Process results
            result.channels_sent = [
                {
                    "type": "channel",
                    "id": sr.channel_id,
                    "name": sr.channel_name,
                    "success": sr.success,
                    "error": sr.error,
                    "level": escalation_level,
                }
                for sr in send_results
            ]

            successful = [sr for sr in send_results if sr.success]
            failed = [sr for sr in send_results if not sr.success]

            if successful:
                result.success = True
                result.status = "sent"

                # Update state
                state.last_sent_at = datetime.utcnow()
                await db.commit()

                # Increment global rate limit counter
                await self._increment_global_counter(db, global_settings)

                # If L1 failed and escalation is enabled, schedule L2
                if failed and event.escalation_enabled and escalation_level == 1:
                    await self._schedule_escalation(db, event, state, target_id, event_data)
            else:
                result.status = "failed"
                result.error_message = "; ".join(sr.error for sr in failed if sr.error)

                # If all L1 failed and escalation enabled, trigger L2 immediately
                if event.escalation_enabled and escalation_level == 1:
                    l2_result = await self.trigger_notification(
                        db,
                        event_type,
                        target_id,
                        event_data,
                        skip_rate_limiting=True,
                        force_escalation_level=2,
                    )
                    result.escalation_level = 2
                    result.channels_sent.extend(l2_result.channels_sent)
                    if l2_result.success:
                        result.success = True
                        result.status = "sent"

            # Record history
            await self._record_history(db, event, target_id, event_data, result, title, message)
            return result

        except Exception as e:
            logger.error(f"Error triggering notification {event_type}: {e}", exc_info=True)
            result.status = "failed"
            result.error_message = str(e)
            return result

    def _check_cooldown(
        self, event: SystemNotificationEvent, state: SystemNotificationState
    ) -> Tuple[bool, int]:
        """
        Check if cooldown period is active.

        Returns:
            Tuple of (is_active, minutes_remaining)
        """
        cooldown_minutes = self.FREQUENCY_MINUTES.get(event.frequency, 0)
        if event.cooldown_minutes > 0:
            cooldown_minutes = max(cooldown_minutes, event.cooldown_minutes)

        if cooldown_minutes == 0:
            return False, 0

        if state.last_sent_at is None:
            return False, 0

        elapsed = (datetime.utcnow() - state.last_sent_at).total_seconds() / 60
        if elapsed < cooldown_minutes:
            return True, int(cooldown_minutes - elapsed)

        return False, 0

    async def _check_flapping(
        self,
        db: AsyncSession,
        event: SystemNotificationEvent,
        state: SystemNotificationState,
    ) -> Tuple[bool, bool]:
        """
        Check for flapping (rapid state changes).

        Returns:
            Tuple of (is_flapping, should_send_summary)
        """
        now = datetime.utcnow()

        # Reset window if expired
        window_minutes = event.flapping_threshold_minutes
        if state.window_start is None or (now - state.window_start).total_seconds() / 60 > window_minutes:
            state.window_start = now
            state.event_count_in_window = 1
            state.is_flapping = False
            await db.commit()
            return False, False

        # Increment counter
        state.event_count_in_window += 1

        # Check if flapping threshold reached
        if state.event_count_in_window >= event.flapping_threshold_count:
            if not state.is_flapping:
                state.is_flapping = True
                state.flapping_started_at = now
                state.last_summary_at = now
                await db.commit()
                # First flapping notification - send summary
                return True, True

            # Already flapping - check if time for another summary
            if state.last_summary_at:
                elapsed = (now - state.last_summary_at).total_seconds() / 60
                if elapsed >= event.flapping_summary_interval:
                    state.last_summary_at = now
                    await db.commit()
                    return True, True

            return True, False

        await db.commit()
        return False, False

    def _is_in_quiet_hours(self, settings: SystemNotificationGlobalSettings) -> bool:
        """Check if current time is within quiet hours."""
        if not settings.quiet_hours_enabled:
            return False

        now = datetime.now()
        current_time = now.strftime("%H:%M")

        start = settings.quiet_hours_start
        end = settings.quiet_hours_end

        # Handle overnight periods (e.g., 22:00 to 07:00)
        if start > end:
            return current_time >= start or current_time < end
        else:
            return start <= current_time < end

    def _is_in_blackout(self, settings: SystemNotificationGlobalSettings) -> bool:
        """Check if current time is within blackout hours."""
        if not settings.blackout_enabled:
            return False

        now = datetime.now()
        current_time = now.strftime("%H:%M")

        start = settings.blackout_start
        end = settings.blackout_end

        if start > end:
            return current_time >= start or current_time < end
        else:
            return start <= current_time < end

    async def _check_global_rate_limit(
        self, db: AsyncSession, settings: SystemNotificationGlobalSettings
    ) -> bool:
        """
        Check if global rate limit allows sending.

        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.utcnow()

        # Reset counter if hour has passed
        if settings.hour_started_at is None or (now - settings.hour_started_at).total_seconds() >= 3600:
            settings.hour_started_at = now
            settings.notifications_this_hour = 0
            await db.commit()

        return settings.notifications_this_hour < settings.max_notifications_per_hour

    async def _increment_global_counter(
        self, db: AsyncSession, settings: SystemNotificationGlobalSettings
    ) -> None:
        """Increment the global notification counter."""
        settings.notifications_this_hour += 1
        await db.commit()

    async def _notify_emergency_contact(
        self, db: AsyncSession, settings: SystemNotificationGlobalSettings
    ) -> None:
        """Notify emergency contact about rate limit exceeded."""
        if not settings.emergency_contact_id:
            return

        try:
            channel = await NotificationChannel.get_by_id(db, settings.emergency_contact_id)
            if channel and channel.enabled:
                await notification_service.send_to_channel(
                    db,
                    channel,
                    "GenMaster Rate Limit Exceeded",
                    f"The notification rate limit of {settings.max_notifications_per_hour}/hour has been exceeded. "
                    "Some notifications may have been suppressed.",
                    "rate_limit_exceeded",
                )
        except Exception as e:
            logger.error(f"Failed to notify emergency contact: {e}")

    def _render_templates(
        self, event: SystemNotificationEvent, data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Render title and message templates with event data."""
        title_template = event.custom_title or event.default_title
        message_template = event.custom_message or event.default_message

        # Add default timestamp if not provided
        if "time" not in data:
            data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Simple template substitution
        title = title_template
        message = message_template

        for key, value in data.items():
            placeholder = "{" + key + "}"
            title = title.replace(placeholder, str(value))
            message = message.replace(placeholder, str(value))

        return title, message

    async def _get_targets_for_level(
        self,
        db: AsyncSession,
        event: SystemNotificationEvent,
        level: int,
    ) -> List[NotificationChannel]:
        """Get notification channels for the given escalation level."""
        channels = []

        # Query targets for this event and level
        result = await db.execute(
            select(SystemNotificationTarget)
            .options(
                selectinload(SystemNotificationTarget.channel),
                selectinload(SystemNotificationTarget.group),
            )
            .where(
                SystemNotificationTarget.event_id == event.id,
                SystemNotificationTarget.escalation_level == level,
            )
        )
        targets = result.scalars().all()

        for target in targets:
            if target.target_type == "channel" and target.channel:
                if target.channel.enabled:
                    channels.append(target.channel)
            elif target.target_type == "group" and target.group:
                if target.group.enabled:
                    for channel in target.group.channels:
                        if channel.enabled and channel not in channels:
                            channels.append(channel)

        # For L2, also include L1 targets
        if level == 2:
            l1_channels = await self._get_targets_for_level(db, event, 1)
            for channel in l1_channels:
                if channel not in channels:
                    channels.append(channel)

        return channels

    async def _get_default_targets(self, db: AsyncSession) -> List[NotificationChannel]:
        """Get all enabled notification channels as default targets."""
        return await NotificationChannel.get_all(db, enabled_only=True)

    async def _send_to_targets(
        self,
        db: AsyncSession,
        channels: List[NotificationChannel],
        title: str,
        message: str,
        event_type: str,
    ) -> List[SendResult]:
        """Send notification to all target channels."""
        results = []
        for channel in channels:
            result = await notification_service.send_to_channel(
                db, channel, title, message, event_type
            )
            results.append(result)
        return results

    async def _schedule_escalation(
        self,
        db: AsyncSession,
        event: SystemNotificationEvent,
        state: SystemNotificationState,
        target_id: Optional[str],
        event_data: Dict[str, Any],
    ) -> None:
        """Schedule L2 escalation after timeout."""
        # Mark escalation as triggered
        state.escalation_triggered_at = datetime.utcnow()
        state.escalation_sent = False
        await db.commit()

        # Note: Actual scheduling would be done via APScheduler
        # For now, we just record that escalation should happen
        logger.info(
            f"Escalation scheduled for {event.event_type} in {event.escalation_timeout_minutes} minutes"
        )

    async def _record_history(
        self,
        db: AsyncSession,
        event: SystemNotificationEvent,
        target_id: Optional[str],
        event_data: Dict[str, Any],
        result: DispatchResult,
        title: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """Record notification to history table."""
        try:
            # Render templates if not provided
            if title is None or message is None:
                title, message = self._render_templates(event, event_data)

            history = SystemNotificationHistory(
                event_type=event.event_type,
                event_id=event.id,
                category=event.category,
                target_id=target_id,
                target_label=target_id,  # Could be enhanced with lookup
                severity=event.severity,
                title=title,
                message=message,
                event_data=event_data,
                channels_sent=result.channels_sent,
                escalation_level=result.escalation_level,
                status=result.status,
                suppression_reason=result.suppression_reason,
                error_message=result.error_message,
                triggered_at=datetime.utcnow(),
                sent_at=datetime.utcnow() if result.status == "sent" else None,
            )
            db.add(history)
            await db.commit()
            await db.refresh(history)
            result.history_id = history.id
        except Exception as e:
            logger.error(f"Failed to record notification history: {e}")

    async def check_pending_escalations(self, db: AsyncSession) -> None:
        """Check and process any pending escalations that have timed out."""
        try:
            now = datetime.utcnow()

            # Find states with pending escalations
            result = await db.execute(
                select(SystemNotificationState).where(
                    SystemNotificationState.escalation_triggered_at.isnot(None),
                    SystemNotificationState.escalation_sent == False,
                )
            )
            pending_states = result.scalars().all()

            for state in pending_states:
                # Get the event configuration
                event = await SystemNotificationEvent.get_by_event_type(db, state.event_type)
                if not event or not event.escalation_enabled:
                    continue

                # Check if timeout has passed
                elapsed = (now - state.escalation_triggered_at).total_seconds() / 60
                if elapsed >= event.escalation_timeout_minutes:
                    # Trigger L2 notification
                    await self.trigger_notification(
                        db,
                        state.event_type,
                        state.target_id if state.target_id != "global" else None,
                        {},  # Original event data not stored
                        skip_rate_limiting=True,
                        force_escalation_level=2,
                    )
                    state.escalation_sent = True
                    await db.commit()

        except Exception as e:
            logger.error(f"Error checking pending escalations: {e}", exc_info=True)

    async def send_daily_digest(self, db: AsyncSession) -> DispatchResult:
        """Send daily digest of batched notifications."""
        result = DispatchResult(success=False)

        try:
            settings = await SystemNotificationGlobalSettings.get_instance(db)
            if not settings.digest_enabled:
                result.status = "suppressed"
                result.suppression_reason = "digest_disabled"
                return result

            # Get batched notifications since last digest
            since = settings.last_digest_sent or (datetime.utcnow() - timedelta(days=1))
            query_result = await db.execute(
                select(SystemNotificationHistory)
                .where(
                    SystemNotificationHistory.status == "batched",
                    SystemNotificationHistory.triggered_at > since,
                )
                .order_by(SystemNotificationHistory.triggered_at)
            )
            batched = query_result.scalars().all()

            if not batched:
                result.status = "suppressed"
                result.suppression_reason = "no_batched_notifications"
                return result

            # Build digest message
            title = f"GenMaster Daily Digest - {len(batched)} notifications"
            message_parts = ["=== GenMaster Daily Notification Digest ===\n"]

            by_category: Dict[str, List[SystemNotificationHistory]] = {}
            for notification in batched:
                if notification.category not in by_category:
                    by_category[notification.category] = []
                by_category[notification.category].append(notification)

            for category, notifications in by_category.items():
                message_parts.append(f"\n--- {category.upper()} ({len(notifications)}) ---")
                for n in notifications:
                    message_parts.append(
                        f"  [{n.triggered_at.strftime('%H:%M')}] {n.title}"
                    )

            message = "\n".join(message_parts)

            # Get default targets (all enabled channels)
            channels = await self._get_default_targets(db)
            if not channels:
                result.status = "failed"
                result.error_message = "No notification targets configured"
                return result

            # Send digest
            send_results = await self._send_to_targets(db, channels, title, message, "daily_digest")

            successful = [sr for sr in send_results if sr.success]
            if successful:
                result.success = True
                result.status = "sent"
                settings.last_digest_sent = datetime.utcnow()
                await db.commit()
            else:
                result.status = "failed"
                result.error_message = "Failed to send digest"

            return result

        except Exception as e:
            logger.error(f"Error sending daily digest: {e}", exc_info=True)
            result.status = "failed"
            result.error_message = str(e)
            return result

    async def clear_recovery(
        self, db: AsyncSession, event_type: str, target_id: Optional[str] = None
    ) -> None:
        """
        Clear flapping state when condition has recovered.

        Should be called when a monitored condition returns to normal.
        """
        try:
            state_target_id = target_id or "global"
            state = await SystemNotificationState.get_state(db, event_type, state_target_id)

            if state and state.is_flapping:
                event = await SystemNotificationEvent.get_by_event_type(db, event_type)

                # Send recovery notification if enabled
                if event and event.notify_on_recovery:
                    await self.trigger_notification(
                        db,
                        event_type + "_recovery",
                        target_id,
                        {"original_event": event_type},
                        skip_rate_limiting=True,
                    )

                # Clear flapping state
                state.is_flapping = False
                state.flapping_started_at = None
                state.event_count_in_window = 0
                state.window_start = None
                await db.commit()

        except Exception as e:
            logger.error(f"Error clearing recovery state: {e}")


# Singleton instance
system_notification_engine = SystemNotificationEngine()
