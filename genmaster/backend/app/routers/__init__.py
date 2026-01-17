# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/__init__.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""API routers package."""

from app.routers import (
    auth,
    backup,
    config,
    containers,
    dev,
    generator,
    health,
    override,
    schedule,
    settings,
    system,
    terminal,
)

__all__ = [
    "auth",
    "backup",
    "config",
    "containers",
    "dev",
    "generator",
    "health",
    "override",
    "schedule",
    "settings",
    "system",
    "terminal",
]
