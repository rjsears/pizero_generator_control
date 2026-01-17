# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/main.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""FastAPI application entry point with service lifecycle management."""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
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
    settings as settings_router,
    system,
)
from app.services.gpio_monitor import GPIOMonitor
from app.services.heartbeat import HeartbeatService
from app.services.scheduler import SchedulerService
from app.services.slave_client import SlaveClient
from app.services.state_machine import StateMachine
from app.services.webhook import WebhookService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global service instances (accessed by routers via dependency injection)
state_machine: Optional[StateMachine] = None
gpio_monitor: Optional[GPIOMonitor] = None
heartbeat_service: Optional[HeartbeatService] = None
scheduler_service: Optional[SchedulerService] = None
webhook_service: Optional[WebhookService] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    global state_machine, gpio_monitor, heartbeat_service, scheduler_service, webhook_service

    # =========================================================================
    # Startup
    # =========================================================================
    logger.info("=" * 60)
    logger.info("Starting GenMaster services...")
    logger.info(f"  Environment: {settings.app_env}")
    logger.info(f"  Debug mode: {settings.app_debug}")
    logger.info(f"  GPIO mock mode: {settings.is_mock_gpio}")
    logger.info("=" * 60)

    try:
        # Initialize webhook service first (used by state machine)
        webhook_service = WebhookService()
        logger.info("Webhook service initialized")

        # Initialize state machine
        state_machine = StateMachine()
        state_machine.set_webhook_service(webhook_service)
        await state_machine.initialize()
        logger.info("State machine initialized")

        # Initialize GPIO monitoring
        gpio_monitor = GPIOMonitor(state_machine)
        gpio_monitor.start()
        logger.info(
            f"GPIO monitor started (mock mode: {gpio_monitor.mock_mode})"
        )

        # Initialize heartbeat service
        heartbeat_service = HeartbeatService(state_machine)
        await heartbeat_service.start()
        logger.info("Heartbeat service started")

        # Initialize scheduler service
        scheduler_service = SchedulerService(state_machine)
        scheduler_service.start()
        logger.info("Scheduler service started")

        # Attempt to reconcile state with GenSlave
        logger.info("Attempting state reconciliation with GenSlave...")
        slave_client = SlaveClient()
        try:
            reconcile_result = await state_machine.reconcile_with_slave(slave_client)
            if reconcile_result["success"]:
                logger.info(f"Reconciliation: {reconcile_result['message']}")
            else:
                logger.warning(
                    f"Reconciliation incomplete: {reconcile_result['message']} "
                    "(GenSlave may not be running yet)"
                )
        except Exception as e:
            logger.warning(f"Reconciliation failed: {e} (GenSlave may not be running yet)")
        finally:
            await slave_client.close()

        # Log startup complete
        await state_machine.log_event(
            "SYSTEM_BOOT",
            {
                "version": "1.0.0",
                "environment": settings.app_env,
                "mock_gpio": gpio_monitor.mock_mode,
            },
        )

        logger.info("=" * 60)
        logger.info("GenMaster startup complete!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to start services: {e}")
        raise

    yield

    # =========================================================================
    # Shutdown
    # =========================================================================
    logger.info("=" * 60)
    logger.info("Shutting down GenMaster services...")
    logger.info("=" * 60)

    try:
        # Stop scheduler first (no new runs)
        if scheduler_service:
            scheduler_service.stop()
            logger.info("Scheduler service stopped")

        # Stop heartbeat service
        if heartbeat_service:
            await heartbeat_service.stop()
            logger.info("Heartbeat service stopped")

        # Stop GPIO monitor
        if gpio_monitor:
            gpio_monitor.stop()
            logger.info("GPIO monitor stopped")

        # Log shutdown event
        if state_machine:
            await state_machine.log_event("SYSTEM_SHUTDOWN")

        # Close webhook service
        if webhook_service:
            await webhook_service.close()
            logger.info("Webhook service closed")

        logger.info("GenMaster shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="GenMaster API",
    description="Generator Control System - Master Controller",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware - allow all origins for development
# In production, restrict to specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(generator.router, prefix="/api/generator", tags=["Generator"])
app.include_router(system.router, prefix="/api/system", tags=["System"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(config.router, prefix="/api/config", tags=["Config"])
app.include_router(override.router, prefix="/api/override", tags=["Override"])
app.include_router(backup.router, prefix="/api/backup", tags=["Backup"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(containers.router, prefix="/api/containers", tags=["Containers"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(dev.router, prefix="/api/dev", tags=["Development"])


# Root status endpoint
@app.get("/api/status")
async def get_status() -> dict:
    """Get complete system status."""
    if state_machine:
        from app.utils.system_info import get_system_health

        system_health = await get_system_health()
        return (await state_machine.get_full_status(system_health)).model_dump()
    return {
        "status": "initializing",
        "timestamp": int(time.time()),
    }


# Mount static files for frontend (if directory exists)
try:
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
except Exception:
    logger.warning("Static files directory not found, frontend not served")


# Health check that doesn't require services
@app.get("/health")
async def root_health() -> dict:
    """Simple health check at root level."""
    return {"status": "ok", "timestamp": int(time.time())}
