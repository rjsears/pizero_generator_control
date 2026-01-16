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

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import AdminUser, get_db, require_admin
from app.models import Settings
from app.schemas import WebhookConfig
from app.services.webhook import WebhookService

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
    db: AsyncSession = Depends(get_db),
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


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
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
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
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
