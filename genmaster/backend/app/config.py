# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/config.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_env: str = "production"
    app_debug: bool = False
    app_secret_key: str = "change-me-in-production"

    # PostgreSQL Database
    database_host: str = "db"
    database_port: int = 5432
    database_user: str = "genmaster"
    database_password: str = "change-me"
    database_name: str = "genmaster"

    # Redis Cache
    redis_url: str = "redis://redis:6379/0"
    redis_config_ttl: int = 300  # 5 minutes TTL for config cache

    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL URL for asyncpg."""
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Construct sync PostgreSQL URL for Alembic migrations."""
        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    # GenSlave Communication
    slave_api_url: str = "http://genslave:8001"
    slave_api_secret: str = "change-me"
    genslave_ip: Optional[str] = None

    # Heartbeat Settings
    # 10s default → GenSlave's failsafe trips at 30s without a heartbeat (3x rule).
    heartbeat_interval_seconds: int = 10
    heartbeat_failure_threshold: int = 3

    # CORS — empty by default = same-origin only (browser default enforcement).
    # All production access paths (Cloudflare Tunnel, LAN, Tailscale Serve)
    # are same-origin via nginx, so no CORS is needed in production. Set to a
    # comma-separated list of dev origins (e.g. "http://localhost:5173") only
    # when running the Vue dev server against a separately-running backend.
    cors_allowed_origins: List[str] = []

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        """Accept a comma-separated string from env vars and split into a list."""
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Webhook Settings (n8n)
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_enabled: bool = False

    # GPIO Settings
    victron_gpio_pin: int = 17
    gpio_mock_mode: Optional[bool] = None  # Auto-detect if None

    # HOA Selector (3-position rotary at GenMaster panel: Quiet/Auto/Run).
    # GPIO22 and GPIO27 are placed adjacent to the existing GPIO17 Victron
    # input so all three operator-side signals share a tight block of
    # header pins (11/13/15) with one shared GND at pin 9.
    hoa_switch_enabled: bool = True
    hoa_gpio_quiet: int = 22
    hoa_gpio_run: int = 27
    # Wait this long after startup before honoring the switch position,
    # so a stale physical position can't trigger an automatic run the
    # instant the system recovers from a power blip. Set to 0 in .env
    # while bench-testing if you don't want to wait between restarts.
    hoa_boot_delay_seconds: int = 30

    @property
    def is_mock_gpio(self) -> bool:
        """Determine if GPIO should run in mock mode."""
        if self.gpio_mock_mode is not None:
            return self.gpio_mock_mode
        return not self._is_raspberry_pi()

    @staticmethod
    def _is_raspberry_pi() -> bool:
        """Check if running on a Raspberry Pi."""
        try:
            with open("/proc/cpuinfo", "r") as f:
                return "Raspberry Pi" in f.read()
        except (FileNotFoundError, PermissionError):
            return False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
