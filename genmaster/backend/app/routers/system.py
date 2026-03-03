# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/system.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System information API endpoints."""

import asyncio
import platform
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# Simple TTL cache for slow operations
_cache: dict[str, dict[str, Any]] = {}
CACHE_TTL_SECONDS = 30  # Cache external service status for 30 seconds


def _get_cached(key: str) -> Any | None:
    """Get cached value if not expired."""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["time"] < CACHE_TTL_SECONDS:
            return entry["data"]
    return None


def _set_cached(key: str, data: Any) -> None:
    """Set cached value with current timestamp."""
    _cache[key] = {"data": data, "time": time.time()}


# Container name for the host-tools sidecar
HOST_TOOLS_CONTAINER = "genmaster_host_tools"


def _exec_host_command(command: str, timeout: int = 10) -> tuple[bool, str]:
    """
    Execute a command in the host-tools sidecar container.

    Uses docker exec for instant execution (no container startup overhead).
    The host-tools container has network tools pre-installed and runs with
    host network access and privileged mode.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default 10)

    Returns:
        Tuple of (success, output_or_error)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        import docker
        client = docker.from_env()

        # Get the host-tools container
        try:
            container = client.containers.get(HOST_TOOLS_CONTAINER)
        except docker.errors.NotFound:
            logger.warning(f"Host-tools container '{HOST_TOOLS_CONTAINER}' not found")
            return False, f"Container '{HOST_TOOLS_CONTAINER}' not running"

        # Check if container is running
        if container.status != "running":
            logger.warning(f"Host-tools container is not running (status: {container.status})")
            return False, f"Container not running (status: {container.status})"

        # Execute command in the container
        exit_code, output = container.exec_run(
            cmd=["sh", "-c", command],
            demux=False,
        )

        output_str = output.decode("utf-8").strip() if output else ""

        if exit_code != 0:
            logger.debug(f"Host command failed (exit {exit_code}): {command[:50]}...")
            return False, output_str or f"Command failed with exit code {exit_code}"

        return True, output_str

    except ImportError:
        return False, "Docker SDK not installed"
    except Exception as e:
        logger.warning(f"Failed to exec host command: {e}")
        return False, str(e)


from app.config import settings
from app.schemas import (
    AutomationArmStatus,
    CombinedSystemHealth,
    FullSystemStatus,
    SystemHealth,
    VictronStatus,
)
from app.utils.system_info import get_system_health

router = APIRouter()


def get_state_machine():
    """Get state machine from app state."""
    from app.main import state_machine

    return state_machine


def get_gpio_monitor():
    """Get GPIO monitor from app state."""
    from app.main import gpio_monitor

    return gpio_monitor


@router.get("", response_model=SystemHealth)
@router.get("/", response_model=SystemHealth)
async def get_system_info() -> SystemHealth:
    """
    Get GenMaster system health metrics.

    Returns CPU, RAM, disk, temperature, and uptime.
    """
    return await get_system_health()


@router.get("/combined", response_model=CombinedSystemHealth)
async def get_combined_system_info(
    state_machine=Depends(get_state_machine),
) -> CombinedSystemHealth:
    """
    Get combined health for GenMaster and GenSlave.
    """
    # Get GenMaster health
    master_health = await get_system_health()

    # Try to get GenSlave health
    slave_health = None
    try:
        from app.services.slave_status_service import create_slave_client

        client = await create_slave_client()
        response = await client.get_system_health()
        await client.close()

        if response.success and response.data:
            # Convert slave response to SystemHealth
            data = response.data
            slave_health = SystemHealth(
                hostname=data.get("hostname", "genslave"),
                platform=data.get("platform", "linux"),
                cpu_percent=data.get("cpu_percent", 0),
                ram_total_mb=data.get("ram_total_mb", 0),
                ram_used_mb=data.get("ram_used_mb", 0),
                ram_percent=data.get("ram_percent", 0),
                disk_total_gb=data.get("disk_total_gb", 0),
                disk_used_gb=data.get("disk_used_gb", 0),
                disk_percent=data.get("disk_percent", 0),
                temperature_celsius=data.get("temperature_celsius"),
                uptime_seconds=data.get("uptime_seconds", 0),
                status=data.get("status", "unknown"),
                warnings=data.get("warnings", []),
            )
    except Exception:
        pass

    # Determine overall status
    if slave_health is None:
        overall = "warning" if master_health.status == "healthy" else master_health.status
    elif master_health.status == "critical" or slave_health.status == "critical":
        overall = "critical"
    elif master_health.status == "warning" or slave_health.status == "warning":
        overall = "warning"
    else:
        overall = "healthy"

    return CombinedSystemHealth(
        genmaster=master_health,
        genslave=slave_health,
        overall_status=overall,
    )


@router.get("/victron", response_model=VictronStatus)
async def get_victron_status(
    state_machine=Depends(get_state_machine),
    gpio_monitor=Depends(get_gpio_monitor),
) -> VictronStatus:
    """
    Get Victron relay input status.

    Returns current GPIO17 state and last change time.
    """
    status = await state_machine.get_victron_status(
        mock_mode=gpio_monitor.mock_mode if gpio_monitor else settings.is_mock_gpio
    )
    return status


@router.get("/status", response_model=FullSystemStatus)
async def get_full_status(
    state_machine=Depends(get_state_machine),
) -> FullSystemStatus:
    """
    Get complete system status.

    Returns generator, victron, slave health, override, and system metrics.
    """
    system_health = await get_system_health()
    return await state_machine.get_full_status(system_health)


@router.get("/info")
async def get_system_metadata() -> dict:
    """
    Get system metadata.

    Returns hostname, platform, Python version, etc.
    """
    import socket

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "timestamp": int(time.time()),
    }


@router.post("/reboot")
async def reboot_system(
    state_machine=Depends(get_state_machine),
) -> dict:
    """
    Initiate system reboot.

    Logs event and sends webhook before rebooting.
    Reboot has a 5-second delay.
    """
    # Log event
    await state_machine.log_event("SYSTEM_REBOOT", {"initiated_by": "api"})

    # Schedule reboot in background
    async def do_reboot():
        await asyncio.sleep(5)
        import subprocess

        subprocess.run(["sudo", "reboot"])

    asyncio.create_task(do_reboot())

    return {
        "success": True,
        "message": "Reboot initiated, system will restart in 5 seconds",
    }


# =========================================================================
# Automation Arming Endpoints
# =========================================================================


@router.get("/arm", response_model=AutomationArmStatus)
async def get_arm_status(
    state_machine=Depends(get_state_machine),
) -> AutomationArmStatus:
    """
    Get current automation arming status.

    Returns whether automation is armed and GenSlave connection status.
    """
    status = await state_machine.get_arm_status()
    return AutomationArmStatus(**status)


# Note: /arm and /disarm endpoints removed - GenSlave is source of truth
# for arm state. Use genslaveApi.arm/disarm directly.

# =========================================================================
# SSL Certificate Endpoints
# =========================================================================


@router.get("/ssl")
async def get_ssl_info() -> dict:
    """
    Get SSL certificate information.

    Returns certificate details including domain, expiry date, and issuer.
    Results are cached for 30 seconds to avoid slow Docker operations on every call.
    """
    # Check cache first
    cached = _get_cached("ssl_info")
    if cached is not None:
        return cached

    import logging
    from datetime import datetime

    logger = logging.getLogger(__name__)

    ssl_info = {
        "configured": False,
        "certificates": [],
    }

    def parse_cert_output(output: str, domain: str, cert_path: str) -> dict:
        """Parse openssl x509 output into certificate info dict."""
        cert_info = {
            "domain": domain,
            "path": cert_path,
            "type": "Let's Encrypt",
        }

        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("subject="):
                cert_info["subject"] = line.replace("subject=", "").strip()
            elif line.startswith("issuer="):
                cert_info["issuer"] = line.replace("issuer=", "").strip()
            elif line.startswith("notBefore="):
                cert_info["valid_from"] = line.replace("notBefore=", "").strip()
            elif line.startswith("notAfter="):
                cert_info["valid_until"] = line.replace("notAfter=", "").strip()
            elif "DNS:" in line:
                sans = [s.strip().replace("DNS:", "") for s in line.split(",") if "DNS:" in s]
                cert_info["san"] = sans

        # Calculate days until expiry
        if "valid_until" in cert_info:
            try:
                expiry = datetime.strptime(
                    cert_info["valid_until"],
                    "%b %d %H:%M:%S %Y %Z"
                )
                days_left = (expiry.replace(tzinfo=None) - datetime.now()).days
                cert_info["days_until_expiry"] = days_left
                cert_info["status"] = "valid" if days_left > 0 else "expired"
                if days_left <= 7:
                    cert_info["warning"] = "Certificate expiring soon!"
                elif days_left <= 30:
                    cert_info["warning"] = "Certificate expires within 30 days"
            except Exception:
                pass

        return cert_info

    # Try to get SSL info from certbot or nginx container
    try:
        import docker
        client = docker.from_env()

        # Find certbot container first (has openssl), fall back to nginx
        cert_container = None
        nginx_container = None
        for container in client.containers.list():
            name_lower = container.name.lower()
            if "certbot" in name_lower:
                cert_container = container
            elif "genmaster_nginx" in name_lower:
                nginx_container = container

        # Use certbot container for openssl commands (nginx:alpine doesn't have openssl)
        # Fall back to nginx just for listing directories
        exec_container = cert_container or nginx_container

        if exec_container:
            # List certificate directories
            try:
                exit_code, output = exec_container.exec_run(
                    "ls /etc/letsencrypt/live/",
                    demux=True
                )
                if exit_code == 0 and output[0]:
                    domains = output[0].decode("utf-8").strip().split("\n")
                    domains = [d for d in domains if d and not d.startswith("README")]

                    for domain in domains:
                        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"

                        # Get certificate info using openssl (only works in certbot container)
                        if cert_container:
                            exit_code, cert_output = cert_container.exec_run(
                                f"openssl x509 -in {cert_path} -noout -subject -issuer -dates -ext subjectAltName",
                                demux=True
                            )

                            if exit_code == 0 and cert_output[0]:
                                cert_str = cert_output[0].decode("utf-8")
                                cert_info = parse_cert_output(cert_str, domain, cert_path)
                                ssl_info["certificates"].append(cert_info)
                        else:
                            # Certbot not running - add basic info without openssl parsing
                            ssl_info["certificates"].append({
                                "domain": domain,
                                "path": cert_path,
                                "type": "Let's Encrypt",
                                "warning": "Certbot container not running - unable to read certificate details"
                            })

                    ssl_info["configured"] = len(ssl_info["certificates"]) > 0

            except Exception as e:
                logger.warning(f"Failed to list certificates: {e}")

    except ImportError:
        ssl_info["error"] = "Docker SDK not installed"
    except Exception as e:
        ssl_info["error"] = str(e)

    # Cache the result
    _set_cached("ssl_info", ssl_info)
    return ssl_info


@router.post("/ssl/renew")
async def force_renew_ssl_certificate() -> dict:
    """
    Force renewal of SSL certificates using certbot.

    After successful renewal, nginx is reloaded to apply new certificates.
    """
    import logging

    logger = logging.getLogger(__name__)
    result = {
        "success": False,
        "message": "",
        "renewal_output": "",
        "nginx_reloaded": False,
    }

    try:
        import docker
        client = docker.from_env()

        # Find certbot container
        try:
            certbot_container = client.containers.get("genmaster_certbot")
        except docker.errors.NotFound:
            raise HTTPException(
                status_code=404,
                detail="Certbot container (genmaster_certbot) not found. Is it running?",
            )

        if certbot_container.status != "running":
            raise HTTPException(
                status_code=400,
                detail=f"Certbot container is not running (status: {certbot_container.status})",
            )

        # Run certbot renew --force-renewal
        logger.info("Starting forced SSL certificate renewal...")
        exec_result = certbot_container.exec_run(
            cmd="certbot renew --force-renewal",
            demux=True,
        )

        stdout = exec_result.output[0].decode("utf-8") if exec_result.output[0] else ""
        stderr = exec_result.output[1].decode("utf-8") if exec_result.output[1] else ""
        renewal_output = stdout + stderr

        result["renewal_output"] = renewal_output

        if exec_result.exit_code != 0:
            logger.error(f"Certbot renewal failed with exit code {exec_result.exit_code}: {renewal_output}")
            result["message"] = f"Certificate renewal failed (exit code {exec_result.exit_code})"
            return result

        logger.info("Certificate renewal completed successfully")

        # Now reload nginx to apply new certificates
        try:
            nginx_container = client.containers.get("genmaster_nginx")
            if nginx_container.status == "running":
                reload_result = nginx_container.exec_run(
                    cmd="nginx -s reload",
                    demux=True,
                )
                if reload_result.exit_code == 0:
                    result["nginx_reloaded"] = True
                    logger.info("Nginx reloaded successfully")
                else:
                    reload_err = reload_result.output[1].decode("utf-8") if reload_result.output[1] else ""
                    logger.warning(f"Nginx reload failed: {reload_err}")
        except Exception as e:
            logger.warning(f"Failed to reload nginx: {e}")

        result["success"] = True
        result["message"] = "Certificate renewal completed successfully"

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="Docker SDK not installed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SSL renewal failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

    return result


@router.post("/test-slave")
async def test_slave_connection() -> dict:
    """
    Test connection to GenSlave.

    Returns success status and latency.
    """
    from app.services.slave_status_service import create_slave_client

    start_time = time.time()
    try:
        client = await create_slave_client()
        response = await client.health_check()
        await client.close()

        latency_ms = int((time.time() - start_time) * 1000)

        if response.success:
            return {
                "success": True,
                "latency_ms": latency_ms,
                "slave_status": response.data.get("status") if response.data else None,
            }
        else:
            return {
                "success": False,
                "error": response.error or "Unknown error",
                "latency_ms": latency_ms,
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "latency_ms": int((time.time() - start_time) * 1000),
        }


# =========================================================================
# External Services Status Endpoints
# =========================================================================


@router.get("/cloudflare")
async def get_cloudflare_status() -> dict:
    """
    Get Cloudflare Tunnel status.

    Returns tunnel connection status, connector info, metrics, and health.
    Parses container logs for connection status and uses HTTP to fetch metrics.
    Results are cached for 30 seconds to avoid slow Docker operations on every call.
    """
    # Check cache first
    cached = _get_cached("cloudflare")
    if cached is not None:
        return cached

    import logging
    import re
    import urllib.request

    logger = logging.getLogger(__name__)
    result = {
        "installed": False,
        "running": False,
        "connected": False,
        "version": None,
        "tunnel_id": None,
        "connector_id": None,
        "edge_locations": [],
        "connections_per_location": {},
        "metrics": {},
        "last_error": None,
        "error": None,
    }

    try:
        import docker
        client = docker.from_env()

        # Find cloudflared container (try multiple possible names)
        cf_container = None
        container_names = ["genmaster_cloudflared", "cloudflared", "cloudflare-tunnel"]
        for name in container_names:
            try:
                cf_container = client.containers.get(name)
                break
            except docker.errors.NotFound:
                continue

        # Also search by partial name
        if not cf_container:
            for container in client.containers.list(all=True):
                name = container.name.lower()
                if "cloudflare" in name or "cloudflared" in name:
                    cf_container = container
                    break

        if cf_container:
            result["installed"] = True
            result["running"] = cf_container.status == "running"

            if result["running"]:
                # Get cloudflared version
                try:
                    exit_code, output = cf_container.exec_run(
                        "cloudflared version",
                        demux=True
                    )
                    if exit_code == 0 and output[0]:
                        version_output = output[0].decode("utf-8").strip()
                        match = re.search(r'version\s+([\d.]+)', version_output)
                        if match:
                            result["version"] = match.group(1)
                except Exception:
                    # Fallback to image tag
                    if cf_container.image.tags:
                        result["version"] = cf_container.image.tags[0].split(":")[-1]

                # Parse logs for connection status, tunnel ID, connector ID, and edge locations
                # Using the same approach as n8n_nginx which is proven to work
                try:
                    logs = cf_container.logs(tail=100).decode("utf-8", errors="ignore")
                    logs_lower = logs.lower()
                    edge_locs = set()

                    # PRIMARY CONNECTION CHECK (from n8n_nginx)
                    # Check if "Connection" (case-sensitive) and "registered" both appear in logs
                    if "Connection" in logs and "registered" in logs_lower:
                        result["connected"] = True
                        logger.debug("Cloudflare connected: found 'Connection' and 'registered' in logs")

                    # Parse line by line for additional info
                    for line in logs.split("\n"):
                        line_lower = line.lower()

                        # Look for tunnel ID (tunnelID=xxx-xxx-xxx)
                        if "tunnelid" in line_lower:
                            match = re.search(r'tunnelID=([a-f0-9-]{36})', line, re.IGNORECASE)
                            if match:
                                result["tunnel_id"] = match.group(1)

                        # Look for connector ID (connectorID=xxx-xxx-xxx)
                        if "connectorid" in line_lower:
                            match = re.search(r'connectorID=([a-f0-9-]{36})', line, re.IGNORECASE)
                            if match:
                                result["connector_id"] = match.group(1)

                        # Extract edge location from "Registered tunnel connection" lines
                        # Pattern: location=LAX or location=SFO
                        loc_match = re.search(r'location=(\w+)', line, re.IGNORECASE)
                        if loc_match:
                            edge_locs.add(loc_match.group(1).upper())

                        # Look for errors (keep last one, filter common non-errors)
                        if ("err" in line_lower or "level=error" in line_lower) and "error" in line_lower:
                            # Skip common non-error messages
                            if "no error" not in line_lower and "error=<nil>" not in line_lower:
                                result["last_error"] = line.strip()[-200:]

                    if edge_locs:
                        result["edge_locations"] = list(edge_locs)

                except Exception as e:
                    logger.debug(f"Could not parse cloudflared logs: {e}")

                # Try to get metrics via HTTP from container's network
                metrics_text = None
                try:
                    # Get container's internal IP
                    networks = cf_container.attrs.get("NetworkSettings", {}).get("Networks", {})
                    for network_name, network_config in networks.items():
                        container_ip = network_config.get("IPAddress")
                        if container_ip:
                            try:
                                req = urllib.request.Request(
                                    f"http://{container_ip}:2000/metrics",
                                    headers={"User-Agent": "GenMaster/1.0"}
                                )
                                with urllib.request.urlopen(req, timeout=2) as resp:
                                    metrics_text = resp.read().decode("utf-8")
                                break
                            except Exception:
                                continue

                    # Also try localhost with mapped port
                    if not metrics_text:
                        ports = cf_container.attrs.get("NetworkSettings", {}).get("Ports", {})
                        for port_key, port_bindings in (ports or {}).items():
                            if "2000" in port_key and port_bindings:
                                host_port = port_bindings[0].get("HostPort", "2000")
                                try:
                                    req = urllib.request.Request(
                                        f"http://localhost:{host_port}/metrics",
                                        headers={"User-Agent": "GenMaster/1.0"}
                                    )
                                    with urllib.request.urlopen(req, timeout=2) as resp:
                                        metrics_text = resp.read().decode("utf-8")
                                    break
                                except Exception:
                                    continue
                except Exception as e:
                    logger.debug(f"Could not connect to cloudflared metrics endpoint: {e}")

                # Parse metrics if we got them
                if metrics_text:
                    try:
                        metrics = result["metrics"]

                        # Active streams
                        match = re.search(r'cloudflared_tunnel_active_streams\s+(\d+)', metrics_text)
                        if match:
                            metrics["active_streams"] = int(match.group(1))

                        # Total requests
                        match = re.search(r'cloudflared_tunnel_total_requests\s+(\d+)', metrics_text)
                        if match:
                            metrics["total_requests"] = int(match.group(1))

                        # Request errors
                        match = re.search(r'cloudflared_tunnel_request_errors\s+(\d+)', metrics_text)
                        if match:
                            metrics["request_errors"] = int(match.group(1))

                        # HA connections (key indicator of connection)
                        match = re.search(r'cloudflared_tunnel_ha_connections\s+(\d+)', metrics_text)
                        if match:
                            ha_connections = int(match.group(1))
                            metrics["ha_connections"] = ha_connections
                            # If we have HA connections, we're definitely connected
                            if ha_connections > 0:
                                result["connected"] = True

                        # Response codes
                        response_codes = {}
                        for match in re.finditer(
                            r'cloudflared_tunnel_response_by_code\{.*?status="(\d+)".*?\}\s+(\d+)',
                            metrics_text
                        ):
                            code = match.group(1)
                            count = int(match.group(2))
                            if count > 0:
                                response_codes[code] = count
                        if response_codes:
                            metrics["response_codes"] = response_codes

                        # Edge locations from metrics
                        locations = []
                        connections_per_loc = {}
                        for match in re.finditer(
                            r'cloudflared_tunnel_server_locations\{.*?location="([^"]+)".*?\}\s+(\d+)',
                            metrics_text
                        ):
                            loc = match.group(1)
                            count = int(match.group(2))
                            if count > 0:
                                if loc not in locations:
                                    locations.append(loc)
                                connections_per_loc[loc] = count
                        if locations:
                            result["edge_locations"] = locations
                            result["connections_per_location"] = connections_per_loc

                    except Exception as e:
                        logger.debug(f"Could not parse cloudflared metrics: {e}")
        else:
            result["installed"] = False
            result["error"] = "Cloudflare tunnel container not found"

    except ImportError:
        result["error"] = "Docker SDK not installed"
    except Exception as e:
        logger.warning(f"Failed to get Cloudflare status: {e}")
        result["error"] = str(e)

    # Fallback checks if primary log parsing didn't find connection
    if result.get("running") and not result.get("connected"):
        # Check 1: If we have HA connections from metrics, we're definitely connected
        if result.get("metrics", {}).get("ha_connections", 0) > 0:
            result["connected"] = True
            logger.debug("Cloudflare connected: ha_connections > 0")

        # Check 2: If we have edge locations (from logs or metrics), we're likely connected
        elif result.get("edge_locations") or result.get("connections_per_location"):
            result["connected"] = True
            logger.debug("Cloudflare connected: edge locations found")

        # Check 3: If we have traffic, we're connected
        elif result.get("metrics", {}).get("total_requests", 0) > 0:
            result["connected"] = True
            logger.debug("Cloudflare connected: has traffic")

    # Cache the result (cache both connected and not connected for 30s)
    _set_cached("cloudflare", result)
    return result


@router.get("/tailscale")
async def get_tailscale_status() -> dict:
    """
    Get Tailscale VPN status.

    Returns connection status, IP addresses, hostname, and peer information.
    Results are cached for 30 seconds to avoid slow Docker operations on every call.
    """
    # Check cache first
    cached = _get_cached("tailscale")
    if cached is not None:
        return cached

    import logging

    logger = logging.getLogger(__name__)
    result = {
        "installed": False,
        "running": False,
        "logged_in": False,
        "tailscale_ip": None,
        "hostname": None,
        "dns_name": None,
        "tailnet": None,
        "peers": [],
        "peer_count": 0,
        "online_peers": 0,
        "version": None,
        "error": None,
    }

    try:
        import docker
        client = docker.from_env()

        # Find tailscale container
        try:
            container = client.containers.get("genmaster_tailscale")
            result["installed"] = True
            result["running"] = container.status == "running"

            if result["running"]:
                # Try to get tailscale status from container
                try:
                    exit_code, output = container.exec_run(
                        "tailscale status --json",
                        demux=True
                    )
                    if exit_code == 0 and output[0]:
                        import json
                        status_data = json.loads(output[0].decode("utf-8"))
                        result["logged_in"] = status_data.get("BackendState") == "Running"

                        # Self info
                        self_info = status_data.get("Self", {})
                        result["hostname"] = self_info.get("HostName")
                        ips = self_info.get("TailscaleIPs", [])
                        result["tailscale_ip"] = ips[0] if ips else None
                        result["dns_name"] = self_info.get("DNSName", "").rstrip(".")

                        # Tailnet name
                        tailnet_data = status_data.get("CurrentTailnet", {})
                        result["tailnet"] = tailnet_data.get("Name") or tailnet_data.get("MagicDNSSuffix", "").rstrip(".")

                        # Self as peer (for display)
                        self_peer = {
                            "id": self_info.get("ID"),
                            "hostname": self_info.get("HostName"),
                            "ip": ips[0] if ips else None,
                            "online": True,
                            "os": self_info.get("OS"),
                            "is_self": True,
                        }

                        # Peer info
                        peers_data = status_data.get("Peer", {})
                        peers = [self_peer]
                        online_count = 1  # Self is always online

                        for peer_id, peer_info in peers_data.items():
                            peer_ips = peer_info.get("TailscaleIPs", [])
                            is_online = peer_info.get("Online", False)
                            peer = {
                                "id": peer_id,
                                "hostname": peer_info.get("HostName"),
                                "ip": peer_ips[0] if peer_ips else None,
                                "online": is_online,
                                "os": peer_info.get("OS"),
                                "is_self": False,
                            }
                            peers.append(peer)
                            if is_online:
                                online_count += 1

                        # Sort: self first, then online, then offline
                        peers.sort(key=lambda p: (not p.get("is_self"), not p["online"], p["hostname"] or ""))

                        result["peers"] = peers
                        result["peer_count"] = len(peers)
                        result["online_peers"] = online_count

                except Exception as e:
                    logger.debug(f"Failed to get tailscale status: {e}")

                # Get version from container exec
                try:
                    exit_code, output = container.exec_run(
                        "tailscale version",
                        demux=True
                    )
                    if exit_code == 0 and output[0]:
                        result["version"] = output[0].decode("utf-8").strip().split("\n")[0]
                except Exception:
                    pass

        except docker.errors.NotFound:
            result["installed"] = False

    except ImportError:
        result["error"] = "Docker SDK not installed"
    except Exception as e:
        logger.warning(f"Failed to get Tailscale status: {e}")
        result["error"] = str(e)

    # Only cache if tailscale is logged in (don't cache disconnected state)
    if result.get("logged_in"):
        _set_cached("tailscale", result)
    return result


@router.get("/docker/info")
async def get_docker_info() -> dict:
    """
    Get Docker daemon information.

    Returns version, containers count, images count, and resource usage.
    Results are cached for 30 seconds to avoid slow Docker operations on every call.
    """
    # Check cache first
    cached = _get_cached("docker_info")
    if cached is not None:
        return cached

    import logging

    logger = logging.getLogger(__name__)

    try:
        import docker
        client = docker.from_env()
        info = client.info()
        version = client.version()

        containers = client.containers.list(all=True)
        running = sum(1 for c in containers if c.status == "running")
        stopped = len(containers) - running

        # Get Docker disk usage
        disk_usage_gb = 0.0
        try:
            df = client.df()
            total_bytes = 0

            # Images - sum SharedSize and unique Size
            for img in df.get("Images", []) or []:
                size = img.get("Size", 0) or 0
                total_bytes += size

            # Containers - sum SizeRw (writable layer size)
            for container in df.get("Containers", []) or []:
                size_rw = container.get("SizeRw", 0) or 0
                total_bytes += size_rw

            # Volumes - sum UsageData.Size
            for vol in df.get("Volumes", []) or []:
                usage_data = vol.get("UsageData", {}) or {}
                size = usage_data.get("Size", 0) or 0
                if size > 0:
                    total_bytes += size

            # Build cache
            build_cache = df.get("BuildCache", []) or []
            for cache in build_cache:
                size = cache.get("Size", 0) or 0
                total_bytes += size

            disk_usage_gb = total_bytes / (1024 * 1024 * 1024)
        except Exception as df_err:
            logger.debug(f"Could not get Docker disk usage: {df_err}")

        result = {
            "version": version.get("Version"),
            "api_version": version.get("ApiVersion"),
            "os": info.get("OperatingSystem"),
            "architecture": info.get("Architecture"),
            "cpus": info.get("NCPU"),
            "memory_bytes": info.get("MemTotal"),
            "containers": {
                "total": len(containers),
                "running": running,
                "stopped": stopped,
            },
            "images": info.get("Images", 0),
            "storage_driver": info.get("Driver"),
            "disk_usage_gb": round(disk_usage_gb, 2),
        }
        # Cache the result
        _set_cached("docker_info", result)
        return result

    except ImportError:
        return {"error": "Docker SDK not installed"}
    except Exception as e:
        logger.warning(f"Failed to get Docker info: {e}")
        return {"error": str(e)}


@router.get("/network")
async def get_network_info() -> dict:
    """
    Get network information.

    Returns IP addresses, interfaces, DNS servers, and gateway.
    """
    import logging
    import socket
    import subprocess

    logger = logging.getLogger(__name__)

    result = {
        "hostname": socket.gethostname(),
        "interfaces": [],
        "dns_servers": [],
        "gateway": None,
    }

    try:
        import psutil

        # Get network interfaces
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface, all_addresses in addrs.items():
            if iface == "lo":
                continue

            # Build addresses array in the format frontend expects
            addresses = []
            is_up = stats.get(iface, type('', (), {'isup': False})()).isup if iface in stats else False

            for addr in all_addresses:
                if addr.family == socket.AF_INET:
                    addresses.append({"type": "ipv4", "address": addr.address})
                elif addr.family == socket.AF_INET6:
                    if not addr.address.startswith("fe80"):  # Skip link-local
                        addresses.append({"type": "ipv6", "address": addr.address})
                elif addr.family == psutil.AF_LINK:
                    addresses.append({"type": "mac", "address": addr.address})

            if addresses:
                result["interfaces"].append({
                    "name": iface,
                    "addresses": addresses,
                    "up": is_up,
                })

        # Get default gateway
        try:
            gws = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if gws.returncode == 0:
                parts = gws.stdout.strip().split()
                if "via" in parts:
                    idx = parts.index("via")
                    if idx + 1 < len(parts):
                        result["gateway"] = parts[idx + 1]
        except Exception:
            # Fallback: try netstat or route command
            try:
                route = subprocess.run(
                    ["route", "-n", "get", "default"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if route.returncode == 0:
                    for line in route.stdout.split("\n"):
                        if "gateway:" in line.lower():
                            result["gateway"] = line.split(":")[-1].strip()
                            break
            except Exception:
                pass

        # Get DNS servers from resolv.conf
        try:
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    if line.strip().startswith("nameserver"):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            result["dns_servers"].append(parts[1])
        except Exception:
            pass

    except ImportError:
        result["error"] = "psutil not installed"
    except Exception as e:
        logger.warning(f"Failed to get network info: {e}")
        result["error"] = str(e)

    return result


@router.get("/host/wifi")
async def get_host_wifi_info() -> dict:
    """
    Get WiFi information for the Docker host.

    Uses the host-tools sidecar container for instant execution.
    Results are cached for 30 seconds.
    """
    # Check cache first
    cached = _get_cached("host_wifi")
    if cached is not None:
        return cached

    import logging
    logger = logging.getLogger(__name__)

    result = {
        "available": False,
        "connected": False,
        "interface": None,
        "ssid": None,
        "signal_dbm": None,
        "signal_percent": None,
        "ip_address": None,
    }

    # Script to get WiFi info (tools are pre-installed in host-tools container)
    script = """
        WLAN=$(ls /sys/class/net/ 2>/dev/null | grep -E "^wlan|^wlp" | head -1)
        if [ -z "$WLAN" ]; then
            echo "NO_WIFI"
            exit 0
        fi
        echo "IFACE:$WLAN"
        IP=$(ip addr show "$WLAN" 2>/dev/null | grep "inet " | awk '{print $2}' | cut -d/ -f1)
        [ -n "$IP" ] && echo "IP:$IP"
        SSID=$(iwgetid "$WLAN" -r 2>/dev/null)
        [ -n "$SSID" ] && echo "SSID:$SSID"
        if [ -f /proc/net/wireless ]; then
            SIGNAL=$(grep "$WLAN" /proc/net/wireless 2>/dev/null | awk '{print $4}' | tr -d '.')
            [ -n "$SIGNAL" ] && echo "SIGNAL:$SIGNAL"
        fi
    """

    success, output_str = _exec_host_command(script)

    if not success:
        result["error"] = output_str
        return result

    if "NO_WIFI" not in output_str:
        result["available"] = True

        for line in output_str.split("\n"):
            if line.startswith("IFACE:"):
                result["interface"] = line.split(":", 1)[1].strip()
            elif line.startswith("IP:"):
                result["ip_address"] = line.split(":", 1)[1].strip()
                result["connected"] = True
            elif line.startswith("SSID:"):
                result["ssid"] = line.split(":", 1)[1].strip()
                result["connected"] = True
            elif line.startswith("SIGNAL:"):
                try:
                    signal_val = int(line.split(":", 1)[1].strip())
                    # Convert to dBm if needed
                    if signal_val > 0:
                        signal_dbm = signal_val - 256 if signal_val > 63 else signal_val - 100
                    else:
                        signal_dbm = signal_val
                    result["signal_dbm"] = signal_dbm
                    result["signal_percent"] = max(0, min(100, int((signal_dbm + 90) * 100 / 60)))
                except ValueError:
                    pass

    # Cache results (even if no WiFi - avoids repeated checks)
    _set_cached("host_wifi", result)

    return result


@router.get("/host/wifi/networks")
async def scan_host_wifi_networks() -> dict:
    """
    Scan for available WiFi networks on the Docker host.

    Uses the host-tools sidecar container for instant execution.
    Returns list of networks with SSID, signal strength, and security type.
    """
    import logging
    logger = logging.getLogger(__name__)

    result = {
        "success": False,
        "networks": [],
        "error": None,
    }

    # nmcli is pre-installed in host-tools container
    script = 'nmcli -t -f SSID,SIGNAL,SECURITY device wifi list 2>/dev/null || echo "SCAN_FAILED"'

    success, output_str = _exec_host_command(script)

    if not success:
        result["error"] = output_str
        return result

    if "SCAN_FAILED" in output_str or not output_str:
        result["error"] = "WiFi scan failed - no wireless interface available"
        return result

    # Parse nmcli output: SSID:SIGNAL:SECURITY
    networks = []
    seen_ssids = set()

    for line in output_str.split("\n"):
        if not line.strip() or line.startswith("SCAN_FAILED"):
            continue

        parts = line.split(":")
        if len(parts) >= 2:
            ssid = parts[0].strip()
            # Skip empty SSIDs (hidden networks) and duplicates
            if not ssid or ssid in seen_ssids:
                continue

            seen_ssids.add(ssid)

            try:
                signal = int(parts[1]) if parts[1] else 0
            except ValueError:
                signal = 0

            security = parts[2].strip() if len(parts) > 2 else ""
            # Normalize security display
            if not security or security == "--":
                security = "Open"

            networks.append({
                "ssid": ssid,
                "signal_percent": signal,
                "security": security,
            })

    # Sort by signal strength (strongest first)
    networks.sort(key=lambda x: x["signal_percent"], reverse=True)
    result["networks"] = networks
    result["success"] = True

    return result


class WifiConnectRequest(BaseModel):
    """Request to connect to a WiFi network."""

    ssid: str = Field(..., min_length=1, max_length=32, description="WiFi network SSID")
    password: Optional[str] = Field(None, description="WiFi password (None for open networks)")


@router.post("/host/wifi/connect")
async def connect_host_wifi(request: WifiConnectRequest) -> dict:
    """
    Connect the Docker host to a WiFi network.

    Uses the host-tools sidecar container for instant execution.
    Requires the SSID and optionally a password for secured networks.
    """
    import logging
    import shlex

    logger = logging.getLogger(__name__)

    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    # Sanitize SSID to prevent command injection
    ssid = request.ssid.strip()
    if not ssid:
        result["error"] = "SSID cannot be empty"
        return result

    # Log the connection attempt (without password)
    logger.info(f"Attempting to connect host WiFi to SSID: {ssid}")

    # Build nmcli command - use shlex.quote for safe escaping
    safe_ssid = shlex.quote(ssid)

    if request.password:
        # For secured networks
        safe_password = shlex.quote(request.password)
        script = f"nmcli device wifi connect {safe_ssid} password {safe_password} 2>&1"
    else:
        # For open networks
        script = f"nmcli device wifi connect {safe_ssid} 2>&1"

    success, output_str = _exec_host_command(script, timeout=30)

    if not success:
        # Parse common nmcli errors
        if "secrets were required" in output_str.lower() or "no secrets" in output_str.lower():
            result["error"] = "Password required for this network"
        elif "not found" in output_str.lower():
            result["error"] = f"Network '{ssid}' not found"
        elif "invalid" in output_str.lower():
            result["error"] = "Invalid password"
        else:
            result["error"] = output_str
        return result

    # Check for success indicators
    if "successfully activated" in output_str.lower() or "connection successfully activated" in output_str.lower():
        result["success"] = True
        result["message"] = f"Successfully connected to {ssid}"
        logger.info(f"Successfully connected host WiFi to: {ssid}")
    elif "error" in output_str.lower():
        result["error"] = output_str
        logger.warning(f"WiFi connection failed: {output_str}")
    else:
        # Assume success if no explicit error
        result["success"] = True
        result["message"] = f"Connection initiated to {ssid}"

    return result


class WifiAddRequest(BaseModel):
    """Request to add a known WiFi network."""

    ssid: str = Field(..., min_length=1, max_length=32, description="WiFi network SSID")
    password: str = Field(..., min_length=8, max_length=63, description="WiFi password (WPA/WPA2)")
    auto_connect: bool = Field(True, description="Automatically connect when network is available")


@router.get("/host/wifi/saved")
async def list_host_saved_wifi() -> dict:
    """
    List saved WiFi network profiles on the Docker host.

    Uses the host-tools sidecar container for instant execution.
    """
    result = {
        "success": False,
        "networks": [],
        "error": None,
    }

    script = 'nmcli -t -f NAME,TYPE,AUTOCONNECT connection show 2>/dev/null || echo "LIST_FAILED"'

    success, output_str = _exec_host_command(script)

    if not success:
        result["error"] = output_str
        return result

    if "LIST_FAILED" in output_str:
        result["error"] = "Failed to list saved networks"
        return result

    networks = []
    for line in output_str.split("\n"):
        if not line.strip() or "LIST_FAILED" in line:
            continue

        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == "802-11-wireless":
            networks.append({
                "name": parts[0],
                "ssid": parts[0],
                "auto_connect": parts[2].lower() == "yes",
            })

    result["networks"] = networks
    result["success"] = True

    return result


@router.post("/host/wifi/add")
async def add_host_wifi(request: WifiAddRequest) -> dict:
    """
    Add a known WiFi network to the Docker host for auto-connect.

    Uses the host-tools sidecar container for instant execution.
    Creates a saved WiFi connection profile that will automatically
    connect when the network becomes available.
    """
    import logging
    import shlex

    logger = logging.getLogger(__name__)

    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    ssid = request.ssid.strip()
    if not ssid:
        result["error"] = "SSID cannot be empty"
        return result

    logger.info(f"Adding known WiFi network to host: {ssid}")

    safe_ssid = shlex.quote(ssid)
    safe_password = shlex.quote(request.password)
    auto_connect = "yes" if request.auto_connect else "no"

    script = (
        f"nmcli connection add type wifi con-name {safe_ssid} ssid {safe_ssid} "
        f"wifi-sec.key-mgmt wpa-psk wifi-sec.psk {safe_password} "
        f"connection.autoconnect {auto_connect} 2>&1"
    )

    success, output_str = _exec_host_command(script)

    if not success:
        if "already exists" in output_str.lower():
            result["error"] = f"Network '{ssid}' already exists. Delete it first to update."
        else:
            result["error"] = output_str
        return result

    if "successfully added" in output_str.lower() or "connection" in output_str.lower():
        result["success"] = True
        result["message"] = f"WiFi network '{ssid}' added successfully. It will auto-connect when available."
        logger.info(f"Successfully added WiFi network to host: {ssid}")
    elif "already exists" in output_str.lower():
        result["error"] = f"Network '{ssid}' already exists. Delete it first to update."
    else:
        result["error"] = output_str or "Failed to add network"
        logger.warning(f"Failed to add WiFi network: {output_str}")

    return result


class WifiDeleteRequest(BaseModel):
    """Request to delete a saved WiFi network."""

    name: str = Field(..., min_length=1, description="Connection profile name to delete")


@router.post("/host/wifi/delete")
async def delete_host_wifi(request: WifiDeleteRequest) -> dict:
    """
    Delete a saved WiFi network from the Docker host.

    Uses the host-tools sidecar container for instant execution.
    Removes a previously saved WiFi connection profile.
    """
    import logging
    import shlex

    logger = logging.getLogger(__name__)

    result = {
        "success": False,
        "message": "",
        "error": None,
    }

    name = request.name.strip()
    if not name:
        result["error"] = "Connection name cannot be empty"
        return result

    logger.info(f"Deleting WiFi network from host: {name}")

    safe_name = shlex.quote(name)
    script = f"nmcli connection delete {safe_name} 2>&1"

    success, output_str = _exec_host_command(script)

    if not success:
        if "not found" in output_str.lower():
            result["error"] = f"Network '{name}' not found"
        else:
            result["error"] = output_str
        return result

    if "successfully deleted" in output_str.lower() or "deleted" in output_str.lower():
        result["success"] = True
        result["message"] = f"WiFi network '{name}' deleted successfully."
        logger.info(f"Successfully deleted WiFi network from host: {name}")
    elif "not found" in output_str.lower():
        result["error"] = f"Network '{name}' not found"
    else:
        result["error"] = output_str or "Failed to delete network"
        logger.warning(f"Failed to delete WiFi network: {output_str}")

    return result


@router.get("/timezone")
async def get_timezone_info() -> dict:
    """
    Get system timezone information.
    """
    import subprocess
    from datetime import datetime
    from datetime import timezone as tz

    result = {
        "timezone": None,
        "offset": None,
        "current_time": datetime.now().isoformat(),
        "utc_time": datetime.now(tz.utc).isoformat(),
    }

    try:
        # Try to get timezone from timedatectl
        proc = subprocess.run(
            ["timedatectl", "show", "--property=Timezone", "--value"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode == 0:
            result["timezone"] = proc.stdout.strip()
    except Exception:
        # Fallback to reading /etc/timezone
        try:
            with open("/etc/timezone", "r") as f:
                result["timezone"] = f.read().strip()
        except Exception:
            pass

    # Calculate offset
    try:
        now = datetime.now()
        utc_now = datetime.now(tz.utc).replace(tzinfo=None)
        offset_seconds = (now - utc_now).total_seconds()
        hours = int(offset_seconds // 3600)
        minutes = int((offset_seconds % 3600) // 60)
        result["offset"] = f"{'+' if hours >= 0 else ''}{hours:02d}:{abs(minutes):02d}"
    except Exception:
        pass

    return result


@router.get("/external-services")
async def get_external_services_status() -> list:
    """
    Get list of external services configured via nginx proxy.

    Returns array of service objects with name, description, url, and running status.
    """
    import logging
    import os

    logger = logging.getLogger(__name__)
    services = []

    # Add configured external services
    # These could come from a config file or database in future
    # For now, return known services based on docker container status

    try:
        import docker
        client = docker.from_env()

        # Check for Portainer
        try:
            portainer = client.containers.get("genmaster_portainer")
            services.append({
                "name": "Portainer",
                "description": "Docker container management",
                "url": "/portainer/",
                "running": portainer.status == "running",
                "color": "bg-blue-100 dark:bg-blue-500/20",
                "iconColor": "text-blue-500",
            })
        except Exception:
            pass

    except Exception as e:
        logger.debug(f"Docker not available: {e}")
        # Return services even if Docker isn't available
        # Just mark them as not running

    # Add any statically configured services from environment
    # Format: SERVICE_NAME=description|url
    for key, value in os.environ.items():
        if key.startswith("EXTERNAL_SERVICE_"):
            try:
                parts = value.split("|")
                if len(parts) >= 2:
                    services.append({
                        "name": key.replace("EXTERNAL_SERVICE_", "").replace("_", " ").title(),
                        "description": parts[0],
                        "url": parts[1],
                        "running": True,
                        "color": "bg-gray-100 dark:bg-gray-500/20",
                        "iconColor": "text-gray-500",
                    })
            except Exception:
                pass

    return services


# =========================================================================
# System Power Control Endpoints
# =========================================================================

from pydantic import BaseModel, Field


class SystemActionResponse(BaseModel):
    """Response from system action (shutdown/reboot)."""

    success: bool = Field(description="Whether the action was initiated")
    message: str = Field(description="Status message")
    action: str = Field(description="The action that was requested")


@router.post("/host/shutdown", response_model=SystemActionResponse)
async def shutdown_host():
    """
    Shutdown the Docker host (Raspberry Pi running GenMaster).

    This runs a privileged container to execute shutdown on the host system.
    The GenMaster containers will stop gracefully before the host powers off.

    WARNING: This will make GenMaster unreachable until manually powered on.
    """
    import logging

    import docker

    logger = logging.getLogger(__name__)

    try:
        client = docker.from_env()

        logger.warning("Host SHUTDOWN requested via API")

        # Run a privileged container to execute shutdown command on host
        # Using alpine:latest as a minimal image
        client.containers.run(
            "alpine:latest",
            command=["sh", "-c", "echo 'Shutting down host...' && sleep 2 && nsenter -t 1 -m -u -n -i -- shutdown -h now"],
            privileged=True,
            pid_mode="host",
            remove=True,
            detach=True,
        )

        return SystemActionResponse(
            success=True,
            message="Host shutdown initiated. System will power off shortly.",
            action="shutdown",
        )

    except Exception as e:
        logger.error(f"Error initiating host shutdown: {e}")
        return SystemActionResponse(
            success=False,
            message=f"Failed to initiate shutdown: {str(e)}",
            action="shutdown",
        )


@router.post("/host/reboot", response_model=SystemActionResponse)
async def reboot_host():
    """
    Reboot the Docker host (Raspberry Pi running GenMaster).

    This runs a privileged container to execute reboot on the host system.
    The GenMaster containers will stop gracefully and restart after the host reboots.

    After reboot, GenMaster will start automatically and become available
    again (typically within 60-90 seconds).
    """
    import logging

    import docker

    logger = logging.getLogger(__name__)

    try:
        client = docker.from_env()

        logger.warning("Host REBOOT requested via API")

        # Run a privileged container to execute reboot command on host
        client.containers.run(
            "alpine:latest",
            command=["sh", "-c", "echo 'Rebooting host...' && sleep 2 && nsenter -t 1 -m -u -n -i -- reboot"],
            privileged=True,
            pid_mode="host",
            remove=True,
            detach=True,
        )

        return SystemActionResponse(
            success=True,
            message="Host reboot initiated. System will restart shortly.",
            action="reboot",
        )

    except Exception as e:
        logger.error(f"Error initiating host reboot: {e}")
        return SystemActionResponse(
            success=False,
            message=f"Failed to initiate reboot: {str(e)}",
            action="reboot",
        )


# =============================================================================
# WiFi Watchdog Management
# =============================================================================


class WifiWatchdogStatus(BaseModel):
    """WiFi watchdog service status."""

    installed: bool = Field(description="Whether watchdog script is installed on host")
    enabled: bool = Field(description="Whether systemd service is enabled")
    running: bool = Field(description="Whether service is currently active")
    failure_count: int = Field(default=0, description="Consecutive connectivity failures")
    last_recovery: Optional[str] = Field(
        default=None, description="Timestamp of last recovery"
    )


class WifiWatchdogActionResponse(BaseModel):
    """Response from WiFi watchdog actions."""

    success: bool = Field(description="Whether the action succeeded")
    message: str = Field(description="Human-readable status message")
    status: Optional[WifiWatchdogStatus] = Field(
        default=None, description="Current watchdog status after action"
    )


def _run_host_command_sync(cmd: str) -> tuple[bool, str]:
    """
    Run a command on the host using nsenter via the host-tools container.

    The host-tools container runs with pid:host and has nsenter installed,
    allowing us to execute commands in the host's namespaces.

    Returns (success, output_or_error).
    """
    import logging

    import docker

    logger = logging.getLogger(__name__)

    try:
        client = docker.from_env()

        # Get the host-tools container (has nsenter and pid:host)
        try:
            container = client.containers.get(HOST_TOOLS_CONTAINER)
        except docker.errors.NotFound:
            logger.warning(f"Host-tools container '{HOST_TOOLS_CONTAINER}' not found")
            return False, f"Container '{HOST_TOOLS_CONTAINER}' not running. Start it with: docker compose up -d host-tools"

        if container.status != "running":
            logger.warning(f"Host-tools container is not running (status: {container.status})")
            return False, f"Container not running (status: {container.status})"

        # Use nsenter to run command in host's namespaces
        # -t 1 targets PID 1 (host's init), -m -u -n -i enters mount, uts, net, ipc namespaces
        exit_code, output = container.exec_run(
            cmd=["nsenter", "-t", "1", "-m", "-u", "-n", "-i", "--", "sh", "-c", cmd],
            demux=False,
        )

        output_str = output.decode("utf-8").strip() if output else ""

        if exit_code != 0:
            logger.debug(f"Host command failed (exit {exit_code}): {cmd[:50]}...")
            return False, output_str or f"Command failed with exit code {exit_code}"

        return True, output_str

    except Exception as e:
        logger.error(f"Error running host command: {e}")
        return False, str(e)


def _get_wifi_watchdog_status() -> WifiWatchdogStatus:
    """Get current WiFi watchdog status from host."""
    import logging

    logger = logging.getLogger(__name__)

    # Check if script is installed
    installed_ok, _ = _run_host_command_sync("test -f /usr/local/bin/wifi-watchdog.sh")
    installed = installed_ok

    # Check if service is enabled
    enabled_ok, _ = _run_host_command_sync("systemctl is-enabled wifi-watchdog 2>/dev/null")
    enabled = enabled_ok

    # Check if service is running
    running_ok, _ = _run_host_command_sync("systemctl is-active wifi-watchdog 2>/dev/null")
    running = running_ok

    # Read state file for failure count and last recovery
    failure_count = 0
    last_recovery = None

    if running:
        state_ok, state_output = _run_host_command_sync(
            "cat /var/run/wifi-watchdog.state 2>/dev/null"
        )
        if state_ok and state_output:
            for line in state_output.split("\n"):
                if line.startswith("CONSECUTIVE_FAILURES="):
                    try:
                        failure_count = int(line.split("=")[1])
                    except (IndexError, ValueError):
                        pass

        # Check journal for last recovery message
        recovery_ok, recovery_output = _run_host_command_sync(
            "journalctl -u wifi-watchdog --no-pager -n 50 2>/dev/null | grep -i 'restored' | tail -1"
        )
        if recovery_ok and recovery_output:
            # Extract timestamp from journal output
            parts = recovery_output.split()
            if len(parts) >= 3:
                last_recovery = " ".join(parts[:3])

    return WifiWatchdogStatus(
        installed=installed,
        enabled=enabled,
        running=running,
        failure_count=failure_count,
        last_recovery=last_recovery,
    )


@router.get("/wifi-watchdog", response_model=WifiWatchdogStatus)
async def get_wifi_watchdog_status():
    """
    Get WiFi watchdog service status.

    Returns installation status, enabled/running state, and failure metrics.
    """
    return await asyncio.to_thread(_get_wifi_watchdog_status)


def _copy_file_to_host_sync(src_path: str, dest_path: str, make_executable: bool = False) -> tuple[bool, str]:
    """
    Copy a file from host-tools container's mounted /scripts to the host filesystem.

    Uses cat to read from container, pipes through nsenter to write to host.
    This avoids command-line length limits from base64 encoding.
    """
    import logging

    import docker

    logger = logging.getLogger(__name__)

    try:
        client = docker.from_env()

        try:
            container = client.containers.get(HOST_TOOLS_CONTAINER)
        except docker.errors.NotFound:
            return False, f"Container '{HOST_TOOLS_CONTAINER}' not running"

        if container.status != "running":
            return False, f"Container not running (status: {container.status})"

        # Build command: cat file | nsenter ... -- sh -c 'cat > dest && chmod +x dest'
        chmod_cmd = " && chmod +x " + dest_path if make_executable else ""
        cmd = f"cat {src_path} | nsenter -t 1 -m -u -n -i -- sh -c 'cat > {dest_path}{chmod_cmd}'"

        exit_code, output = container.exec_run(
            cmd=["sh", "-c", cmd],
            demux=False,
        )

        output_str = output.decode("utf-8").strip() if output else ""

        if exit_code != 0:
            logger.debug(f"Copy to host failed (exit {exit_code}): {src_path} -> {dest_path}")
            return False, output_str or f"Command failed with exit code {exit_code}"

        return True, output_str

    except Exception as e:
        logger.error(f"Error copying file to host: {e}")
        return False, str(e)


@router.post("/wifi-watchdog/install", response_model=WifiWatchdogActionResponse)
async def install_wifi_watchdog():
    """
    Install the WiFi watchdog service on the host.

    Copies the watchdog script and systemd service file from the host-tools
    container's mounted /scripts directory to the host, then enables and
    starts the service.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Copy script to host (from host-tools container's /scripts mount)
        logger.info("Installing wifi-watchdog.sh to host")
        ok, output = await asyncio.to_thread(
            _copy_file_to_host_sync,
            "/scripts/wifi-watchdog.sh",
            "/usr/local/bin/wifi-watchdog.sh",
            True  # make executable
        )
        if not ok:
            return WifiWatchdogActionResponse(
                success=False,
                message=f"Failed to install script: {output}",
                status=None,
            )

        # Copy service file to host
        logger.info("Installing wifi-watchdog.service to host")
        ok, output = await asyncio.to_thread(
            _copy_file_to_host_sync,
            "/scripts/wifi-watchdog.service",
            "/etc/systemd/system/wifi-watchdog.service",
            False
        )
        if not ok:
            return WifiWatchdogActionResponse(
                success=False,
                message=f"Failed to install service file: {output}",
                status=None,
            )

        # Reload systemd and enable service
        logger.info("Enabling wifi-watchdog service")
        ok, output = await asyncio.to_thread(
            _run_host_command_sync,
            "systemctl daemon-reload && systemctl enable --now wifi-watchdog"
        )
        if not ok:
            return WifiWatchdogActionResponse(
                success=False,
                message=f"Failed to enable service: {output}",
                status=None,
            )

        # Get current status
        status = await asyncio.to_thread(_get_wifi_watchdog_status)

        logger.info("WiFi watchdog installed and started successfully")
        return WifiWatchdogActionResponse(
            success=True,
            message="WiFi watchdog installed and started successfully",
            status=status,
        )

    except Exception as e:
        logger.error(f"Error installing wifi watchdog: {e}")
        return WifiWatchdogActionResponse(
            success=False,
            message=f"Installation failed: {str(e)}",
            status=None,
        )


@router.post("/wifi-watchdog/enable", response_model=WifiWatchdogActionResponse)
async def enable_wifi_watchdog():
    """
    Enable and start the WiFi watchdog service.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Check if installed first
        status = await asyncio.to_thread(_get_wifi_watchdog_status)
        if not status.installed:
            return WifiWatchdogActionResponse(
                success=False,
                message="WiFi watchdog is not installed. Install it first.",
                status=status,
            )

        # Enable and start the service
        ok, output = await asyncio.to_thread(
            _run_host_command_sync,
            "systemctl enable --now wifi-watchdog"
        )

        if not ok:
            return WifiWatchdogActionResponse(
                success=False,
                message=f"Failed to enable service: {output}",
                status=status,
            )

        # Get updated status
        status = await asyncio.to_thread(_get_wifi_watchdog_status)

        logger.info("WiFi watchdog enabled and started")
        return WifiWatchdogActionResponse(
            success=True,
            message="WiFi watchdog enabled and started",
            status=status,
        )

    except Exception as e:
        logger.error(f"Error enabling wifi watchdog: {e}")
        return WifiWatchdogActionResponse(
            success=False,
            message=f"Failed to enable: {str(e)}",
            status=None,
        )


@router.post("/wifi-watchdog/disable", response_model=WifiWatchdogActionResponse)
async def disable_wifi_watchdog():
    """
    Disable and stop the WiFi watchdog service.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Disable and stop the service
        ok, output = await asyncio.to_thread(
            _run_host_command_sync,
            "systemctl disable --now wifi-watchdog"
        )

        if not ok:
            # If service doesn't exist, that's fine
            if "not found" in output.lower() or "no such" in output.lower():
                return WifiWatchdogActionResponse(
                    success=True,
                    message="WiFi watchdog is not installed",
                    status=WifiWatchdogStatus(
                        installed=False,
                        enabled=False,
                        running=False,
                        failure_count=0,
                        last_recovery=None,
                    ),
                )
            return WifiWatchdogActionResponse(
                success=False,
                message=f"Failed to disable service: {output}",
                status=None,
            )

        # Get updated status
        status = await asyncio.to_thread(_get_wifi_watchdog_status)

        logger.info("WiFi watchdog disabled and stopped")
        return WifiWatchdogActionResponse(
            success=True,
            message="WiFi watchdog disabled and stopped",
            status=status,
        )

    except Exception as e:
        logger.error(f"Error disabling wifi watchdog: {e}")
        return WifiWatchdogActionResponse(
            success=False,
            message=f"Failed to disable: {str(e)}",
            status=None,
        )
