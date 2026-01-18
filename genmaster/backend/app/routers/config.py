# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/config.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System configuration API endpoints."""

from fastapi import APIRouter, HTTPException
from sqlalchemy.future import select

from app.dependencies import AdminUser, DbSession
from app.models import Config
from app.schemas import ConfigResponse, ConfigUpdateRequest

router = APIRouter()


@router.get("", response_model=ConfigResponse)
@router.get("/", response_model=ConfigResponse)
async def get_config(
    db: DbSession,
) -> ConfigResponse:
    """
    Get system configuration.

    Includes slave_api_secret for admin configuration purposes.
    """
    result = await db.execute(select(Config).where(Config.id == 1))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Configuration not found")

    return ConfigResponse(
        heartbeat_interval_seconds=config.heartbeat_interval_seconds,
        heartbeat_failure_threshold=config.heartbeat_failure_threshold,
        slave_api_url=config.slave_api_url,
        slave_api_secret=config.slave_api_secret,
        genslave_ip=config.genslave_ip,
        genslave_hostname=config.genslave_hostname,
        webhook_base_url=config.webhook_base_url,
        webhook_enabled=config.webhook_enabled,
        temp_warning_celsius=config.temp_warning_celsius,
        temp_critical_celsius=config.temp_critical_celsius,
        disk_warning_percent=config.disk_warning_percent,
        disk_critical_percent=config.disk_critical_percent,
        ram_warning_percent=config.ram_warning_percent,
        tailscale_hostname=config.tailscale_hostname,
        tailscale_ip=config.tailscale_ip,
        cloudflare_enabled=config.cloudflare_enabled,
        cloudflare_hostname=config.cloudflare_hostname,
        ssl_enabled=config.ssl_enabled,
        ssl_domain=config.ssl_domain,
        event_log_retention_days=config.event_log_retention_days,
    )


@router.put("", response_model=ConfigResponse)
@router.put("/", response_model=ConfigResponse)
async def update_config(
    request: ConfigUpdateRequest,
    db: DbSession,
    admin: AdminUser,
) -> ConfigResponse:
    """
    Update system configuration.

    Requires admin authentication.
    """
    result = await db.execute(select(Config).where(Config.id == 1))
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=500, detail="Configuration not found")

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)

    return ConfigResponse(
        heartbeat_interval_seconds=config.heartbeat_interval_seconds,
        heartbeat_failure_threshold=config.heartbeat_failure_threshold,
        slave_api_url=config.slave_api_url,
        slave_api_secret=config.slave_api_secret,
        genslave_ip=config.genslave_ip,
        genslave_hostname=config.genslave_hostname,
        webhook_base_url=config.webhook_base_url,
        webhook_enabled=config.webhook_enabled,
        temp_warning_celsius=config.temp_warning_celsius,
        temp_critical_celsius=config.temp_critical_celsius,
        disk_warning_percent=config.disk_warning_percent,
        disk_critical_percent=config.disk_critical_percent,
        ram_warning_percent=config.ram_warning_percent,
        tailscale_hostname=config.tailscale_hostname,
        tailscale_ip=config.tailscale_ip,
        cloudflare_enabled=config.cloudflare_enabled,
        cloudflare_hostname=config.cloudflare_hostname,
        ssl_enabled=config.ssl_enabled,
        ssl_domain=config.ssl_domain,
        event_log_retention_days=config.event_log_retention_days,
    )
