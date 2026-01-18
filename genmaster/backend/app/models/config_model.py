# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/config_model.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Configuration model - singleton table for system configuration."""

from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Config(Base):
    """
    Stores system configuration.

    Always exactly one row with id=1.
    """

    __tablename__ = "config"
    __table_args__ = (CheckConstraint("id = 1", name="chk_config_single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Heartbeat Settings
    heartbeat_interval_seconds: Mapped[int] = mapped_column(default=60)
    heartbeat_failure_threshold: Mapped[int] = mapped_column(default=3)

    # GenSlave Connection
    slave_api_url: Mapped[str] = mapped_column(
        nullable=False, default="http://genslave:8001"
    )
    slave_api_secret: Mapped[str] = mapped_column(nullable=False, default="change-me")
    genslave_ip: Mapped[Optional[str]] = mapped_column(nullable=True)
    genslave_hostname: Mapped[str] = mapped_column(nullable=False, default="genslave")

    # Webhook Settings
    webhook_base_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(nullable=True)
    webhook_enabled: Mapped[bool] = mapped_column(default=True)

    # Health Thresholds
    temp_warning_celsius: Mapped[int] = mapped_column(default=70)
    temp_critical_celsius: Mapped[int] = mapped_column(default=80)
    disk_warning_percent: Mapped[int] = mapped_column(default=80)
    disk_critical_percent: Mapped[int] = mapped_column(default=90)
    ram_warning_percent: Mapped[int] = mapped_column(default=85)

    # Networking
    tailscale_hostname: Mapped[Optional[str]] = mapped_column(nullable=True)
    tailscale_ip: Mapped[Optional[str]] = mapped_column(nullable=True)
    cloudflare_enabled: Mapped[bool] = mapped_column(default=False)
    cloudflare_hostname: Mapped[Optional[str]] = mapped_column(nullable=True)

    # SSL Configuration
    ssl_enabled: Mapped[bool] = mapped_column(default=False)
    ssl_domain: Mapped[Optional[str]] = mapped_column(nullable=True)
    ssl_email: Mapped[Optional[str]] = mapped_column(nullable=True)
    ssl_dns_provider: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Event Log Retention
    event_log_retention_days: Mapped[int] = mapped_column(default=30)

    # Metadata
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    async def get_instance(cls, db: AsyncSession) -> "Config":
        """Get or create the singleton config row."""
        result = await db.execute(select(cls).where(cls.id == 1))
        config = result.scalar_one_or_none()
        if not config:
            raise RuntimeError("Config row not found - run migrations first")
        return config
