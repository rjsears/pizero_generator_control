# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/notifications.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Notification management API endpoints."""

from typing import List

from fastapi import APIRouter, HTTPException
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, DbSession
from app.models import NotificationChannel, NotificationGroup, NotificationHistory
from app.schemas import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationGroupCreate,
    NotificationGroupResponse,
    NotificationGroupUpdate,
    NotificationHistoryResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    TestChannelRequest,
    TestChannelResponse,
)
from app.services.notification_service import notification_service, slugify

router = APIRouter()


# ============================================================================
# Channel Endpoints
# ============================================================================


@router.get("/channels", response_model=List[NotificationChannelResponse])
async def list_channels(db: DbSession) -> List[NotificationChannelResponse]:
    """Get all notification channels."""
    channels = await NotificationChannel.get_all(db)
    return [
        NotificationChannelResponse(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            channel_type=c.channel_type,
            config=_mask_sensitive_config(c.config, c.channel_type),
            enabled=c.enabled,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in channels
    ]


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def get_channel(channel_id: int, db: DbSession) -> NotificationChannelResponse:
    """Get a specific notification channel."""
    channel = await NotificationChannel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    return NotificationChannelResponse(
        id=channel.id,
        name=channel.name,
        slug=channel.slug,
        description=channel.description,
        channel_type=channel.channel_type,
        config=_mask_sensitive_config(channel.config, channel.channel_type),
        enabled=channel.enabled,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.post("/channels", response_model=NotificationChannelResponse)
async def create_channel(
    data: NotificationChannelCreate,
    db: DbSession,
    admin: AdminUser,
) -> NotificationChannelResponse:
    """Create a new notification channel."""
    # Generate slug from name
    slug = slugify(data.name)

    # Check for duplicate slug
    existing = await NotificationChannel.get_by_slug(db, slug)
    if existing:
        raise HTTPException(status_code=400, detail="Channel with this name already exists")

    # Create channel
    channel = NotificationChannel(
        name=data.name,
        slug=slug,
        description=data.description,
        channel_type=data.channel_type.value,
        config=data.config,
        enabled=data.enabled,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)

    return NotificationChannelResponse(
        id=channel.id,
        name=channel.name,
        slug=channel.slug,
        description=channel.description,
        channel_type=channel.channel_type,
        config=_mask_sensitive_config(channel.config, channel.channel_type),
        enabled=channel.enabled,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_channel(
    channel_id: int,
    data: NotificationChannelUpdate,
    db: DbSession,
    admin: AdminUser,
) -> NotificationChannelResponse:
    """Update a notification channel."""
    channel = await NotificationChannel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Update fields
    if data.name is not None:
        channel.name = data.name
        channel.slug = slugify(data.name)
    if data.description is not None:
        channel.description = data.description
    if data.config is not None:
        # Merge config, preserving password if masked
        new_config = data.config.copy()
        if channel.channel_type == "email":
            if new_config.get("password") == "********":
                new_config["password"] = channel.config.get("password", "")
        channel.config = new_config
    if data.enabled is not None:
        channel.enabled = data.enabled

    await db.commit()
    await db.refresh(channel)

    return NotificationChannelResponse(
        id=channel.id,
        name=channel.name,
        slug=channel.slug,
        description=channel.description,
        channel_type=channel.channel_type,
        config=_mask_sensitive_config(channel.config, channel.channel_type),
        enabled=channel.enabled,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


@router.delete("/channels/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """Delete a notification channel."""
    channel = await NotificationChannel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    await db.delete(channel)
    await db.commit()

    return {"success": True, "message": f"Channel '{channel.name}' deleted"}


@router.post("/channels/{channel_id}/test", response_model=TestChannelResponse)
async def test_channel(
    channel_id: int,
    data: TestChannelRequest,
    db: DbSession,
    admin: AdminUser,
) -> TestChannelResponse:
    """Test a notification channel."""
    channel = await NotificationChannel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    result = await notification_service.test_channel(
        db, channel, data.title, data.message
    )

    return TestChannelResponse(
        success=result.success,
        message="Test notification sent successfully" if result.success else "Test failed",
        error=result.error,
    )


@router.post("/channels/{channel_id}/toggle")
async def toggle_channel(
    channel_id: int,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """Toggle a channel's enabled status."""
    channel = await NotificationChannel.get_by_id(db, channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.enabled = not channel.enabled
    await db.commit()

    return {
        "success": True,
        "enabled": channel.enabled,
        "message": f"Channel {'enabled' if channel.enabled else 'disabled'}",
    }


# ============================================================================
# Group Endpoints
# ============================================================================


@router.get("/groups", response_model=List[NotificationGroupResponse])
async def list_groups(db: DbSession) -> List[NotificationGroupResponse]:
    """Get all notification groups with their channels."""
    result = await db.execute(
        select(NotificationGroup)
        .options(selectinload(NotificationGroup.channels))
        .order_by(NotificationGroup.name)
    )
    groups = result.scalars().all()

    return [
        NotificationGroupResponse(
            id=g.id,
            name=g.name,
            slug=g.slug,
            description=g.description,
            enabled=g.enabled,
            channels=[
                NotificationChannelResponse(
                    id=c.id,
                    name=c.name,
                    slug=c.slug,
                    description=c.description,
                    channel_type=c.channel_type,
                    config=_mask_sensitive_config(c.config, c.channel_type),
                    enabled=c.enabled,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
                for c in g.channels
            ],
            created_at=g.created_at,
            updated_at=g.updated_at,
        )
        for g in groups
    ]


@router.get("/groups/{group_id}", response_model=NotificationGroupResponse)
async def get_group(group_id: int, db: DbSession) -> NotificationGroupResponse:
    """Get a specific notification group."""
    result = await db.execute(
        select(NotificationGroup)
        .options(selectinload(NotificationGroup.channels))
        .where(NotificationGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return NotificationGroupResponse(
        id=group.id,
        name=group.name,
        slug=group.slug,
        description=group.description,
        enabled=group.enabled,
        channels=[
            NotificationChannelResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description,
                channel_type=c.channel_type,
                config=_mask_sensitive_config(c.config, c.channel_type),
                enabled=c.enabled,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in group.channels
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.post("/groups", response_model=NotificationGroupResponse)
async def create_group(
    data: NotificationGroupCreate,
    db: DbSession,
    admin: AdminUser,
) -> NotificationGroupResponse:
    """Create a new notification group."""
    # Generate slug from name
    slug = slugify(data.name)

    # Check for duplicate slug
    existing = await NotificationGroup.get_by_slug(db, slug)
    if existing:
        raise HTTPException(status_code=400, detail="Group with this name already exists")

    # Create group
    group = NotificationGroup(
        name=data.name,
        slug=slug,
        description=data.description,
        enabled=data.enabled,
    )

    # Add channels
    if data.channel_ids:
        for channel_id in data.channel_ids:
            channel = await NotificationChannel.get_by_id(db, channel_id)
            if channel:
                group.channels.append(channel)

    db.add(group)
    await db.commit()

    # Reload with channels
    result = await db.execute(
        select(NotificationGroup)
        .options(selectinload(NotificationGroup.channels))
        .where(NotificationGroup.id == group.id)
    )
    group = result.scalar_one()

    return NotificationGroupResponse(
        id=group.id,
        name=group.name,
        slug=group.slug,
        description=group.description,
        enabled=group.enabled,
        channels=[
            NotificationChannelResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description,
                channel_type=c.channel_type,
                config=_mask_sensitive_config(c.config, c.channel_type),
                enabled=c.enabled,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in group.channels
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.put("/groups/{group_id}", response_model=NotificationGroupResponse)
async def update_group(
    group_id: int,
    data: NotificationGroupUpdate,
    db: DbSession,
    admin: AdminUser,
) -> NotificationGroupResponse:
    """Update a notification group."""
    result = await db.execute(
        select(NotificationGroup)
        .options(selectinload(NotificationGroup.channels))
        .where(NotificationGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Update fields
    if data.name is not None:
        group.name = data.name
        group.slug = slugify(data.name)
    if data.description is not None:
        group.description = data.description
    if data.enabled is not None:
        group.enabled = data.enabled
    if data.channel_ids is not None:
        # Update channels
        group.channels.clear()
        for channel_id in data.channel_ids:
            channel = await NotificationChannel.get_by_id(db, channel_id)
            if channel:
                group.channels.append(channel)

    await db.commit()

    # Reload with channels
    result = await db.execute(
        select(NotificationGroup)
        .options(selectinload(NotificationGroup.channels))
        .where(NotificationGroup.id == group.id)
    )
    group = result.scalar_one()

    return NotificationGroupResponse(
        id=group.id,
        name=group.name,
        slug=group.slug,
        description=group.description,
        enabled=group.enabled,
        channels=[
            NotificationChannelResponse(
                id=c.id,
                name=c.name,
                slug=c.slug,
                description=c.description,
                channel_type=c.channel_type,
                config=_mask_sensitive_config(c.config, c.channel_type),
                enabled=c.enabled,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in group.channels
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: int,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """Delete a notification group."""
    group = await NotificationGroup.get_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    await db.delete(group)
    await db.commit()

    return {"success": True, "message": f"Group '{group.name}' deleted"}


# ============================================================================
# History Endpoints
# ============================================================================


@router.get("/history", response_model=List[NotificationHistoryResponse])
async def get_history(
    db: DbSession,
    limit: int = 50,
    channel_id: int = None,
) -> List[NotificationHistoryResponse]:
    """Get notification history."""
    query = (
        select(NotificationHistory)
        .options(selectinload(NotificationHistory.channel))
        .order_by(NotificationHistory.sent_at.desc())
        .limit(limit)
    )
    if channel_id:
        query = query.where(NotificationHistory.channel_id == channel_id)

    result = await db.execute(query)
    history = result.scalars().all()

    return [
        NotificationHistoryResponse(
            id=h.id,
            channel_id=h.channel_id,
            channel_name=h.channel.name if h.channel else None,
            event_type=h.event_type,
            title=h.title,
            message=h.message,
            success=h.success,
            error_message=h.error_message,
            sent_at=h.sent_at,
        )
        for h in history
    ]


# ============================================================================
# Send Notification Endpoint
# ============================================================================


@router.post("/send", response_model=SendNotificationResponse)
async def send_notification(
    data: SendNotificationRequest,
    db: DbSession,
    admin: AdminUser,
) -> SendNotificationResponse:
    """Send a notification to specified channels/groups."""
    results = await notification_service.send_notification(
        db=db,
        event_type=data.event_type.value,
        title=data.title,
        message=data.message,
        channel_ids=data.channel_ids,
        group_ids=data.group_ids,
    )

    total_sent = sum(1 for r in results if r.success)
    total_failed = sum(1 for r in results if not r.success)

    return SendNotificationResponse(
        success=total_failed == 0,
        total_sent=total_sent,
        total_failed=total_failed,
        results=[
            {
                "channel_id": r.channel_id,
                "channel_name": r.channel_name,
                "success": r.success,
                "error": r.error,
            }
            for r in results
        ],
    )


# ============================================================================
# Helper Functions
# ============================================================================


def _mask_sensitive_config(config: dict, channel_type: str) -> dict:
    """Mask sensitive fields in channel config."""
    masked = config.copy()
    if channel_type == "email" and "password" in masked:
        masked["password"] = "********"
    return masked
