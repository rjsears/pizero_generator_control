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
from app.models import Config, SystemState
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
        runtime_limits_enabled=config.runtime_limits_enabled,
        min_run_minutes=config.min_run_minutes,
        max_run_minutes=config.max_run_minutes,
        max_runtime_action=config.max_runtime_action,
        cooldown_duration_minutes=config.cooldown_duration_minutes,
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

    # Validate max_run_minutes > min_run_minutes
    new_min = update_data.get("min_run_minutes", config.min_run_minutes)
    new_max = update_data.get("max_run_minutes", config.max_run_minutes)
    if new_max <= new_min:
        raise HTTPException(
            status_code=400,
            detail=f"max_run_minutes ({new_max}) must be greater than min_run_minutes ({new_min})"
        )

    # Check if runtime_limits_enabled is being disabled
    was_enabled = config.runtime_limits_enabled
    will_be_disabled = update_data.get("runtime_limits_enabled") is False

    for field, value in update_data.items():
        setattr(config, field, value)

    # If runtime limits is being disabled, clear any active lockout or cooldown
    if was_enabled and will_be_disabled:
        state_result = await db.execute(select(SystemState).where(SystemState.id == 1))
        state = state_result.scalar_one_or_none()
        if state:
            if state.runtime_lockout_active:
                state.runtime_lockout_active = False
                state.runtime_lockout_started = None
                state.runtime_lockout_reason = None
            if state.cooldown_active:
                state.cooldown_active = False
                state.cooldown_end_time = None

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
        runtime_limits_enabled=config.runtime_limits_enabled,
        min_run_minutes=config.min_run_minutes,
        max_run_minutes=config.max_run_minutes,
        max_runtime_action=config.max_runtime_action,
        cooldown_duration_minutes=config.cooldown_duration_minutes,
    )
