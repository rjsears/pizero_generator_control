# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/__init__.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Services package - business logic and background services."""

from app.services.backup import BackupService
from app.services.gpio_monitor import GPIOMonitor
from app.services.scheduler import SchedulerService
from app.services.slave_client import SlaveClient
from app.services.slave_status_service import SlaveStatusService, get_slave_status_service
from app.services.state_machine import StateMachine
from app.services.webhook import WebhookService

__all__ = [
    "BackupService",
    "GPIOMonitor",
    "SchedulerService",
    "SlaveClient",
    "SlaveStatusService",
    "get_slave_status_service",
    "StateMachine",
    "WebhookService",
]
