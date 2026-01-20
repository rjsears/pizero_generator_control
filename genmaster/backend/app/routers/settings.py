# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/settings.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Key-value settings API endpoints."""

import logging
from typing import Any, Dict, List
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import AdminUser, DbSession
from app.models import Settings
from app.schemas import WebhookConfig
from app.schemas.access_control import (
    AccessControlResponse,
    AccessControlUpdateRequest,
    AddIPRangeRequest,
    IPRange,
    IPRangeActionResponse,
    NginxReloadResponse,
    UpdateIPRangeRequest,
)
from app.services.access_control import (
    NGINX_CONFIG_PATH,
    generate_nginx_geo_block,
    get_config_last_modified,
    get_default_ip_ranges,
    is_protected_range,
    parse_nginx_geo_block,
    reload_nginx,
    update_nginx_config_geo_block,
)
from app.services.webhook import WebhookService

logger = logging.getLogger(__name__)

router = APIRouter()


class SettingValue(BaseModel):
    """Setting value wrapper."""

    value: Any
    description: str | None = None


class SettingResponse(BaseModel):
    """Setting response."""

    key: str
    value: Any
    description: str | None
    updated_at: str


@router.get("", response_model=List[SettingResponse])
@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(
    db: DbSession,
) -> List[SettingResponse]:
    """
    Get all settings.
    """
    settings = await Settings.get_all(db)
    return [
        SettingResponse(
            key=s.key,
            value=s.value,
            description=s.description,
            updated_at=s.updated_at.isoformat(),
        )
        for s in settings
    ]


# Debug Mode endpoints
# NOTE: These must be defined BEFORE the /{key} catch-all route


class DebugModeResponse(BaseModel):
    """Debug mode response."""

    enabled: bool


class DebugModeRequest(BaseModel):
    """Debug mode update request."""

    enabled: bool


@router.get("/debug", response_model=DebugModeResponse)
async def get_debug_mode(
    db: DbSession,
) -> DebugModeResponse:
    """
    Get current debug mode status.
    """
    setting = await Settings.get(db, "debug_mode")
    enabled = setting.value if setting else False
    return DebugModeResponse(enabled=bool(enabled))


@router.put("/debug", response_model=DebugModeResponse)
async def set_debug_mode(
    data: DebugModeRequest,
    db: DbSession,
    admin: AdminUser,
) -> DebugModeResponse:
    """
    Set debug mode.

    Requires admin authentication.
    """
    await Settings.set(db, "debug_mode", data.enabled, "Enable debug mode")
    return DebugModeResponse(enabled=data.enabled)


# Security Settings endpoints
# NOTE: These must be defined BEFORE the /{key} catch-all route


class SecuritySettingsResponse(BaseModel):
    """Security settings response."""

    session_timeout: int = 30
    max_login_attempts: int = 5
    lockout_duration: int = 15


class SecuritySettingsRequest(BaseModel):
    """Security settings update request."""

    value: SecuritySettingsResponse


@router.get("/security", response_model=Dict[str, Any])
async def get_security_settings(
    db: DbSession,
) -> Dict[str, Any]:
    """
    Get security settings.
    """
    setting = await Settings.get(db, "security")
    if setting and isinstance(setting.value, dict):
        return {"value": setting.value}
    # Return defaults
    return {
        "value": {
            "session_timeout": 30,
            "max_login_attempts": 5,
            "lockout_duration": 15,
        }
    }


@router.put("/security", response_model=Dict[str, Any])
async def set_security_settings(
    data: SecuritySettingsRequest,
    db: DbSession,
    admin: AdminUser,
) -> Dict[str, Any]:
    """
    Set security settings.

    Requires admin authentication.
    """
    await Settings.set(
        db,
        "security",
        data.value.model_dump(),
        "Security settings (session timeout, login attempts, lockout)",
    )
    return {"value": data.value.model_dump()}


# Generic key-value settings endpoints
# NOTE: These catch-all routes must come AFTER specific routes like /debug and /security


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: DbSession,
) -> SettingResponse:
    """
    Get a specific setting by key.
    """
    setting = await Settings.get(db, key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return SettingResponse(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        updated_at=setting.updated_at.isoformat(),
    )


@router.put("/{key}", response_model=SettingResponse)
async def set_setting(
    key: str,
    data: SettingValue,
    db: DbSession,
    admin: AdminUser,
) -> SettingResponse:
    """
    Set or update a setting.

    Requires admin authentication.
    """
    setting = await Settings.set(db, key, data.value, data.description)
    return SettingResponse(
        key=setting.key,
        value=setting.value,
        description=setting.description,
        updated_at=setting.updated_at.isoformat(),
    )


@router.delete("/{key}")
async def delete_setting(
    key: str,
    db: DbSession,
    admin: AdminUser,
) -> dict:
    """
    Delete a setting.

    Requires admin authentication.
    """
    setting = await Settings.get(db, key)
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    await db.delete(setting)
    await db.commit()

    return {"success": True, "message": f"Setting '{key}' deleted"}


# Webhook-specific endpoints


@router.get("/webhooks/config", response_model=WebhookConfig)
async def get_webhook_config(
    db: DbSession,
) -> WebhookConfig:
    """
    Get webhook configuration.

    Note: Secret is masked in response.
    """
    from app.models import Config

    config = await Config.get_instance(db)
    return WebhookConfig(
        base_url=config.webhook_base_url,
        secret="********" if config.webhook_secret else None,
        enabled=config.webhook_enabled,
    )


@router.put("/webhooks/config", response_model=WebhookConfig)
async def update_webhook_config(
    data: WebhookConfig,
    db: DbSession,
    admin: AdminUser,
) -> WebhookConfig:
    """
    Update webhook configuration.

    Requires admin authentication.
    """
    from sqlalchemy.future import select

    from app.models import Config

    result = await db.execute(select(Config).where(Config.id == 1))
    config = result.scalar_one_or_none()

    if data.base_url is not None:
        config.webhook_base_url = data.base_url
    if data.secret is not None and data.secret != "********":
        config.webhook_secret = data.secret
    config.webhook_enabled = data.enabled

    await db.commit()

    return WebhookConfig(
        base_url=config.webhook_base_url,
        secret="********" if config.webhook_secret else None,
        enabled=config.webhook_enabled,
    )


@router.post("/webhooks/test")
async def test_webhook() -> dict:
    """
    Send a test webhook.
    """
    service = WebhookService()
    result = await service.send_test()
    await service.close()

    if result.success:
        return {
            "success": True,
            "message": "Test webhook sent successfully",
            "status_code": result.status_code,
            "response_time_ms": result.response_time_ms,
        }
    else:
        return {
            "success": False,
            "message": "Test webhook failed",
            "error": result.error,
        }


# Access Control endpoints


def _read_nginx_config() -> str:
    """Read nginx config file content."""
    from pathlib import Path

    path = Path(NGINX_CONFIG_PATH)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Nginx config not found at {NGINX_CONFIG_PATH}",
        )
    return path.read_text()


@router.get("/access-control", response_model=AccessControlResponse)
async def get_access_control(
    admin: AdminUser,
) -> AccessControlResponse:
    """
    Get current access control configuration.

    Returns the geo block IP ranges from nginx.conf.
    Requires admin authentication.
    """
    try:
        config_content = _read_nginx_config()
        ip_ranges = parse_nginx_geo_block(config_content)
        last_modified = get_config_last_modified(NGINX_CONFIG_PATH)

        return AccessControlResponse(
            enabled=len(ip_ranges) > 0,
            ip_ranges=ip_ranges,
            nginx_config_path=NGINX_CONFIG_PATH,
            last_updated=last_modified,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get access control config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/access-control", response_model=AccessControlResponse)
async def update_access_control(
    data: AccessControlUpdateRequest,
    admin: AdminUser,
) -> AccessControlResponse:
    """
    Replace all IP ranges at once.

    This will update the nginx.conf geo block with the provided IP ranges.
    Requires admin authentication.
    """
    try:
        # Ensure localhost is always included and protected
        has_localhost = any(r.cidr == "127.0.0.1/32" for r in data.ip_ranges)
        if not has_localhost:
            data.ip_ranges.insert(
                0,
                IPRange(
                    cidr="127.0.0.1/32",
                    description="Localhost (protected)",
                    access_level="internal",
                    protected=True,
                ),
            )

        # Update nginx config
        success, message = update_nginx_config_geo_block(
            NGINX_CONFIG_PATH, data.ip_ranges
        )
        if not success:
            raise HTTPException(status_code=500, detail=message)

        # Return updated config
        config_content = _read_nginx_config()
        ip_ranges = parse_nginx_geo_block(config_content)
        last_modified = get_config_last_modified(NGINX_CONFIG_PATH)

        return AccessControlResponse(
            enabled=len(ip_ranges) > 0,
            ip_ranges=ip_ranges,
            nginx_config_path=NGINX_CONFIG_PATH,
            last_updated=last_modified,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update access control: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/access-control/ip", response_model=IPRangeActionResponse)
async def add_ip_range(
    data: AddIPRangeRequest,
    admin: AdminUser,
) -> IPRangeActionResponse:
    """
    Add a single IP range to the access control list.

    Requires admin authentication.
    """
    try:
        # Read current config
        config_content = _read_nginx_config()
        ip_ranges = parse_nginx_geo_block(config_content)

        # Check if CIDR already exists
        if any(r.cidr == data.cidr for r in ip_ranges):
            raise HTTPException(
                status_code=400,
                detail=f"IP range {data.cidr} already exists",
            )

        # Add new range
        new_range = IPRange(
            cidr=data.cidr,
            description=data.description or "",
            access_level=data.access_level,
            protected=is_protected_range(data.cidr),
        )
        ip_ranges.append(new_range)

        # Update nginx config
        success, message = update_nginx_config_geo_block(NGINX_CONFIG_PATH, ip_ranges)
        if not success:
            raise HTTPException(status_code=500, detail=message)

        return IPRangeActionResponse(
            success=True,
            message=f"Added IP range {data.cidr}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add IP range: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/access-control/ip/{cidr:path}", response_model=IPRangeActionResponse)
async def update_ip_range(
    cidr: str,
    data: UpdateIPRangeRequest,
    admin: AdminUser,
) -> IPRangeActionResponse:
    """
    Update an IP range's description.

    The CIDR in the URL should be URL-encoded (e.g., 10.0.0.0%2F8).
    Requires admin authentication.
    """
    try:
        # Decode CIDR from URL
        decoded_cidr = unquote(cidr)

        # Read current config
        config_content = _read_nginx_config()
        ip_ranges = parse_nginx_geo_block(config_content)

        # Find and update the range
        found = False
        for ip_range in ip_ranges:
            if ip_range.cidr == decoded_cidr:
                ip_range.description = data.description
                found = True
                break

        if not found:
            raise HTTPException(
                status_code=404,
                detail=f"IP range {decoded_cidr} not found",
            )

        # Update nginx config
        success, message = update_nginx_config_geo_block(NGINX_CONFIG_PATH, ip_ranges)
        if not success:
            raise HTTPException(status_code=500, detail=message)

        return IPRangeActionResponse(
            success=True,
            message=f"Updated IP range {decoded_cidr}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update IP range: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/access-control/ip/{cidr:path}", response_model=IPRangeActionResponse)
async def delete_ip_range(
    cidr: str,
    admin: AdminUser,
) -> IPRangeActionResponse:
    """
    Delete an IP range from the access control list.

    Protected ranges (like 127.0.0.1/32) cannot be deleted.
    The CIDR in the URL should be URL-encoded (e.g., 10.0.0.0%2F8).
    Requires admin authentication.
    """
    try:
        # Decode CIDR from URL
        decoded_cidr = unquote(cidr)

        # Check if protected
        if is_protected_range(decoded_cidr):
            raise HTTPException(
                status_code=400,
                detail=f"IP range {decoded_cidr} is protected and cannot be deleted",
            )

        # Read current config
        config_content = _read_nginx_config()
        ip_ranges = parse_nginx_geo_block(config_content)

        # Find and remove the range
        original_count = len(ip_ranges)
        ip_ranges = [r for r in ip_ranges if r.cidr != decoded_cidr]

        if len(ip_ranges) == original_count:
            raise HTTPException(
                status_code=404,
                detail=f"IP range {decoded_cidr} not found",
            )

        # Update nginx config
        success, message = update_nginx_config_geo_block(NGINX_CONFIG_PATH, ip_ranges)
        if not success:
            raise HTTPException(status_code=500, detail=message)

        return IPRangeActionResponse(
            success=True,
            message=f"Deleted IP range {decoded_cidr}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete IP range: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/access-control/reload-nginx", response_model=NginxReloadResponse)
async def reload_nginx_config(
    admin: AdminUser,
) -> NginxReloadResponse:
    """
    Reload nginx configuration.

    This tests the config first, then reloads if valid.
    Requires admin authentication.
    """
    try:
        success, message, output = reload_nginx()
        return NginxReloadResponse(
            success=success,
            message=message,
            output=output,
        )
    except Exception as e:
        logger.error(f"Failed to reload nginx: {e}")
        return NginxReloadResponse(
            success=False,
            message=f"Failed to reload nginx: {str(e)}",
            output=None,
        )


@router.get("/access-control/defaults", response_model=List[IPRange])
async def get_default_ip_ranges_endpoint(
    admin: AdminUser,
) -> List[IPRange]:
    """
    Get the default IP ranges for quick-add functionality.

    Returns common RFC1918 ranges and Tailscale range.
    Requires admin authentication.
    """
    return get_default_ip_ranges()
