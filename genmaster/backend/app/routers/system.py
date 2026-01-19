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

from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.schemas import (
    ArmRequest,
    ArmResponse,
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
        from app.services.slave_client import SlaveClient

        client = SlaveClient()
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
    """
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
    from app.services.slave_client import SlaveClient

    start_time = time.time()
    try:
        client = SlaveClient()
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

    Returns tunnel connection status, connector info, and health.
    """
    import logging
    import re

    logger = logging.getLogger(__name__)
    result = {
        "installed": False,
        "running": False,
        "connected": False,
        "version": None,
        "tunnel_id": None,
        "edge_locations": [],
        "metrics": {},
        "last_error": None,
        "error": None,
    }

    try:
        import docker
        client = docker.from_env()

        # Find cloudflared container
        try:
            container = client.containers.get("genmaster_cloudflared")
            result["installed"] = True
            result["running"] = container.status == "running"

            if result["running"]:
                # Try to get tunnel info from logs
                try:
                    logs = container.logs(tail=100).decode("utf-8")
                    edge_locs = set()
                    for line in logs.split("\n"):
                        # Check for connection registration
                        if "Connection" in line and "registered" in line:
                            result["connected"] = True
                            # Extract edge location (e.g., "DFW" from logs)
                            loc_match = re.search(r'connIndex=\d+ ip=[\d.]+.*?location=(\w+)', line)
                            if loc_match:
                                edge_locs.add(loc_match.group(1))
                        # Extract tunnel/connector ID
                        if "tunnelID" in line or "Tunnel ID" in line:
                            match = re.search(r'[a-f0-9-]{36}', line)
                            if match:
                                result["tunnel_id"] = match.group()
                        # Extract errors
                        if "ERR" in line or "error" in line.lower():
                            result["last_error"] = line.strip()[-200:]
                    result["edge_locations"] = list(edge_locs)
                except Exception:
                    pass

                # Get image version
                if container.image.tags:
                    result["version"] = container.image.tags[0].split(":")[-1]

        except docker.errors.NotFound:
            result["installed"] = False

    except ImportError:
        result["error"] = "Docker SDK not installed"
    except Exception as e:
        logger.warning(f"Failed to get Cloudflare status: {e}")
        result["error"] = str(e)

    return result


@router.get("/tailscale")
async def get_tailscale_status() -> dict:
    """
    Get Tailscale VPN status.

    Returns connection status, IP addresses, hostname, and peer information.
    """
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

    return result


@router.get("/docker/info")
async def get_docker_info() -> dict:
    """
    Get Docker daemon information.

    Returns version, containers count, images count, and resource usage.
    """
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
            # Sum up all types of disk usage
            for layer in df.get("LayersSize", 0) or []:
                disk_usage_gb += layer if isinstance(layer, (int, float)) else 0
            # LayersSize is usually a single int
            if isinstance(df.get("LayersSize"), (int, float)):
                disk_usage_gb = df.get("LayersSize", 0) / (1024 * 1024 * 1024)
            # Add volumes
            for vol in df.get("Volumes", []) or []:
                if vol.get("UsageData", {}).get("Size"):
                    disk_usage_gb += vol["UsageData"]["Size"] / (1024 * 1024 * 1024)
            # Add images
            for img in df.get("Images", []) or []:
                if img.get("Size"):
                    disk_usage_gb += img["Size"] / (1024 * 1024 * 1024)
        except Exception as df_err:
            logger.debug(f"Could not get Docker disk usage: {df_err}")

        return {
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


@router.get("/timezone")
async def get_timezone_info() -> dict:
    """
    Get system timezone information.
    """
    import subprocess
    from datetime import datetime, timezone as tz

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
