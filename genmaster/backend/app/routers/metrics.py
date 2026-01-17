# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/metrics.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Metrics API endpoints for dashboard charts and system monitoring."""

from typing import Any

from fastapi import APIRouter, Query

from app.services.metrics_service import (
    get_container_summary,
    get_core_services_status,
    get_docker_storage,
    get_metrics_service,
    get_recent_logs_analysis,
)

router = APIRouter()


@router.get("/history")
async def get_metrics_history(
    minutes: int = Query(default=60, ge=1, le=60, description="Minutes of history (1-60)")
) -> dict[str, Any]:
    """
    Get system metrics history for dashboard charts.

    Returns CPU, memory, and network I/O data points collected over the specified
    time period. Data is collected every minute, so maximum 60 data points are available.

    Use this for rendering line charts showing system performance over time.
    """
    service = get_metrics_service()
    return service.get_history(minutes)


@router.get("/network")
async def get_network_metrics() -> dict[str, Any]:
    """
    Get current network I/O metrics.

    Returns current send/receive rates in bytes per second, along with total
    bytes transferred since system boot.
    """
    service = get_metrics_service()
    return service.get_current_network_io()


@router.get("/containers/summary")
async def get_containers_summary() -> dict[str, Any]:
    """
    Get summary of container statuses.

    Returns counts of running, stopped, and unhealthy containers.
    Useful for dashboard status tiles.
    """
    return get_container_summary()


@router.get("/docker/storage")
async def get_docker_storage_usage() -> dict[str, Any]:
    """
    Get Docker storage usage breakdown.

    Returns storage used by images, volumes, containers, and build cache.
    """
    return get_docker_storage()


@router.get("/services")
async def get_services_status() -> dict[str, Any]:
    """
    Get status of core services.

    Checks status of genmaster_api, nginx, postgres, and redis containers.
    Returns running state and health status for each.
    """
    return get_core_services_status()


@router.get("/logs/analysis")
async def get_logs_analysis(
    lines: int = Query(default=100, ge=10, le=500, description="Lines to analyze per container")
) -> dict[str, Any]:
    """
    Analyze recent container logs for errors and warnings.

    Scans the most recent log lines from each running container and counts
    occurrences of error and warning messages.
    """
    return get_recent_logs_analysis(lines)


@router.get("/dashboard")
async def get_dashboard_metrics() -> dict[str, Any]:
    """
    Get all metrics needed for the dashboard in a single call.

    Combines metrics history, network I/O, container summary, and services status
    into a single response to reduce API calls from the frontend.
    """
    service = get_metrics_service()

    return {
        "history": service.get_history(60),
        "network": service.get_current_network_io(),
        "containers": get_container_summary(),
        "services": get_core_services_status(),
    }
