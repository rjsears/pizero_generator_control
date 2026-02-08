# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/system_notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""
System Notification API endpoints for event-driven notification configuration.

Provides endpoints for:
- Event configuration (per-event settings, templates, targets)
- Global settings (maintenance, quiet hours, rate limiting, digest)
- Container monitoring configuration
- Enhanced notification history
"""

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, DbSession
from app.models.notifications import NotificationChannel, NotificationGroup
from app.models.system_notifications import (
    SystemNotificationContainerConfig,
    SystemNotificationEvent,
    SystemNotificationGlobalSettings,
    SystemNotificationHistory,
    SystemNotificationTarget,
)
from app.schemas.system_notifications import (
    BulkUpdateRequest,
    BulkUpdateResponse,
    ContainerConfigCreate,
    ContainerConfigResponse,
    ContainerConfigUpdate,
    ContainerDiscoveryResponse,
    ContainerListResponse,
    DiscoveredContainer,
    GlobalSettingsResponse,
    GlobalSettingsUpdate,
    HistoryListResponse,
    HistoryStatsResponse,
    NotificationTargetCreate,
    NotificationTargetResponse,
    ResetTemplateRequest,
    SystemNotificationEventListResponse,
    SystemNotificationEventResponse,
    SystemNotificationEventUpdate,
    SystemNotificationHistoryResponse,
    TriggerNotificationRequest,
    TriggerNotificationResponse,
)
from app.services.system_notification_engine import system_notification_engine

router = APIRouter()


# ============================================================================
# Event Configuration Endpoints
# ============================================================================


@router.get("/events", response_model=SystemNotificationEventListResponse)
async def list_events(
    db: DbSession,
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled_only: bool = Query(False, description="Only show enabled events"),
) -> SystemNotificationEventListResponse:
    """Get all system notification events with their configuration."""
    events = await SystemNotificationEvent.get_all(db, category=category, enabled_only=enabled_only)

    # Get unique categories
    categories = list(set(e.category for e in events))
    categories.sort()

    # Build response with targets
    event_responses = []
    for event in events:
        # Load targets for this event
        result = await db.execute(
            select(SystemNotificationTarget)
            .options(
                selectinload(SystemNotificationTarget.channel),
                selectinload(SystemNotificationTarget.group),
            )
            .where(SystemNotificationTarget.event_id == event.id)
        )
        targets = result.scalars().all()

        event_responses.append(
            SystemNotificationEventResponse(
                id=event.id,
                event_type=event.event_type,
                display_name=event.display_name,
                description=event.description,
                icon=event.icon,
                category=event.category,
                enabled=event.enabled,
                severity=event.severity,
                frequency=event.frequency,
                cooldown_minutes=event.cooldown_minutes,
                flapping_enabled=event.flapping_enabled,
                flapping_threshold_count=event.flapping_threshold_count,
                flapping_threshold_minutes=event.flapping_threshold_minutes,
                flapping_summary_interval=event.flapping_summary_interval,
                notify_on_recovery=event.notify_on_recovery,
                escalation_enabled=event.escalation_enabled,
                escalation_timeout_minutes=event.escalation_timeout_minutes,
                thresholds=event.thresholds,
                include_in_digest=event.include_in_digest,
                default_title=event.default_title,
                default_message=event.default_message,
                custom_title=event.custom_title,
                custom_message=event.custom_message,
                targets=[
                    NotificationTargetResponse(
                        id=t.id,
                        target_type=t.target_type,
                        channel_id=t.channel_id,
                        group_id=t.group_id,
                        escalation_level=t.escalation_level,
                        escalation_timeout_minutes=t.escalation_timeout_minutes,
                        target_name=t.target_name,
                    )
                    for t in targets
                ],
                created_at=event.created_at,
                updated_at=event.updated_at,
            )
        )

    return SystemNotificationEventListResponse(
        events=event_responses,
        total=len(event_responses),
        categories=categories,
    )


@router.get("/events/{event_id}", response_model=SystemNotificationEventResponse)
async def get_event(event_id: int, db: DbSession) -> SystemNotificationEventResponse:
    """Get a specific system notification event."""
    event = await SystemNotificationEvent.get_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Load targets
    result = await db.execute(
        select(SystemNotificationTarget)
        .options(
            selectinload(SystemNotificationTarget.channel),
            selectinload(SystemNotificationTarget.group),
        )
        .where(SystemNotificationTarget.event_id == event.id)
    )
    targets = result.scalars().all()

    return SystemNotificationEventResponse(
        id=event.id,
        event_type=event.event_type,
        display_name=event.display_name,
        description=event.description,
        icon=event.icon,
        category=event.category,
        enabled=event.enabled,
        severity=event.severity,
        frequency=event.frequency,
        cooldown_minutes=event.cooldown_minutes,
        flapping_enabled=event.flapping_enabled,
        flapping_threshold_count=event.flapping_threshold_count,
        flapping_threshold_minutes=event.flapping_threshold_minutes,
        flapping_summary_interval=event.flapping_summary_interval,
        notify_on_recovery=event.notify_on_recovery,
        escalation_enabled=event.escalation_enabled,
        escalation_timeout_minutes=event.escalation_timeout_minutes,
        thresholds=event.thresholds,
        include_in_digest=event.include_in_digest,
        default_title=event.default_title,
        default_message=event.default_message,
        custom_title=event.custom_title,
        custom_message=event.custom_message,
        targets=[
            NotificationTargetResponse(
                id=t.id,
                target_type=t.target_type,
                channel_id=t.channel_id,
                group_id=t.group_id,
                escalation_level=t.escalation_level,
                escalation_timeout_minutes=t.escalation_timeout_minutes,
                target_name=t.target_name,
            )
            for t in targets
        ],
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.put("/events/{event_id}", response_model=SystemNotificationEventResponse)
async def update_event(
    event_id: int,
    data: SystemNotificationEventUpdate,
    db: DbSession,
    admin: AdminUser,
) -> SystemNotificationEventResponse:
    """Update a system notification event configuration."""
    event = await SystemNotificationEvent.get_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Update scalar fields
    update_fields = [
        "enabled", "severity", "frequency", "cooldown_minutes",
        "flapping_enabled", "flapping_threshold_count", "flapping_threshold_minutes",
        "flapping_summary_interval", "notify_on_recovery",
        "escalation_enabled", "escalation_timeout_minutes",
        "thresholds", "include_in_digest", "custom_title", "custom_message",
    ]
    for field in update_fields:
        value = getattr(data, field, None)
        if value is not None:
            setattr(event, field, value if not hasattr(value, "value") else value.value)

    # Update targets if provided
    if data.l1_targets is not None or data.l2_targets is not None:
        # Remove existing targets
        await db.execute(
            select(SystemNotificationTarget).where(
                SystemNotificationTarget.event_id == event.id
            )
        )
        existing = await db.execute(
            select(SystemNotificationTarget).where(
                SystemNotificationTarget.event_id == event.id
            )
        )
        for target in existing.scalars().all():
            await db.delete(target)

        # Add new L1 targets
        if data.l1_targets:
            for t in data.l1_targets:
                target = SystemNotificationTarget(
                    event_id=event.id,
                    target_type=t.target_type.value,
                    channel_id=t.channel_id,
                    group_id=t.group_id,
                    escalation_level=1,
                    escalation_timeout_minutes=t.escalation_timeout_minutes,
                )
                db.add(target)

        # Add new L2 targets
        if data.l2_targets:
            for t in data.l2_targets:
                target = SystemNotificationTarget(
                    event_id=event.id,
                    target_type=t.target_type.value,
                    channel_id=t.channel_id,
                    group_id=t.group_id,
                    escalation_level=2,
                    escalation_timeout_minutes=t.escalation_timeout_minutes,
                )
                db.add(target)

    await db.commit()
    await db.refresh(event)

    # Reload with targets
    return await get_event(event_id, db)


@router.post("/events/{event_id}/targets", response_model=NotificationTargetResponse)
async def add_event_target(
    event_id: int,
    data: NotificationTargetCreate,
    db: DbSession,
    admin: AdminUser,
) -> NotificationTargetResponse:
    """Add a notification target to an event."""
    event = await SystemNotificationEvent.get_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    target_type = data.target_type.value if hasattr(data.target_type, 'value') else data.target_type

    # Validate that the referenced channel/group exists
    if target_type == "channel":
        if not data.channel_id:
            raise HTTPException(status_code=400, detail="channel_id is required for channel targets")
        channel = await db.execute(
            select(NotificationChannel).where(NotificationChannel.id == data.channel_id)
        )
        if not channel.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Notification channel with ID {data.channel_id} not found. Please create a channel first."
            )
    elif target_type == "group":
        if not data.group_id:
            raise HTTPException(status_code=400, detail="group_id is required for group targets")
        group = await db.execute(
            select(NotificationGroup).where(NotificationGroup.id == data.group_id)
        )
        if not group.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Notification group with ID {data.group_id} not found. Please create a group first."
            )

    # Create the target
    target = SystemNotificationTarget(
        event_id=event.id,
        target_type=target_type,
        channel_id=data.channel_id,
        group_id=data.group_id,
        escalation_level=data.escalation_level,
        escalation_timeout_minutes=data.escalation_timeout_minutes,
    )

    try:
        db.add(target)
        await db.commit()
        await db.refresh(target)
    except IntegrityError as e:
        await db.rollback()
        if "uq_snt_event_target_level" in str(e):
            raise HTTPException(
                status_code=409,
                detail="This target is already configured for this event at this escalation level"
            )
        raise HTTPException(status_code=400, detail=f"Failed to add target: {str(e)}")

    return NotificationTargetResponse(
        id=target.id,
        target_type=target.target_type,
        channel_id=target.channel_id,
        group_id=target.group_id,
        escalation_level=target.escalation_level,
        escalation_timeout_minutes=target.escalation_timeout_minutes,
        target_name=target.target_name,
    )


@router.delete("/events/{event_id}/targets/{target_id}")
async def remove_event_target(
    event_id: int,
    target_id: int,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """Remove a notification target from an event."""
    result = await db.execute(
        select(SystemNotificationTarget).where(
            SystemNotificationTarget.id == target_id,
            SystemNotificationTarget.event_id == event_id,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    await db.delete(target)
    await db.commit()

    return {"success": True, "message": "Target removed"}


@router.post("/events/{event_id}/reset-template")
async def reset_event_template(
    event_id: int,
    data: ResetTemplateRequest,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """Reset event templates to defaults."""
    event = await SystemNotificationEvent.get_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if data.reset_title:
        event.custom_title = None
    if data.reset_message:
        event.custom_message = None

    await db.commit()

    return {
        "success": True,
        "message": "Template reset to defaults",
        "default_title": event.default_title,
        "default_message": event.default_message,
    }


@router.post("/events/bulk-update", response_model=BulkUpdateResponse)
async def bulk_update_events(
    data: BulkUpdateRequest,
    db: DbSession,
    admin: AdminUser,
) -> BulkUpdateResponse:
    """Bulk update multiple events at once."""
    updated_count = 0

    for event_id in data.event_ids:
        event = await SystemNotificationEvent.get_by_id(db, event_id)
        if event:
            if data.enabled is not None:
                event.enabled = data.enabled
            if data.severity is not None:
                event.severity = data.severity.value
            if data.frequency is not None:
                event.frequency = data.frequency.value
            if data.escalation_enabled is not None:
                event.escalation_enabled = data.escalation_enabled
            updated_count += 1

    await db.commit()

    return BulkUpdateResponse(
        success=True,
        updated_count=updated_count,
        message=f"Updated {updated_count} events",
    )


# ============================================================================
# Global Settings Endpoints
# ============================================================================


def _add_utc_timezone(dt: Optional[datetime]) -> Optional[datetime]:
    """Add UTC timezone to naive datetime (stored as UTC in DB)."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/settings", response_model=GlobalSettingsResponse)
async def get_global_settings(db: DbSession) -> GlobalSettingsResponse:
    """Get global notification settings."""
    settings = await SystemNotificationGlobalSettings.get_instance(db)

    return GlobalSettingsResponse(
        id=settings.id,
        maintenance_mode=settings.maintenance_mode,
        maintenance_until=_add_utc_timezone(settings.maintenance_until),
        maintenance_reason=settings.maintenance_reason,
        quiet_hours_enabled=settings.quiet_hours_enabled,
        quiet_hours_start=settings.quiet_hours_start,
        quiet_hours_end=settings.quiet_hours_end,
        quiet_hours_reduce_priority=settings.quiet_hours_reduce_priority,
        blackout_enabled=settings.blackout_enabled,
        blackout_start=settings.blackout_start,
        blackout_end=settings.blackout_end,
        max_notifications_per_hour=settings.max_notifications_per_hour,
        notifications_this_hour=settings.notifications_this_hour,
        hour_started_at=settings.hour_started_at,
        emergency_contact_id=settings.emergency_contact_id,
        digest_enabled=settings.digest_enabled,
        digest_time=settings.digest_time,
        digest_severity_levels=settings.digest_severity_levels,
        last_digest_sent=settings.last_digest_sent,
        updated_at=settings.updated_at,
    )


@router.put("/settings", response_model=GlobalSettingsResponse)
async def update_global_settings(
    data: GlobalSettingsUpdate,
    db: DbSession,
    admin: AdminUser,
) -> GlobalSettingsResponse:
    """Update global notification settings."""

    settings = await SystemNotificationGlobalSettings.get_instance(db)

    # Update fields
    update_fields = [
        "maintenance_mode", "maintenance_until", "maintenance_reason",
        "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end",
        "quiet_hours_reduce_priority",
        "blackout_enabled", "blackout_start", "blackout_end",
        "max_notifications_per_hour", "emergency_contact_id",
        "digest_enabled", "digest_time", "digest_severity_levels",
    ]
    for field in update_fields:
        value = getattr(data, field, None)
        if value is not None:
            # Strip timezone from datetime fields (DB uses TIMESTAMP WITHOUT TIME ZONE)
            if isinstance(value, datetime) and value.tzinfo is not None:
                value = value.replace(tzinfo=None)
            setattr(settings, field, value)

    try:
        await db.commit()
        await db.refresh(settings)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update settings: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")

    return await get_global_settings(db)


# ============================================================================
# Container Configuration Endpoints
# ============================================================================


@router.get("/containers", response_model=ContainerListResponse)
async def list_container_configs(db: DbSession) -> ContainerListResponse:
    """Get all container monitoring configurations."""
    configs = await SystemNotificationContainerConfig.get_all(db)

    return ContainerListResponse(
        configs=[
            ContainerConfigResponse(
                id=c.id,
                container_name=c.container_name,
                enabled=c.enabled,
                monitor_unhealthy=c.monitor_unhealthy,
                monitor_restart=c.monitor_restart,
                monitor_stopped=c.monitor_stopped,
                monitor_high_cpu=c.monitor_high_cpu,
                monitor_high_memory=c.monitor_high_memory,
                cpu_threshold=c.cpu_threshold,
                memory_threshold=c.memory_threshold,
                custom_targets=c.custom_targets,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in configs
        ],
        total=len(configs),
    )


@router.get("/containers/discover", response_model=ContainerDiscoveryResponse)
async def discover_containers(db: DbSession) -> ContainerDiscoveryResponse:
    """Discover running Docker containers."""
    import docker

    containers = []
    try:
        client = docker.from_env()
        for container in client.containers.list(all=True):
            # Check if already configured
            config = await SystemNotificationContainerConfig.get_by_name(db, container.name)

            containers.append(
                DiscoveredContainer(
                    name=container.name,
                    status=container.status,
                    health=container.attrs.get("State", {}).get("Health", {}).get("Status"),
                    image=container.image.tags[0] if container.image.tags else "unknown",
                    configured=config is not None,
                )
            )
    except Exception:
        # Docker not available or error
        pass

    return ContainerDiscoveryResponse(
        containers=containers,
        total=len(containers),
    )


@router.post("/containers", response_model=ContainerConfigResponse)
async def create_container_config(
    data: ContainerConfigCreate,
    db: DbSession,
    admin: AdminUser,
) -> ContainerConfigResponse:
    """Create a new container monitoring configuration."""
    # Check for existing
    existing = await SystemNotificationContainerConfig.get_by_name(db, data.container_name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration for container '{data.container_name}' already exists",
        )

    config = SystemNotificationContainerConfig(
        container_name=data.container_name,
        enabled=data.enabled,
        monitor_unhealthy=data.monitor_unhealthy,
        monitor_restart=data.monitor_restart,
        monitor_stopped=data.monitor_stopped,
        monitor_high_cpu=data.monitor_high_cpu,
        monitor_high_memory=data.monitor_high_memory,
        cpu_threshold=data.cpu_threshold,
        memory_threshold=data.memory_threshold,
        custom_targets=data.custom_targets,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    return ContainerConfigResponse(
        id=config.id,
        container_name=config.container_name,
        enabled=config.enabled,
        monitor_unhealthy=config.monitor_unhealthy,
        monitor_restart=config.monitor_restart,
        monitor_stopped=config.monitor_stopped,
        monitor_high_cpu=config.monitor_high_cpu,
        monitor_high_memory=config.monitor_high_memory,
        cpu_threshold=config.cpu_threshold,
        memory_threshold=config.memory_threshold,
        custom_targets=config.custom_targets,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.put("/containers/{config_id}", response_model=ContainerConfigResponse)
async def update_container_config(
    config_id: int,
    data: ContainerConfigUpdate,
    db: DbSession,
    admin: AdminUser,
) -> ContainerConfigResponse:
    """Update a container monitoring configuration."""
    result = await db.execute(
        select(SystemNotificationContainerConfig).where(
            SystemNotificationContainerConfig.id == config_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Container configuration not found")

    # Update fields
    update_fields = [
        "enabled", "monitor_unhealthy", "monitor_restart", "monitor_stopped",
        "monitor_high_cpu", "monitor_high_memory",
        "cpu_threshold", "memory_threshold", "custom_targets",
    ]
    for field in update_fields:
        value = getattr(data, field, None)
        if value is not None:
            setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return ContainerConfigResponse(
        id=config.id,
        container_name=config.container_name,
        enabled=config.enabled,
        monitor_unhealthy=config.monitor_unhealthy,
        monitor_restart=config.monitor_restart,
        monitor_stopped=config.monitor_stopped,
        monitor_high_cpu=config.monitor_high_cpu,
        monitor_high_memory=config.monitor_high_memory,
        cpu_threshold=config.cpu_threshold,
        memory_threshold=config.memory_threshold,
        custom_targets=config.custom_targets,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.delete("/containers/{config_id}")
async def delete_container_config(
    config_id: int,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """Delete a container monitoring configuration."""
    result = await db.execute(
        select(SystemNotificationContainerConfig).where(
            SystemNotificationContainerConfig.id == config_id
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Container configuration not found")

    container_name = config.container_name
    await db.delete(config)
    await db.commit()

    return {"success": True, "message": f"Configuration for '{container_name}' deleted"}


# ============================================================================
# History Endpoints
# ============================================================================


@router.get("/history", response_model=HistoryListResponse)
async def get_history(
    db: DbSession,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status"),
) -> HistoryListResponse:
    """Get paginated system notification history."""
    offset = (page - 1) * page_size

    # Get total count
    total = await SystemNotificationHistory.count(
        db, event_type=event_type, category=category, status=status
    )

    # Get history items
    items = await SystemNotificationHistory.get_recent(
        db,
        limit=page_size,
        offset=offset,
        event_type=event_type,
        category=category,
        status=status,
    )

    return HistoryListResponse(
        items=[
            SystemNotificationHistoryResponse(
                id=h.id,
                event_type=h.event_type,
                event_id=h.event_id,
                category=h.category,
                target_id=h.target_id,
                target_label=h.target_label,
                severity=h.severity,
                title=h.title,
                message=h.message,
                event_data=h.event_data,
                channels_sent=h.channels_sent,
                escalation_level=h.escalation_level,
                status=h.status,
                suppression_reason=h.suppression_reason,
                error_message=h.error_message,
                triggered_at=h.triggered_at,
                sent_at=h.sent_at,
            )
            for h in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/history/stats", response_model=HistoryStatsResponse)
async def get_history_stats(db: DbSession) -> HistoryStatsResponse:
    """Get notification history statistics."""
    from sqlalchemy import func

    # Get counts by status
    sent_count = await SystemNotificationHistory.count(db, status="sent")
    failed_count = await SystemNotificationHistory.count(db, status="failed")
    suppressed_count = await SystemNotificationHistory.count(db, status="suppressed")
    batched_count = await SystemNotificationHistory.count(db, status="batched")
    total = sent_count + failed_count + suppressed_count + batched_count

    # Get counts by category
    result = await db.execute(
        select(
            SystemNotificationHistory.category,
            func.count(SystemNotificationHistory.id),
        ).group_by(SystemNotificationHistory.category)
    )
    by_category = {row[0]: row[1] for row in result.all()}

    # Get counts by severity
    result = await db.execute(
        select(
            SystemNotificationHistory.severity,
            func.count(SystemNotificationHistory.id),
        ).group_by(SystemNotificationHistory.severity)
    )
    by_severity = {row[0]: row[1] for row in result.all()}

    return HistoryStatsResponse(
        total_notifications=total,
        sent_count=sent_count,
        failed_count=failed_count,
        suppressed_count=suppressed_count,
        batched_count=batched_count,
        by_category=by_category,
        by_severity=by_severity,
    )


@router.delete("/history/cleanup")
async def cleanup_history(
    db: DbSession,
    admin: AdminUser,
    days: int = Query(60, ge=1, le=365, description="Delete records older than X days"),
) -> dict:
    """Clean up old notification history records."""
    deleted = await SystemNotificationHistory.cleanup_old_records(db, days=days)

    return {
        "success": True,
        "deleted_count": deleted,
        "message": f"Deleted {deleted} records older than {days} days",
    }


# ============================================================================
# Action Endpoints
# ============================================================================


@router.post("/trigger", response_model=TriggerNotificationResponse)
async def trigger_notification(
    data: TriggerNotificationRequest,
    db: DbSession,
    admin: AdminUser,
) -> TriggerNotificationResponse:
    """Manually trigger a notification for testing."""
    result = await system_notification_engine.trigger_notification(
        db=db,
        event_type=data.event_type,
        target_id=data.target_id,
        event_data=data.event_data,
        skip_rate_limiting=data.skip_rate_limiting,
    )

    return TriggerNotificationResponse(
        success=result.success,
        message="Notification triggered" if result.success else f"Notification {result.status}",
        history_id=result.history_id,
        suppression_reason=result.suppression_reason,
    )


@router.post("/test-event/{event_type}")
async def test_event(
    event_type: str,
    db: DbSession,
    admin: AdminUser,
) -> TriggerNotificationResponse:
    """Test a specific event type with sample data."""
    # Sample data for different event types
    sample_data = {
        "generator_started": {"start_time": "2026-01-19 12:00:00", "reason": "Manual"},
        "generator_stopped": {"reason": "Manual", "runtime": "2h 30m", "fuel_gallons": "5.2", "fuel_type": "propane"},
        "genslave_comm_lost": {"time": "2026-01-19 12:00:00"},
        "genslave_comm_restored": {"relay_status": "ENABLED", "relay_warning": ""},
        "container_unhealthy": {"container_name": "test-container"},
        "container_stopped": {"container_name": "test-container"},
    }

    event_data = sample_data.get(event_type, {"time": "2026-01-19 12:00:00"})

    result = await system_notification_engine.trigger_notification(
        db=db,
        event_type=event_type,
        event_data=event_data,
        skip_rate_limiting=True,
    )

    return TriggerNotificationResponse(
        success=result.success,
        message=f"Test notification for '{event_type}' {result.status}",
        history_id=result.history_id,
        suppression_reason=result.suppression_reason,
    )
