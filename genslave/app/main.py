# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/main.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""GenSlave FastAPI Application - Generator relay control for Pi Zero 2W."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import verify_api_key
from app.config import settings
from app.routers import relay_router, health_router, system_router
from app.services.database import db_service
from app.services.relay import relay_service
from app.services.failsafe import failsafe_monitor
from app.services.display import display_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"GenSlave v{settings.APP_VERSION} starting...")

    # Ensure directories exist
    settings.ensure_directories()

    # Initialize database (loads API secret from env on first run)
    db_service.initialize()

    # Connect failsafe monitor to relay service
    failsafe_monitor.set_relay_service(relay_service)

    # Connect display to services
    display_service.set_services(failsafe_monitor, relay_service)

    # Start failsafe monitor
    await failsafe_monitor.start()

    # Start display service
    await display_service.start()

    # Check if API secret is configured
    api_secret = db_service.get_api_secret()
    api_status = "configured" if api_secret else "NOT CONFIGURED (API unprotected!)"

    logger.info(
        f"GenSlave ready - "
        f"HAT: {'real' if not relay_service.is_mock_mode else 'mock'}, "
        f"Failsafe timeout: {settings.FAILSAFE_TIMEOUT_SECONDS}s, "
        f"API Auth: {api_status}"
    )

    yield

    # Shutdown
    logger.info("GenSlave shutting down...")

    # Stop display service
    await display_service.stop()

    # Stop failsafe monitor
    await failsafe_monitor.stop()

    # Ensure relay is OFF on shutdown for safety
    relay_service.relay_off(force=True)

    logger.info("GenSlave stopped")


# Create FastAPI application
app = FastAPI(
    title="GenSlave API",
    description="Generator relay control API for Raspberry Pi Zero 2W with Automation Hat Mini",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to GenMaster IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with API key authentication
# All API endpoints require X-API-Key header (if API_SECRET is configured)
api_key_dependency = [Depends(verify_api_key)]
app.include_router(health_router, dependencies=api_key_dependency)
app.include_router(relay_router, dependencies=api_key_dependency)
app.include_router(system_router, dependencies=api_key_dependency)


@app.get("/")
async def root():
    """Root endpoint - basic info."""
    return {
        "service": "GenSlave",
        "version": settings.APP_VERSION,
        "status": "running",
        "armed": relay_service.is_armed,
        "relay_state": relay_service.get_state(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
