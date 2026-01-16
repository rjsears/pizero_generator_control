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
from typing import Optional

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
    slave_api_url: str = "http://genslave:8000"
    slave_api_secret: str = "change-me"

    # Heartbeat Settings
    heartbeat_interval_seconds: int = 60
    heartbeat_failure_threshold: int = 3

    # Webhook Settings (n8n)
    webhook_base_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_enabled: bool = False

    # GPIO Settings
    victron_gpio_pin: int = 17
    gpio_mock_mode: Optional[bool] = None  # Auto-detect if None

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
