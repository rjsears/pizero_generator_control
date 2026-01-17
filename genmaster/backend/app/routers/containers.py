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


@router.delete("/{name}")
async def delete_container(
    name: str,
    force: bool = Query(False, description="Force removal of running container"),
) -> dict:
    """
    Delete a container.

    Use force=true to remove a running container.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)

        # Check if container is running and force is not set
        if container.status == "running" and not force:
            raise HTTPException(
                status_code=400,
                detail="Container is running. Use force=true to remove it.",
            )

        container.remove(force=force)
        return {"success": True, "message": f"Container {name} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.post("/{name}/recreate")
async def recreate_container(name: str) -> dict:
    """
    Recreate a container with the same configuration.

    Pulls the latest image, stops and removes the old container,
    then creates a new one with the same configuration.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        container = client.containers.get(name)

        # Get container configuration
        config = container.attrs
        image = config["Config"]["Image"]
        labels = config["Config"].get("Labels", {})
        env = config["Config"].get("Env", [])
        volumes = config.get("HostConfig", {}).get("Binds", [])
        ports = config.get("HostConfig", {}).get("PortBindings", {})
        network_mode = config.get("HostConfig", {}).get("NetworkMode", "bridge")
        restart_policy = config.get("HostConfig", {}).get("RestartPolicy", {})

        # Pull latest image
        logger.info(f"Pulling latest image for {image}")
        try:
            client.images.pull(image)
        except Exception as e:
            logger.warning(f"Failed to pull image {image}: {e}")

        # Stop and remove old container
        container.stop()
        container.remove()

        # Create new container
        new_container = client.containers.run(
            image,
            name=name,
            labels=labels,
            environment=env,
            volumes=volumes,
            ports=ports if ports else None,
            network_mode=network_mode,
            restart_policy=restart_policy,
            detach=True,
        )

        return {
            "success": True,
            "message": f"Container {name} recreated",
            "new_id": new_container.short_id,
        }
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Container not found")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()


@router.get("/health")
async def get_containers_health() -> dict:
    """
    Get overall container health status.

    Returns count of running, stopped, and unhealthy containers.
    """
    client = get_docker_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Docker is not available"
        )

    try:
        containers = client.containers.list(all=True)

        running = 0
        stopped = 0
        unhealthy = 0

        for c in containers:
            if c.status == "running":
                running += 1
                # Check health status if available
                health = c.attrs.get("State", {}).get("Health", {})
                if health.get("Status") == "unhealthy":
                    unhealthy += 1
            else:
                stopped += 1

        overall = "healthy"
        if unhealthy > 0:
            overall = "unhealthy"
        elif stopped > running:
            overall = "warning"

        return {
            "status": overall,
            "total": len(containers),
            "running": running,
            "stopped": stopped,
            "unhealthy": unhealthy,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.close()
