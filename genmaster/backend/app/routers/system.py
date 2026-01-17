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


@router.post("/arm", response_model=ArmResponse)
async def arm_automation(
    request: ArmRequest = ArmRequest(),
    state_machine=Depends(get_state_machine),
) -> ArmResponse:
    """
    Arm the automation system.

    Arming enables all automated actions:
    - Victron signal will trigger generator start/stop
    - Scheduled runs will execute
    - Heartbeat failures will trigger safety actions

    Before arming, the system verifies GenSlave connectivity.
    Warnings are returned if connectivity is degraded.
    """
    result = await state_machine.arm_automation(source=request.source)
    return ArmResponse(**result)


@router.post("/disarm", response_model=ArmResponse)
async def disarm_automation(
    request: ArmRequest = ArmRequest(),
    state_machine=Depends(get_state_machine),
) -> ArmResponse:
    """
    Disarm the automation system.

    Disarming blocks all automated actions:
    - Victron signals are logged but not acted upon
    - Scheduled runs are skipped
    - No automatic start/stop of generator

    WARNING: If the generator is running when disarmed, it will NOT
    be stopped automatically. Use manual stop if needed.
    """
    result = await state_machine.disarm_automation(source=request.source)
    return ArmResponse(**result)


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

    # Try to get SSL info from nginx container
    try:
        import docker
        client = docker.from_env()

        # Find nginx container
        nginx_container = None
        for container in client.containers.list():
            if "genmaster_nginx" in container.name.lower():
                nginx_container = container
                break

        if nginx_container:
            # List certificate directories
            try:
                exit_code, output = nginx_container.exec_run(
                    "ls /etc/letsencrypt/live/",
                    demux=True
                )
                if exit_code == 0 and output[0]:
                    domains = output[0].decode("utf-8").strip().split("\n")
                    domains = [d for d in domains if d and not d.startswith("README")]

                    for domain in domains:
                        cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"

                        # Get certificate info using openssl
                        exit_code, cert_output = nginx_container.exec_run(
                            f"openssl x509 -in {cert_path} -noout -subject -issuer -dates -ext subjectAltName",
                            demux=True
                        )

                        if exit_code == 0 and cert_output[0]:
                            cert_str = cert_output[0].decode("utf-8")
                            cert_info = parse_cert_output(cert_str, domain, cert_path)
                            ssl_info["certificates"].append(cert_info)

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

    logger = logging.getLogger(__name__)
    result = {
        "enabled": False,
        "running": False,
        "healthy": False,
        "connector_id": None,
        "version": None,
        "error": None,
    }

    try:
        import docker
        client = docker.from_env()

        # Find cloudflared container
        try:
            container = client.containers.get("genmaster_cloudflared")
            result["enabled"] = True
            result["running"] = container.status == "running"

            if result["running"]:
                # Try to get tunnel info from logs
                try:
                    logs = container.logs(tail=50).decode("utf-8")
                    # Look for connection info in logs
                    for line in logs.split("\n"):
                        if "Connection" in line and "registered" in line:
                            result["healthy"] = True
                        if "Connector ID" in line or "connectorId" in line.lower():
                            # Extract connector ID from log line
                            import re
                            match = re.search(r'[a-f0-9-]{36}', line)
                            if match:
                                result["connector_id"] = match.group()
                except Exception:
                    pass

                # Get image version
                result["version"] = container.image.tags[0] if container.image.tags else None

        except docker.errors.NotFound:
            result["enabled"] = False

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
        "enabled": False,
        "running": False,
        "connected": False,
        "hostname": None,
        "ip_addresses": [],
        "version": None,
        "peers": [],
        "exit_node": None,
        "tailnet_name": None,
        "error": None,
    }

    try:
        import docker
        client = docker.from_env()

        # Find tailscale container
        try:
            container = client.containers.get("genmaster_tailscale")
            result["enabled"] = True
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
                        result["connected"] = status_data.get("BackendState") == "Running"

                        # Self info
                        self_info = status_data.get("Self", {})
                        result["hostname"] = self_info.get("HostName")
                        result["ip_addresses"] = self_info.get("TailscaleIPs", [])

                        # Tailnet name
                        result["tailnet_name"] = status_data.get("CurrentTailnet", {}).get("Name")

                        # Exit node info
                        if status_data.get("ExitNodeStatus"):
                            result["exit_node"] = status_data.get("ExitNodeStatus", {}).get("ID")

                        # Peer info
                        peers_data = status_data.get("Peer", {})
                        for peer_id, peer_info in peers_data.items():
                            peer = {
                                "id": peer_id,
                                "hostname": peer_info.get("HostName"),
                                "ip_addresses": peer_info.get("TailscaleIPs", []),
                                "online": peer_info.get("Online", False),
                                "os": peer_info.get("OS"),
                                "last_seen": peer_info.get("LastSeen"),
                                "is_exit_node": peer_info.get("ExitNode", False),
                                "rx_bytes": peer_info.get("RxBytes", 0),
                                "tx_bytes": peer_info.get("TxBytes", 0),
                            }
                            result["peers"].append(peer)

                        # Sort peers by online status then hostname
                        result["peers"].sort(key=lambda p: (not p["online"], p["hostname"] or ""))

                except Exception as e:
                    logger.debug(f"Failed to get tailscale status: {e}")

                # Get image version
                result["version"] = container.image.tags[0] if container.image.tags else None

        except docker.errors.NotFound:
            result["enabled"] = False

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

        for iface, addresses in addrs.items():
            if iface == "lo":
                continue

            iface_info = {
                "name": iface,
                "ipv4": None,
                "ipv6": None,
                "mac": None,
                "up": stats.get(iface, {}).isup if iface in stats else False,
            }

            for addr in addresses:
                if addr.family == socket.AF_INET:
                    iface_info["ipv4"] = addr.address
                elif addr.family == socket.AF_INET6:
                    if not addr.address.startswith("fe80"):  # Skip link-local
                        iface_info["ipv6"] = addr.address
                elif addr.family == psutil.AF_LINK:
                    iface_info["mac"] = addr.address

            if iface_info["ipv4"] or iface_info["ipv6"]:
                result["interfaces"].append(iface_info)

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
async def get_external_services_status() -> dict:
    """
    Get status of all external services (Cloudflare, Tailscale).
    """
    cloudflare = await get_cloudflare_status()
    tailscale = await get_tailscale_status()

    return {
        "cloudflare": cloudflare,
        "tailscale": tailscale,
    }
