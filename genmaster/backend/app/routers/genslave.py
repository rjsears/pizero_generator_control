# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/genslave.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 21st, 2026
#
# Proxy endpoints for managing GenSlave configuration,
# including notification settings.
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""GenSlave management API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.routers.auth import require_auth
from app.services.slave_client import SlaveClient

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])


# =========================================================================
# Schemas
# =========================================================================


class NotificationConfig(BaseModel):
    """GenSlave notification configuration."""

    apprise_urls: list[str] = Field(
        default_factory=list,
        description="List of Apprise notification URLs (masked)",
    )
    configured: bool = Field(description="Whether any URLs are configured")
    enabled: bool = Field(description="Whether notifications are enabled")


class NotificationUpdateRequest(BaseModel):
    """Request to update GenSlave notification URLs."""

    apprise_urls: list[str] = Field(
        description="List of Apprise notification URLs",
    )


class NotificationCooldownSettings(BaseModel):
    """GenSlave notification cooldown settings."""

    failsafe_cooldown_minutes: int = Field(
        description="Cooldown for failsafe notifications (minutes)"
    )
    restored_cooldown_minutes: int = Field(
        description="Cooldown for restored notifications (minutes)"
    )
    last_failsafe_notification_at: Optional[int] = Field(
        None, description="Unix timestamp of last failsafe notification"
    )
    last_restored_notification_at: Optional[int] = Field(
        None, description="Unix timestamp of last restored notification"
    )


class NotificationCooldownUpdateRequest(BaseModel):
    """Request to update GenSlave notification cooldown settings."""

    failsafe_cooldown_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=60,
        description="Cooldown for failsafe notifications (1-60 minutes)",
    )
    restored_cooldown_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=60,
        description="Cooldown for restored notifications (1-60 minutes)",
    )


class NotificationEnableRequest(BaseModel):
    """Request to enable/disable GenSlave notifications."""

    enabled: bool = Field(description="True to enable, False to disable")


class NotificationClearCooldownRequest(BaseModel):
    """Request to clear GenSlave notification cooldown."""

    event_type: Optional[str] = Field(
        None,
        description="Event type: 'failsafe', 'restored', or null for both",
    )


class GenSlaveResponse(BaseModel):
    """Standard response from GenSlave operations."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Status message")
    data: Optional[dict] = Field(None, description="Additional response data")


class NotificationTestResponse(BaseModel):
    """Response from GenSlave notification test."""

    success: bool = Field(description="Whether the test was sent")
    message: str = Field(description="Status message")
    configured_services: int = Field(
        default=0, description="Number of configured services"
    )


# =========================================================================
# Notification Endpoints
# =========================================================================


@router.get("/notifications", response_model=NotificationConfig)
async def get_genslave_notifications():
    """
    Get GenSlave notification configuration.

    Returns the configured Apprise URLs (masked for security),
    whether notifications are configured, and whether they are enabled.
    """
    client = SlaveClient()
    try:
        response = await client.get_notifications()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to get GenSlave notifications: {response.error}",
            )

        return NotificationConfig(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GenSlave notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/notifications", response_model=GenSlaveResponse)
async def update_genslave_notifications(request: NotificationUpdateRequest):
    """
    Update GenSlave Apprise notification URLs.

    Accepts a list of Apprise URLs. Supports 80+ notification services:
    - Telegram: tgram://bottoken/chatid
    - Slack: slack://tokenA/tokenB/tokenC/channel
    - Discord: discord://webhook_id/webhook_token
    - Twilio: twilio://account_sid:auth_token@from_phone/to_phone
    - Pushover: pover://user_key@api_token
    - Email: mailto://user:pass@gmail.com
    - And many more: https://github.com/caronc/apprise/wiki
    """
    client = SlaveClient()
    try:
        response = await client.set_notifications(request.apprise_urls)

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to update GenSlave notifications: {response.error}",
            )

        return GenSlaveResponse(
            success=True,
            message=response.data.get("message", "Notification URLs updated"),
            data=response.data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating GenSlave notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/notifications/settings", response_model=NotificationCooldownSettings)
async def get_genslave_notification_settings():
    """
    Get GenSlave notification cooldown settings.

    Returns the cooldown configuration for failsafe and restored
    notifications, including timestamps of last notifications sent.
    """
    client = SlaveClient()
    try:
        response = await client.get_notification_settings()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to get GenSlave notification settings: {response.error}",
            )

        return NotificationCooldownSettings(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting GenSlave notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/notifications/settings", response_model=GenSlaveResponse)
async def update_genslave_notification_settings(
    request: NotificationCooldownUpdateRequest,
):
    """
    Update GenSlave notification cooldown settings.

    Allows configuring cooldown periods to prevent notification flapping
    when communication with GenMaster is unstable.

    - failsafe_cooldown_minutes: How long to wait between failsafe notifications
    - restored_cooldown_minutes: How long to wait between restored notifications
    """
    client = SlaveClient()
    try:
        response = await client.set_notification_settings(
            failsafe_cooldown_minutes=request.failsafe_cooldown_minutes,
            restored_cooldown_minutes=request.restored_cooldown_minutes,
        )

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to update GenSlave notification settings: {response.error}",
            )

        return GenSlaveResponse(
            success=True,
            message=response.data.get("message", "Cooldown settings updated"),
            data=response.data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating GenSlave notification settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/notifications/test", response_model=NotificationTestResponse)
async def test_genslave_notifications():
    """
    Send a test notification from GenSlave.

    This sends a test message to all configured notification services
    on GenSlave. Use this to verify the notification configuration is working.
    """
    client = SlaveClient()
    try:
        response = await client.test_notifications()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to send GenSlave test notification: {response.error}",
            )

        return NotificationTestResponse(
            success=response.data.get("success", False),
            message=response.data.get("message", "Test notification sent"),
            configured_services=response.data.get("configured_services", 0),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending GenSlave test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/notifications/enable", response_model=GenSlaveResponse)
async def set_genslave_notifications_enabled(request: NotificationEnableRequest):
    """
    Enable or disable GenSlave notifications.

    When disabled, no notifications will be sent from GenSlave
    (except test notifications). This allows temporarily muting
    notifications without removing the configuration.
    """
    client = SlaveClient()
    try:
        response = await client.set_notifications_enabled(request.enabled)

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to update GenSlave notification state: {response.error}",
            )

        state = "enabled" if request.enabled else "disabled"
        return GenSlaveResponse(
            success=True,
            message=f"GenSlave notifications {state}",
            data=response.data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating GenSlave notification state: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/notifications/clear-cooldown", response_model=GenSlaveResponse)
async def clear_genslave_notification_cooldown(request: NotificationClearCooldownRequest):
    """
    Clear GenSlave notification cooldown state.

    This allows forcing a notification to be sent immediately,
    bypassing the cooldown period. Useful for testing or when
    you need to ensure a notification is sent.

    - event_type: "failsafe", "restored", or null/omit for both
    """
    client = SlaveClient()
    try:
        event_type = request.event_type
        if event_type and event_type not in ("failsafe", "restored"):
            raise HTTPException(
                status_code=400,
                detail="Invalid event_type. Use 'failsafe', 'restored', or null for both.",
            )

        response = await client.clear_notification_cooldown(event_type)

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to clear GenSlave notification cooldown: {response.error}",
            )

        cleared = event_type or "all"
        return GenSlaveResponse(
            success=True,
            message=f"Cooldown cleared for {cleared} notifications",
            data=response.data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing GenSlave notification cooldown: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()
