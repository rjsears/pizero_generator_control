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
    FuelResetResponse,
    FuelUsageResponse,
    GeneratorHistoryResponse,
    GeneratorRunHistory,
    GeneratorStartRequest,
    GeneratorStartResponse,
    GeneratorStats,
    GeneratorStatus,
    GeneratorStopRequest,
    GeneratorStopResponse,
    LockoutClearRequest,
    LockoutClearResponse,
    RuntimeLimitsStatus,
)
from app.schemas.health import (
    HealthCheck,
    HeartbeatTestResponse,
    SlaveHealth,
    WebhookTestResponse,
)
from app.schemas.notifications import (
    ChannelType,
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationEvent,
    NotificationGroupCreate,
    NotificationGroupResponse,
    NotificationGroupUpdate,
    NotificationHistoryResponse,
    SendNotificationRequest,
    SendNotificationResponse,
    TestChannelRequest,
    TestChannelResponse,
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
from app.schemas.generator_info import (
    FuelTypeEnum,
    GeneratorInfoResponse,
    GeneratorInfoUpdate,
    LoadExpectedEnum,
)
from app.schemas.exercise_schedule import (
    ExerciseRunNowResponse,
    ExerciseScheduleResponse,
    ExerciseScheduleUpdate,
)

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
    "GeneratorHistoryResponse",
    "GeneratorRunHistory",
    "GeneratorStats",
    "RuntimeLimitsStatus",
    "LockoutClearRequest",
    "LockoutClearResponse",
    "FuelUsageResponse",
    "FuelResetResponse",
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
    # Notifications
    "ChannelType",
    "NotificationEvent",
    "NotificationChannelCreate",
    "NotificationChannelUpdate",
    "NotificationChannelResponse",
    "NotificationGroupCreate",
    "NotificationGroupUpdate",
    "NotificationGroupResponse",
    "NotificationHistoryResponse",
    "SendNotificationRequest",
    "SendNotificationResponse",
    "TestChannelRequest",
    "TestChannelResponse",
    # Generator Info
    "FuelTypeEnum",
    "LoadExpectedEnum",
    "GeneratorInfoResponse",
    "GeneratorInfoUpdate",
    # Exercise Schedule
    "ExerciseScheduleResponse",
    "ExerciseScheduleUpdate",
    "ExerciseRunNowResponse",
]
