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
