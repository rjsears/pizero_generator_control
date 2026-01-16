# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/__init__.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Pydantic schemas package - exports all request/response schemas."""

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.schemas.backup import BackupInfo, BackupListResponse, BackupResponse
from app.schemas.config import ConfigResponse, ConfigUpdateRequest
from app.schemas.generator import (
    GeneratorRunHistory,
    GeneratorStartRequest,
    GeneratorStartResponse,
    GeneratorStats,
    GeneratorStatus,
    GeneratorStopRequest,
    GeneratorStopResponse,
)
from app.schemas.health import (
    HealthCheck,
    HeartbeatTestResponse,
    SlaveHealth,
    WebhookTestResponse,
)
from app.schemas.override import (
    OverrideDisableResponse,
    OverrideEnableRequest,
    OverrideStatus,
)
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
)
from app.schemas.system import (
    ArmRequest,
    ArmResponse,
    AutomationArmStatus,
    CombinedSystemHealth,
    FullSystemStatus,
    SystemHealth,
    VictronStatus,
)
from app.schemas.webhook import WebhookConfig, WebhookEvent, WebhookPayload

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "TokenResponse",
    "UserCreate",
    "UserResponse",
    "ChangePasswordRequest",
    # Backup
    "BackupResponse",
    "BackupListResponse",
    "BackupInfo",
    # Config
    "ConfigResponse",
    "ConfigUpdateRequest",
    # Generator
    "GeneratorStatus",
    "GeneratorStartRequest",
    "GeneratorStartResponse",
    "GeneratorStopRequest",
    "GeneratorStopResponse",
    "GeneratorRunHistory",
    "GeneratorStats",
    # Health
    "HealthCheck",
    "SlaveHealth",
    "HeartbeatTestResponse",
    "WebhookTestResponse",
    # Override
    "OverrideStatus",
    "OverrideEnableRequest",
    "OverrideDisableResponse",
    # Schedule
    "ScheduleCreateRequest",
    "ScheduleResponse",
    "ScheduleUpdateRequest",
    # System
    "SystemHealth",
    "CombinedSystemHealth",
    "VictronStatus",
    "FullSystemStatus",
    "AutomationArmStatus",
    "ArmRequest",
    "ArmResponse",
    # Webhook
    "WebhookPayload",
    "WebhookEvent",
    "WebhookConfig",
]
