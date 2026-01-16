# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/containers.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Docker container management API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
logger = logging.getLogger(__name__)


def get_docker_client():
    """Get Docker client, handling import errors."""
    try:
        import docker

        return docker.from_env()
    except Exception as e:
        logger.warning(f"Docker not available: {e}")
        return None


@router.get("")
@router.get("/")
async def list_containers(
    all: bool = Query(False, description="Include stopped containers"),
) -> List[dict]:
    """
    List Docker containers.

    By default only shows running containers.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        containers = client.containers.list(all=all)
        return [
            {
                "id": c.short_id,
                "name": c.name,
                "image": c.image.tags[0] if c.image.tags else c.image.short_id,
                "status": c.status,
                "created": c.attrs.get("Created"),
                "ports": c.ports,
            }
            for c in containers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.get("/{name}")
async def get_container(name: str) -> dict:
    """
    Get details for a specific container.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)
        return {
            "id": container.short_id,
            "name": container.name,
            "image": container.image.tags[0] if container.image.tags else container.image.short_id,
            "status": container.status,
            "created": container.attrs.get("Created"),
            "ports": container.ports,
            "labels": container.labels,
            "mounts": [
                {"source": m.get("Source"), "destination": m.get("Destination")}
                for m in container.attrs.get("Mounts", [])
            ],
        }
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.get("/stats")
async def get_container_stats() -> List[dict]:
    """
    Get resource usage stats for all running containers.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        containers = client.containers.list()
        stats = []

        for container in containers:
            try:
                stat = container.stats(stream=False)
                # Calculate CPU percentage
                cpu_delta = (
                    stat["cpu_stats"]["cpu_usage"]["total_usage"]
                    - stat["precpu_stats"]["cpu_usage"]["total_usage"]
                )
                system_delta = (
                    stat["cpu_stats"]["system_cpu_usage"]
                    - stat["precpu_stats"]["system_cpu_usage"]
                )
                cpu_percent = 0.0
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100.0

                # Calculate memory
                mem_usage = stat["memory_stats"].get("usage", 0)
                mem_limit = stat["memory_stats"].get("limit", 1)
                mem_percent = (mem_usage / mem_limit) * 100

                stats.append({
                    "name": container.name,
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_usage_mb": round(mem_usage / (1024 * 1024), 2),
                    "memory_limit_mb": round(mem_limit / (1024 * 1024), 2),
                    "memory_percent": round(mem_percent, 2),
                })
            except Exception:
                continue

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.post("/{name}/start")
async def start_container(name: str) -> dict:
    """
    Start a stopped container.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)
        container.start()
        return {"success": True, "message": f"Container {name} started"}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.post("/{name}/stop")
async def stop_container(name: str) -> dict:
    """
    Stop a running container.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)
        container.stop()
        return {"success": True, "message": f"Container {name} stopped"}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.post("/{name}/restart")
async def restart_container(name: str) -> dict:
    """
    Restart a container.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)
        container.restart()
        return {"success": True, "message": f"Container {name} restarted"}
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.get("/{name}/logs")
async def get_container_logs(
    name: str,
    tail: int = Query(100, ge=1, le=10000),
    since: Optional[str] = Query(None, description="Show logs since timestamp"),
) -> dict:
    """
    Get container logs.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)
        logs = container.logs(
            tail=tail,
            since=since,
            timestamps=True,
        )
        return {
            "container": name,
            "logs": logs.decode("utf-8", errors="replace"),
        }
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()
