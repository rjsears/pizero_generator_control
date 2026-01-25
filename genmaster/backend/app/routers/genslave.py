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

from app.dependencies import get_current_user
from app.services.slave_client import SlaveClient

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


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


# =========================================================================
# WiFi Configuration Endpoints
# =========================================================================


class WifiNetwork(BaseModel):
    """WiFi network information."""

    ssid: str = Field(description="Network SSID")
    signal_percent: int = Field(description="Signal strength as percentage")
    security: str = Field(description="Security type (Open, WPA, WPA2, etc.)")


class WifiScanResponse(BaseModel):
    """Response from WiFi network scan."""

    success: bool = Field(description="Whether the scan was successful")
    networks: list[WifiNetwork] = Field(default_factory=list, description="List of available networks")
    error: Optional[str] = Field(None, description="Error message if scan failed")


class WifiConnectRequest(BaseModel):
    """Request to connect to a WiFi network."""

    ssid: str = Field(..., min_length=1, max_length=32, description="WiFi network SSID")
    password: Optional[str] = Field(None, description="WiFi password (None for open networks)")


class WifiConnectResponse(BaseModel):
    """Response from WiFi connect attempt."""

    success: bool = Field(description="Whether connection was successful")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(None, description="Error message if connection failed")


@router.get("/wifi/networks", response_model=WifiScanResponse)
async def get_genslave_wifi_networks():
    """
    Scan for available WiFi networks on GenSlave.

    Proxies the request to GenSlave and returns a list of
    available networks with SSID, signal strength, and security type.
    """
    client = SlaveClient()
    try:
        response = await client.scan_wifi_networks()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to scan GenSlave WiFi networks: {response.error}",
            )

        return WifiScanResponse(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning GenSlave WiFi networks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/wifi/connect", response_model=WifiConnectResponse)
async def connect_genslave_wifi(request: WifiConnectRequest):
    """
    Connect GenSlave to a WiFi network.

    Proxies the connection request to GenSlave.
    Requires the SSID and optionally a password for secured networks.
    """
    client = SlaveClient()
    try:
        response = await client.connect_wifi(
            ssid=request.ssid,
            password=request.password,
        )

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to connect GenSlave WiFi: {response.error}",
            )

        return WifiConnectResponse(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting GenSlave WiFi: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


class WifiAddRequest(BaseModel):
    """Request to add a known WiFi network."""

    ssid: str = Field(..., min_length=1, max_length=32, description="WiFi network SSID")
    password: str = Field(..., min_length=8, max_length=63, description="WiFi password (WPA/WPA2)")
    auto_connect: bool = Field(True, description="Automatically connect when network is available")


class WifiAddResponse(BaseModel):
    """Response from adding a known WiFi network."""

    success: bool = Field(description="Whether the network was added successfully")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(None, description="Error message if adding failed")


class WifiSavedNetwork(BaseModel):
    """Saved WiFi network information."""

    name: str = Field(description="Connection profile name")
    ssid: str = Field(description="Network SSID")
    auto_connect: bool = Field(description="Whether auto-connect is enabled")


class WifiSavedListResponse(BaseModel):
    """Response listing saved WiFi networks."""

    success: bool = Field(description="Whether the list was retrieved successfully")
    networks: list[WifiSavedNetwork] = Field(default_factory=list, description="List of saved networks")
    error: Optional[str] = Field(None, description="Error message if listing failed")


class WifiDeleteRequest(BaseModel):
    """Request to delete a saved WiFi network."""

    name: str = Field(..., min_length=1, description="Connection profile name to delete")


class WifiDeleteResponse(BaseModel):
    """Response from deleting a saved WiFi network."""

    success: bool = Field(description="Whether the network was deleted successfully")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(None, description="Error message if deletion failed")


@router.get("/wifi/saved", response_model=WifiSavedListResponse)
async def list_genslave_saved_wifi():
    """
    List saved WiFi network profiles on GenSlave.

    Returns all WiFi connection profiles that have been configured,
    including those added for auto-connect.
    """
    client = SlaveClient()
    try:
        response = await client.list_saved_wifi_networks()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to list GenSlave saved WiFi networks: {response.error}",
            )

        return WifiSavedListResponse(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing GenSlave saved WiFi networks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/wifi/add", response_model=WifiAddResponse)
async def add_genslave_wifi(request: WifiAddRequest):
    """
    Add a known WiFi network to GenSlave for auto-connect.

    Creates a saved WiFi connection profile that will automatically
    connect when the network becomes available.
    """
    client = SlaveClient()
    try:
        response = await client.add_wifi_network(
            ssid=request.ssid,
            password=request.password,
            auto_connect=request.auto_connect,
        )

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to add GenSlave WiFi network: {response.error}",
            )

        return WifiAddResponse(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding GenSlave WiFi network: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/wifi/delete", response_model=WifiDeleteResponse)
async def delete_genslave_wifi(request: WifiDeleteRequest):
    """
    Delete a saved WiFi network from GenSlave.

    Removes a previously saved WiFi connection profile.
    """
    client = SlaveClient()
    try:
        response = await client.delete_wifi_network(name=request.name)

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to delete GenSlave WiFi network: {response.error}",
            )

        return WifiDeleteResponse(**response.data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting GenSlave WiFi network: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


# =========================================================================
# System Power Control Endpoints
# =========================================================================


class SystemActionResponse(BaseModel):
    """Response from GenSlave system action."""

    success: bool = Field(description="Whether the action was initiated")
    message: str = Field(description="Status message")
    action: str = Field(description="The action that was requested")


# Track intentional reboots to suppress "GenSlave down" messages
_intentional_reboot_until: int = 0


def set_intentional_reboot(duration_seconds: int = 120) -> None:
    """Mark that an intentional reboot is in progress."""
    import time
    global _intentional_reboot_until
    _intentional_reboot_until = int(time.time()) + duration_seconds
    logger.info(f"Intentional reboot marked for {duration_seconds}s")


def is_intentional_reboot() -> bool:
    """Check if we're in an intentional reboot window."""
    import time
    return time.time() < _intentional_reboot_until


@router.post("/shutdown", response_model=SystemActionResponse)
async def shutdown_genslave():
    """
    Shutdown GenSlave (Raspberry Pi).

    This will shut down the Raspberry Pi running GenSlave.
    The relay will be turned off for safety before shutdown.

    WARNING: This will make GenSlave unreachable until manually powered on.
    """
    client = SlaveClient()
    try:
        response = await client.shutdown()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to initiate GenSlave shutdown: {response.error}",
            )

        return SystemActionResponse(
            success=True,
            message="GenSlave shutdown initiated. System will power off shortly.",
            action="shutdown",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating GenSlave shutdown: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.post("/reboot", response_model=SystemActionResponse)
async def reboot_genslave():
    """
    Reboot GenSlave (Raspberry Pi).

    This will reboot the Raspberry Pi running GenSlave.
    The relay will be turned off for safety during the reboot.

    After reboot, GenSlave will start automatically and become available
    again (typically within 60-90 seconds).

    The system will suppress "GenSlave down" warnings for 2 minutes after
    an intentional reboot to prevent unnecessary alerts.
    """
    client = SlaveClient()
    try:
        response = await client.reboot()

        if not response.success:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to initiate GenSlave reboot: {response.error}",
            )

        # Mark this as an intentional reboot (suppress warnings for 2 minutes)
        set_intentional_reboot(120)

        return SystemActionResponse(
            success=True,
            message="GenSlave reboot initiated. System will restart in ~60-90 seconds.",
            action="reboot",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating GenSlave reboot: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close()


@router.get("/reboot-status")
async def get_reboot_status():
    """
    Check if we're in an intentional reboot window.

    This can be used by the frontend to suppress "GenSlave down" warnings
    after an intentional reboot.
    """
    import time
    in_reboot = is_intentional_reboot()
    remaining = max(0, _intentional_reboot_until - int(time.time()))

    return {
        "in_reboot_window": in_reboot,
        "remaining_seconds": remaining if in_reboot else 0,
    }
