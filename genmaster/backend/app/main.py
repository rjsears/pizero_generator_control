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

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    auth,
    backup,
    config,
    containers,
    dev,
    exercise,
    generator,
    generator_info,
    health,
    metrics,
    notifications,
    override,
    schedule,
    settings as settings_router,
    system,
    system_notifications,
    terminal,
)
from app.services.exercise_scheduler import ExerciseSchedulerService
from app.services.gpio_monitor import GPIOMonitor
from app.services.heartbeat import HeartbeatService
from app.services.metrics_service import get_metrics_service
from app.services.scheduler import SchedulerService
from app.services.slave_client import SlaveClient
from app.services.redis_cache import get_redis_cache
from app.services.slave_status_service import get_slave_status_service
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
exercise_scheduler_service: Optional[ExerciseSchedulerService] = None
webhook_service: Optional[WebhookService] = None


async def sync_env_to_database() -> None:
    """Sync critical settings from environment variables to database config.

    This ensures that values set in .env (via setup.sh) are reflected in the
    database config table, which is what the heartbeat and health services use.

    Only updates values that are explicitly set in the environment (not defaults).
    """
    from app.database import AsyncSessionLocal
    from app.models import Config

    async with AsyncSessionLocal() as db:
        config = await Config.get_instance(db)

        updates = []

        # Sync slave_api_url if set in environment (not the default)
        if settings.slave_api_url and settings.slave_api_url != "http://genslave:8001":
            if config.slave_api_url != settings.slave_api_url:
                config.slave_api_url = settings.slave_api_url
                updates.append(f"slave_api_url={settings.slave_api_url}")

        # Sync slave_api_secret if set in environment (not the default)
        if settings.slave_api_secret and settings.slave_api_secret != "change-me":
            if config.slave_api_secret != settings.slave_api_secret:
                config.slave_api_secret = settings.slave_api_secret
                updates.append("slave_api_secret=***")

        # Sync genslave_ip if set in environment
        if settings.genslave_ip:
            if config.genslave_ip != settings.genslave_ip:
                config.genslave_ip = settings.genslave_ip
                updates.append(f"genslave_ip={settings.genslave_ip}")

        if updates:
            await db.commit()
            logger.info(f"Synced env vars to database config: {', '.join(updates)}")
        else:
            logger.debug("Database config already in sync with environment")


async def sync_generator_info_to_database() -> None:
    """Sync generator info from environment variables to database.

    This allows generator info to be pre-configured via .env file.
    Only updates values that are explicitly set in the environment.
    """
    import os
    from app.database import AsyncSessionLocal
    from app.models import GeneratorInfo

    async with AsyncSessionLocal() as db:
        info = await GeneratorInfo.get_instance(db)
        updates = []

        # Check for environment variables and sync to database
        if os.getenv("GEN_INFO_MANUFACTURER"):
            val = os.getenv("GEN_INFO_MANUFACTURER")
            if info.manufacturer != val:
                info.manufacturer = val
                updates.append(f"manufacturer={val}")

        if os.getenv("GEN_INFO_MODEL_NUMBER"):
            val = os.getenv("GEN_INFO_MODEL_NUMBER")
            if info.model_number != val:
                info.model_number = val
                updates.append(f"model_number={val}")

        if os.getenv("GEN_INFO_SERIAL_NUMBER"):
            val = os.getenv("GEN_INFO_SERIAL_NUMBER")
            if info.serial_number != val:
                info.serial_number = val
                updates.append(f"serial_number={val}")

        if os.getenv("GEN_INFO_FUEL_TYPE"):
            val = os.getenv("GEN_INFO_FUEL_TYPE")
            if info.fuel_type != val:
                info.fuel_type = val
                updates.append(f"fuel_type={val}")

        if os.getenv("GEN_INFO_LOAD_EXPECTED"):
            val = int(os.getenv("GEN_INFO_LOAD_EXPECTED"))
            if info.load_expected != val:
                info.load_expected = val
                updates.append(f"load_expected={val}")

        if os.getenv("GEN_INFO_FUEL_CONSUMPTION_50"):
            val = float(os.getenv("GEN_INFO_FUEL_CONSUMPTION_50"))
            if info.fuel_consumption_50 != val:
                info.fuel_consumption_50 = val
                updates.append(f"fuel_consumption_50={val}")

        if os.getenv("GEN_INFO_FUEL_CONSUMPTION_100"):
            val = float(os.getenv("GEN_INFO_FUEL_CONSUMPTION_100"))
            if info.fuel_consumption_100 != val:
                info.fuel_consumption_100 = val
                updates.append(f"fuel_consumption_100={val}")

        if updates:
            await db.commit()
            logger.info(f"Synced generator info from env vars: {', '.join(updates)}")
        else:
            logger.debug("Generator info already in sync with environment")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    global state_machine, gpio_monitor, heartbeat_service, scheduler_service, exercise_scheduler_service, webhook_service

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
        # Sync environment variables to database config first
        # This ensures .env values (from setup.sh) are reflected in the database
        await sync_env_to_database()

        # Initialize Redis cache (before services that use it)
        redis_cache = get_redis_cache()
        await redis_cache.connect()
        logger.info(f"Redis cache initialized (connected: {redis_cache.is_connected})")

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

        # Initialize slave status service (background polling for UI performance)
        slave_status_service = get_slave_status_service()
        await slave_status_service.start()
        logger.info("Slave status service started")

        # Initialize scheduler service
        scheduler_service = SchedulerService(state_machine)
        scheduler_service.start()
        logger.info("Scheduler service started")

        # Initialize exercise scheduler service
        exercise_scheduler_service = ExerciseSchedulerService(state_machine, scheduler_service)
        await exercise_scheduler_service.start()
        logger.info("Exercise scheduler service started")

        # Sync generator info from environment variables
        await sync_generator_info_to_database()

        # Initialize metrics collection service
        metrics_service = get_metrics_service()
        await metrics_service.start()
        logger.info("Metrics service started")

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
        # Stop metrics service
        metrics_svc = get_metrics_service()
        await metrics_svc.stop()
        logger.info("Metrics service stopped")

        # Stop exercise scheduler first
        if exercise_scheduler_service:
            await exercise_scheduler_service.stop()
            logger.info("Exercise scheduler service stopped")

        # Stop scheduler (no new runs)
        if scheduler_service:
            scheduler_service.stop()
            logger.info("Scheduler service stopped")

        # Stop slave status service
        slave_status_svc = get_slave_status_service()
        await slave_status_svc.stop()
        logger.info("Slave status service stopped")

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

        # Disconnect Redis cache
        redis_cache = get_redis_cache()
        await redis_cache.disconnect()
        logger.info("Redis cache disconnected")

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
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])
app.include_router(dev.router, prefix="/api/dev", tags=["Development"])
app.include_router(terminal.router, prefix="/api/terminal", tags=["Terminal"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["Metrics"])
app.include_router(generator_info.router, prefix="/api/generator-info", tags=["Generator Info"])
app.include_router(exercise.router, prefix="/api/exercise", tags=["Exercise"])
app.include_router(system_notifications.router, prefix="/api/system-notifications", tags=["System Notifications"])


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


# Static files directory
STATIC_DIR = Path("static")

# Mount static assets (js, css, images, etc.)
if STATIC_DIR.exists():
    # Mount assets subdirectory for Vite build output
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Serve index.html for SPA routes (catch-all)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA routing)."""
        # Check if it's a static file request
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # For all other routes, serve index.html (SPA)
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        # Fallback if no frontend built
        return {"error": "Frontend not built", "path": full_path}
else:
    logger.warning("Static files directory not found, frontend not served")


# Health check that doesn't require services
@app.get("/health")
async def root_health() -> dict:
    """Simple health check at root level."""
    return {"status": "ok", "timestamp": int(time.time())}
