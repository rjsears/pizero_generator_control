# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/models/__init__.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""SQLAlchemy models package - exports all models."""

from app.models.base import Base
from app.models.config_model import Config
from app.models.event_log import EventLog
from app.models.generator_runs import GeneratorRun
from app.models.notifications import (
    NotificationChannel,
    NotificationGroup,
    NotificationHistory,
)
from app.models.scheduled_runs import ScheduledRun
from app.models.session import Session
from app.models.settings import Settings
from app.models.system_state import SystemState
from app.models.user import User

__all__ = [
    "Base",
    "Config",
    "EventLog",
    "GeneratorRun",
    "NotificationChannel",
    "NotificationGroup",
    "NotificationHistory",
    "ScheduledRun",
    "Session",
    "Settings",
    "SystemState",
    "User",
]
