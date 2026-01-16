# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/config.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""GenSlave configuration management."""

import os
from pathlib import Path


class Settings:
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "GenSlave"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "production")
    DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"

    # API Security
    API_SECRET: str = os.getenv("GENSLAVE_API_SECRET", "")

    # Heartbeat/Failsafe
    FAILSAFE_TIMEOUT_SECONDS: int = int(os.getenv("FAILSAFE_TIMEOUT_SECONDS", "30"))
    HEARTBEAT_GRACE_PERIOD: int = int(os.getenv("HEARTBEAT_GRACE_PERIOD", "5"))

    # Hardware
    MOCK_HAT_MODE: bool = os.getenv("MOCK_HAT_MODE", "false").lower() == "true"
    RELAY_GPIO_PIN: int = int(os.getenv("RELAY_GPIO_PIN", "16"))

    # Database
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", "/opt/genslave/data/genslave.db"
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_PATH: str = os.getenv("LOG_PATH", "/opt/genslave/logs")

    # Webhook (backup notification if GenMaster is down)
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8001"))

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure required directories exist."""
        Path(cls.LOG_PATH).mkdir(parents=True, exist_ok=True)
        Path(cls.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
