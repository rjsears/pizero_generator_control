# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/metrics_service.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 17th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Metrics collection and history service."""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single point of metric data."""
    timestamp: int
    cpu_percent: float
    memory_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    network_rate_sent: float = 0.0  # bytes/sec
    network_rate_recv: float = 0.0  # bytes/sec


@dataclass
class MetricsHistory:
    """Container for metrics history with circular buffer."""
    points: deque = field(default_factory=lambda: deque(maxlen=60))
    last_network_bytes_sent: int = 0
    last_network_bytes_recv: int = 0
    last_collection_time: float = 0


class MetricsService:
    """Service for collecting and managing system metrics history."""

    def __init__(self, collection_interval: int = 60):
        """
        Initialize metrics service.

        Args:
            collection_interval: Seconds between metric collections (default 60 = 1 minute)
        """
        self.collection_interval = collection_interval
        self.history = MetricsHistory()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the metrics collection background task."""
        if self._running:
            return

        self._running = True
        # Collect initial metrics
        await self._collect_metrics()
        # Start background task
        self._task = asyncio.create_task(self._collection_loop())
        logger.info("Metrics service started")

    async def stop(self):
        """Stop the metrics collection background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics service stopped")

    async def _collection_loop(self):
        """Background loop that collects metrics at regular intervals."""
        while self._running:
            try:
                await asyncio.sleep(self.collection_interval)
                await self._collect_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _collect_metrics(self):
        """Collect current system metrics and add to history."""
        try:
            current_time = time.time()

            # Get CPU (use interval=None for non-blocking)
            cpu_percent = psutil.cpu_percent(interval=None)

            # Get memory
            mem = psutil.virtual_memory()
            memory_percent = mem.percent

            # Get network I/O
            net_io = psutil.net_io_counters()
            bytes_sent = net_io.bytes_sent
            bytes_recv = net_io.bytes_recv

            # Calculate rates if we have previous data
            rate_sent = 0.0
            rate_recv = 0.0

            if self.history.last_collection_time > 0:
                time_delta = current_time - self.history.last_collection_time
                if time_delta > 0:
                    bytes_sent_delta = bytes_sent - self.history.last_network_bytes_sent
                    bytes_recv_delta = bytes_recv - self.history.last_network_bytes_recv
                    rate_sent = bytes_sent_delta / time_delta
                    rate_recv = bytes_recv_delta / time_delta

            # Create metric point
            point = MetricPoint(
                timestamp=int(current_time),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                network_bytes_sent=bytes_sent,
                network_bytes_recv=bytes_recv,
                network_rate_sent=rate_sent,
                network_rate_recv=rate_recv,
            )

            # Add to history
            self.history.points.append(point)

            # Update last values
            self.history.last_network_bytes_sent = bytes_sent
            self.history.last_network_bytes_recv = bytes_recv
            self.history.last_collection_time = current_time

            logger.debug(f"Collected metrics: CPU={cpu_percent}%, MEM={memory_percent}%")

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")

    def get_history(self, minutes: int = 60) -> dict[str, Any]:
        """
        Get metrics history for the specified time period.

        Args:
            minutes: Number of minutes of history to return (max 60)

        Returns:
            Dict with timestamps and metric arrays
        """
        points = list(self.history.points)

        # Filter to requested time range
        if minutes < 60:
            cutoff = time.time() - (minutes * 60)
            points = [p for p in points if p.timestamp >= cutoff]

        return {
            "timestamps": [p.timestamp for p in points],
            "cpu_percent": [p.cpu_percent for p in points],
            "memory_percent": [p.memory_percent for p in points],
            "network_bytes_sent": [p.network_bytes_sent for p in points],
            "network_bytes_recv": [p.network_bytes_recv for p in points],
            "network_rate_sent": [p.network_rate_sent for p in points],
            "network_rate_recv": [p.network_rate_recv for p in points],
            "points_count": len(points),
            "collection_interval_seconds": self.collection_interval,
        }

    def get_current_network_io(self) -> dict[str, Any]:
        """
        Get current network I/O rates.

        Returns:
            Dict with current send/receive rates
        """
        if not self.history.points:
            return {
                "bytes_sent_rate": 0,
                "bytes_recv_rate": 0,
                "bytes_sent_total": 0,
                "bytes_recv_total": 0,
            }

        latest = self.history.points[-1]
        return {
            "bytes_sent_rate": latest.network_rate_sent,
            "bytes_recv_rate": latest.network_rate_recv,
            "bytes_sent_total": latest.network_bytes_sent,
            "bytes_recv_total": latest.network_bytes_recv,
            "timestamp": latest.timestamp,
        }


def get_container_summary() -> dict[str, Any]:
    """
    Get summary of Docker container statuses.

    Returns:
        Dict with running, stopped, unhealthy counts
    """
    try:
        import docker
        client = docker.from_env()

        containers = client.containers.list(all=True)

        running = 0
        stopped = 0
        unhealthy = 0

        for container in containers:
            status = container.status
            if status == "running":
                # Check health status
                health = container.attrs.get("State", {}).get("Health", {})
                health_status = health.get("Status", "none")
                if health_status == "unhealthy":
                    unhealthy += 1
                else:
                    running += 1
            else:
                stopped += 1

        return {
            "total": len(containers),
            "running": running,
            "stopped": stopped,
            "unhealthy": unhealthy,
        }

    except ImportError:
        return {"error": "Docker SDK not installed"}
    except Exception as e:
        logger.warning(f"Failed to get container summary: {e}")
        return {"error": str(e)}


def get_docker_storage() -> dict[str, Any]:
    """
    Get Docker storage usage information.

    Returns:
        Dict with images, volumes, and total storage usage
    """
    try:
        import docker
        client = docker.from_env()

        # Get disk usage info
        df_data = client.df()

        images_size = sum(img.get("Size", 0) for img in df_data.get("Images", []))
        volumes_size = sum(vol.get("UsageData", {}).get("Size", 0)
                         for vol in df_data.get("Volumes", [])
                         if vol.get("UsageData"))
        containers_size = sum(c.get("SizeRw", 0) for c in df_data.get("Containers", []))
        build_cache_size = sum(bc.get("Size", 0) for bc in df_data.get("BuildCache", []))

        return {
            "images": {
                "count": len(df_data.get("Images", [])),
                "size_bytes": images_size,
                "size_formatted": format_bytes(images_size),
            },
            "volumes": {
                "count": len(df_data.get("Volumes", [])),
                "size_bytes": volumes_size,
                "size_formatted": format_bytes(volumes_size),
            },
            "containers": {
                "count": len(df_data.get("Containers", [])),
                "size_bytes": containers_size,
                "size_formatted": format_bytes(containers_size),
            },
            "build_cache": {
                "count": len(df_data.get("BuildCache", [])),
                "size_bytes": build_cache_size,
                "size_formatted": format_bytes(build_cache_size),
            },
            "total_bytes": images_size + volumes_size + containers_size + build_cache_size,
            "total_formatted": format_bytes(images_size + volumes_size + containers_size + build_cache_size),
        }

    except ImportError:
        return {"error": "Docker SDK not installed"}
    except Exception as e:
        logger.warning(f"Failed to get Docker storage: {e}")
        return {"error": str(e)}


def get_core_services_status() -> dict[str, Any]:
    """
    Get status of core services (genmaster containers, nginx, postgres).

    Returns:
        Dict with service statuses
    """
    try:
        import docker
        client = docker.from_env()

        # Define core services to check
        core_services = {
            "genmaster_api": ["genmaster_api", "genmaster_backend", "genmaster-api"],
            "nginx": ["genmaster_nginx", "nginx"],
            "postgres": ["genmaster_postgres", "genmaster_db", "postgres"],
            "redis": ["genmaster_redis", "redis"],
        }

        services = {}
        containers = client.containers.list(all=True)

        for service_name, possible_names in core_services.items():
            found = None
            for container in containers:
                container_name = container.name.lower()
                if any(name.lower() in container_name for name in possible_names):
                    found = container
                    break

            if found:
                health = found.attrs.get("State", {}).get("Health", {})
                health_status = health.get("Status", "none")

                services[service_name] = {
                    "name": found.name,
                    "status": found.status,
                    "health": health_status,
                    "running": found.status == "running",
                    "healthy": found.status == "running" and health_status != "unhealthy",
                }
            else:
                services[service_name] = {
                    "name": service_name,
                    "status": "not_found",
                    "health": "none",
                    "running": False,
                    "healthy": False,
                }

        # Determine overall status
        all_running = all(s["running"] for s in services.values() if s["status"] != "not_found")
        any_unhealthy = any(s["health"] == "unhealthy" for s in services.values())

        return {
            "services": services,
            "all_running": all_running,
            "any_unhealthy": any_unhealthy,
            "overall_status": "healthy" if all_running and not any_unhealthy else "degraded",
        }

    except ImportError:
        return {"error": "Docker SDK not installed"}
    except Exception as e:
        logger.warning(f"Failed to get core services status: {e}")
        return {"error": str(e)}


def get_recent_logs_analysis(tail_lines: int = 100) -> dict[str, Any]:
    """
    Analyze recent container logs for errors and warnings.

    Args:
        tail_lines: Number of recent log lines to analyze per container

    Returns:
        Dict with error/warning counts per container
    """
    try:
        import docker
        client = docker.from_env()

        containers_analysis = {}
        containers = client.containers.list()

        for container in containers:
            try:
                logs = container.logs(tail=tail_lines, timestamps=False).decode("utf-8", errors="ignore")
                lines = logs.split("\n")

                error_count = 0
                warning_count = 0

                for line in lines:
                    line_lower = line.lower()
                    if "error" in line_lower or "exception" in line_lower or "critical" in line_lower:
                        error_count += 1
                    elif "warn" in line_lower:
                        warning_count += 1

                containers_analysis[container.name] = {
                    "lines_analyzed": len(lines),
                    "errors": error_count,
                    "warnings": warning_count,
                    "status": "critical" if error_count > 10 else "warning" if error_count > 0 or warning_count > 5 else "healthy",
                }

            except Exception as e:
                containers_analysis[container.name] = {
                    "error": str(e),
                    "lines_analyzed": 0,
                    "errors": 0,
                    "warnings": 0,
                    "status": "unknown",
                }

        total_errors = sum(c.get("errors", 0) for c in containers_analysis.values())
        total_warnings = sum(c.get("warnings", 0) for c in containers_analysis.values())

        return {
            "containers": containers_analysis,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "overall_status": "critical" if total_errors > 20 else "warning" if total_errors > 0 or total_warnings > 10 else "healthy",
        }

    except ImportError:
        return {"error": "Docker SDK not installed"}
    except Exception as e:
        logger.warning(f"Failed to analyze logs: {e}")
        return {"error": str(e)}


def format_bytes(size: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


# Global metrics service instance
metrics_service: Optional[MetricsService] = None


def get_metrics_service() -> MetricsService:
    """Get or create the global metrics service instance."""
    global metrics_service
    if metrics_service is None:
        metrics_service = MetricsService()
    return metrics_service
