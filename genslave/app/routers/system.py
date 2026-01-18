# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genslave/app/routers/system.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 16th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""System information API endpoints."""

import logging
import os
import platform
from typing import Literal, Optional

import psutil
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings
from app.services.database import db_service
from app.services.notification import notification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


# =========================================================================
# Schemas
# =========================================================================


class NetworkInfo(BaseModel):
    """Network interface information."""

    interface: str = Field(description="Interface name")
    ip_address: Optional[str] = Field(None, description="IP address")
    mac_address: Optional[str] = Field(None, description="MAC address")
    is_wifi: bool = Field(default=False, description="Whether this is a WiFi interface")
    wifi_ssid: Optional[str] = Field(None, description="Connected WiFi SSID")
    wifi_signal_dbm: Optional[int] = Field(None, description="WiFi signal strength in dBm")
    wifi_signal_percent: Optional[int] = Field(
        None, description="WiFi signal strength as percentage"
    )


class SystemInfo(BaseModel):
    """System information and resource usage."""

    hostname: str = Field(description="System hostname")
    platform: str = Field(description="Platform identifier")
    cpu_percent: float = Field(description="CPU usage percentage")
    ram_total_mb: int = Field(description="Total RAM in MB")
    ram_used_mb: int = Field(description="Used RAM in MB")
    ram_available_mb: int = Field(description="Available RAM in MB")
    ram_percent: float = Field(description="RAM usage percentage")
    disk_total_gb: float = Field(description="Total disk space in GB")
    disk_used_gb: float = Field(description="Used disk space in GB")
    disk_free_gb: float = Field(description="Free disk space in GB")
    disk_percent: float = Field(description="Disk usage percentage")
    temperature_celsius: Optional[float] = Field(
        None, description="CPU temperature in Celsius"
    )
    uptime_seconds: int = Field(description="System uptime in seconds")
    ip_address: Optional[str] = Field(None, description="Primary IP address")
    network_interfaces: list[NetworkInfo] = Field(
        default_factory=list, description="Network interface details"
    )
    status: Literal["healthy", "warning", "critical"] = Field(
        description="Overall health status"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of warning messages"
    )


class ConfigUpdate(BaseModel):
    """Configuration update from GenMaster."""

    failsafe_timeout_seconds: Optional[int] = Field(
        None, description="New failsafe timeout"
    )
    webhook_url: Optional[str] = Field(None, description="Backup webhook URL")
    webhook_secret: Optional[str] = Field(None, description="Webhook secret")


class ConfigResponse(BaseModel):
    """Response from config update."""

    success: bool = Field(description="Whether update was successful")
    message: str = Field(description="Status message")


class RotateKeyRequest(BaseModel):
    """Request to rotate the API secret key."""

    new_key: str = Field(
        min_length=16,
        max_length=128,
        description="The new API secret key (minimum 16 characters)",
    )


class RotateKeyResponse(BaseModel):
    """Response from API key rotation."""

    success: bool = Field(description="Whether the rotation was successful")
    message: str = Field(description="Status message")


class NotificationConfig(BaseModel):
    """Current notification configuration."""

    apprise_urls: list[str] = Field(
        default_factory=list,
        description="List of Apprise notification URLs (masked for security)",
    )
    configured: bool = Field(description="Whether any notification URLs are configured")


class NotificationUpdateRequest(BaseModel):
    """Request to update notification configuration."""

    apprise_urls: list[str] = Field(
        description="List of Apprise notification URLs",
    )


class NotificationResponse(BaseModel):
    """Response from notification operations."""

    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Status message")


class NotificationTestResponse(BaseModel):
    """Response from test notification."""

    success: bool = Field(description="Whether the test notification was sent")
    message: str = Field(description="Status message")
    configured_services: int = Field(description="Number of configured notification services")


# =========================================================================
# Endpoints
# =========================================================================


@router.get("", response_model=SystemInfo)
async def get_system_info() -> SystemInfo:
    """
    Get system information and resource usage.

    Returns CPU, RAM, disk, temperature, and overall health status.
    """
    warnings = []
    status = "healthy"

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    if cpu_percent > 90:
        warnings.append(f"CPU usage critical: {cpu_percent}%")
        status = "critical"
    elif cpu_percent > 80:
        warnings.append(f"CPU usage high: {cpu_percent}%")
        if status != "critical":
            status = "warning"

    # Memory usage
    memory = psutil.virtual_memory()
    ram_percent = memory.percent
    if ram_percent > 90:
        warnings.append(f"Memory usage critical: {ram_percent}%")
        status = "critical"
    elif ram_percent > 80:
        warnings.append(f"Memory usage high: {ram_percent}%")
        if status != "critical":
            status = "warning"

    # Disk usage
    disk = psutil.disk_usage("/")
    disk_percent = disk.percent
    if disk_percent > 95:
        warnings.append(f"Disk usage critical: {disk_percent}%")
        status = "critical"
    elif disk_percent > 85:
        warnings.append(f"Disk usage high: {disk_percent}%")
        if status != "critical":
            status = "warning"

    # Temperature
    temperature = _get_cpu_temperature()
    if temperature:
        if temperature > 80:
            warnings.append(f"Temperature critical: {temperature}°C")
            status = "critical"
        elif temperature > 70:
            warnings.append(f"Temperature high: {temperature}°C")
            if status != "critical":
                status = "warning"

    # Network info
    network_interfaces = _get_network_interfaces()
    primary_ip = _get_primary_ip(network_interfaces)

    return SystemInfo(
        hostname=platform.node(),
        platform=platform.system().lower(),
        cpu_percent=cpu_percent,
        ram_total_mb=int(memory.total / (1024 * 1024)),
        ram_used_mb=int(memory.used / (1024 * 1024)),
        ram_available_mb=int(memory.available / (1024 * 1024)),
        ram_percent=ram_percent,
        disk_total_gb=round(disk.total / (1024**3), 1),
        disk_used_gb=round(disk.used / (1024**3), 1),
        disk_free_gb=round(disk.free / (1024**3), 1),
        disk_percent=disk_percent,
        temperature_celsius=temperature,
        uptime_seconds=_get_uptime(),
        ip_address=primary_ip,
        network_interfaces=network_interfaces,
        status=status,
        warnings=warnings,
    )


@router.post("/config", response_model=ConfigResponse)
async def update_config(config: ConfigUpdate) -> ConfigResponse:
    """
    Receive configuration push from GenMaster.

    Allows GenMaster to update certain settings on GenSlave.
    Note: Changes are applied in memory only, not persisted.
    """
    changes = []

    if config.failsafe_timeout_seconds is not None:
        # Update in memory (would need to restart for full effect)
        settings.FAILSAFE_TIMEOUT_SECONDS = config.failsafe_timeout_seconds
        changes.append(f"failsafe_timeout={config.failsafe_timeout_seconds}")

    if config.webhook_url is not None:
        settings.WEBHOOK_URL = config.webhook_url
        changes.append("webhook_url updated")

    if config.webhook_secret is not None:
        settings.WEBHOOK_SECRET = config.webhook_secret
        changes.append("webhook_secret updated")

    if changes:
        logger.info(f"Config updated: {', '.join(changes)}")
        return ConfigResponse(
            success=True,
            message=f"Updated: {', '.join(changes)}",
        )
    else:
        return ConfigResponse(
            success=True,
            message="No changes to apply",
        )


def _get_cpu_temperature() -> Optional[float]:
    """Get CPU temperature on Raspberry Pi."""
    # Try vcgencmd first (Raspberry Pi specific)
    try:
        temp_output = os.popen("vcgencmd measure_temp 2>/dev/null").read()
        if temp_output:
            # Format: "temp=45.0'C"
            temp_str = temp_output.replace("temp=", "").replace("'C", "").strip()
            return float(temp_str)
    except Exception:
        pass

    # Try thermal zone (generic Linux)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        pass

    return None


def _get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        with open("/proc/uptime", "r") as f:
            return int(float(f.read().split()[0]))
    except Exception:
        return 0


def _get_network_interfaces() -> list[NetworkInfo]:
    """Get network interface information including WiFi signal strength."""
    interfaces = []

    try:
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()

        for iface_name, addrs in net_if_addrs.items():
            # Skip loopback and down interfaces
            if iface_name == "lo":
                continue

            stats = net_if_stats.get(iface_name)
            if stats and not stats.isup:
                continue

            ip_address = None
            mac_address = None

            for addr in addrs:
                # IPv4 address
                if addr.family.name == "AF_INET":
                    ip_address = addr.address
                # MAC address
                elif addr.family.name == "AF_PACKET":
                    mac_address = addr.address

            # Check if this is a WiFi interface
            is_wifi = iface_name.startswith(("wlan", "wlp", "wifi"))
            wifi_ssid = None
            wifi_signal_dbm = None
            wifi_signal_percent = None

            if is_wifi and ip_address:
                wifi_info = _get_wifi_info(iface_name)
                if wifi_info:
                    wifi_ssid = wifi_info.get("ssid")
                    wifi_signal_dbm = wifi_info.get("signal_dbm")
                    wifi_signal_percent = wifi_info.get("signal_percent")

            interfaces.append(
                NetworkInfo(
                    interface=iface_name,
                    ip_address=ip_address,
                    mac_address=mac_address,
                    is_wifi=is_wifi,
                    wifi_ssid=wifi_ssid,
                    wifi_signal_dbm=wifi_signal_dbm,
                    wifi_signal_percent=wifi_signal_percent,
                )
            )
    except Exception as e:
        logger.warning(f"Failed to get network interfaces: {e}")

    return interfaces


def _get_wifi_info(interface: str) -> Optional[dict]:
    """Get WiFi information for an interface using iwconfig/iw."""
    try:
        # Try iw first (more modern)
        import subprocess

        result = subprocess.run(
            ["iw", "dev", interface, "link"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            output = result.stdout
            info = {}

            # Parse SSID
            for line in output.split("\n"):
                if "SSID:" in line:
                    info["ssid"] = line.split("SSID:")[1].strip()
                elif "signal:" in line:
                    # Format: "signal: -45 dBm"
                    signal_str = line.split("signal:")[1].strip().split()[0]
                    signal_dbm = int(signal_str)
                    info["signal_dbm"] = signal_dbm
                    # Convert dBm to percentage (rough approximation)
                    # -30 dBm = 100%, -90 dBm = 0%
                    info["signal_percent"] = max(
                        0, min(100, int((signal_dbm + 90) * 100 / 60))
                    )

            if info:
                return info

    except Exception:
        pass

    # Fallback to iwconfig
    try:
        import subprocess

        result = subprocess.run(
            ["iwconfig", interface],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            output = result.stdout
            info = {}

            # Parse ESSID
            if 'ESSID:"' in output:
                essid_start = output.index('ESSID:"') + 7
                essid_end = output.index('"', essid_start)
                info["ssid"] = output[essid_start:essid_end]

            # Parse signal level
            if "Signal level=" in output:
                signal_part = output.split("Signal level=")[1].split()[0]
                if "dBm" in signal_part:
                    signal_dbm = int(signal_part.replace("dBm", ""))
                else:
                    # Some drivers report as ratio (e.g., 70/100)
                    signal_dbm = int(signal_part.split("/")[0]) - 100
                info["signal_dbm"] = signal_dbm
                info["signal_percent"] = max(
                    0, min(100, int((signal_dbm + 90) * 100 / 60))
                )

            if info:
                return info

    except Exception:
        pass

    return None


def _get_primary_ip(interfaces: list[NetworkInfo]) -> Optional[str]:
    """Get the primary IP address from interfaces."""
    # Prefer WiFi, then ethernet
    for iface in interfaces:
        if iface.is_wifi and iface.ip_address:
            return iface.ip_address

    for iface in interfaces:
        if iface.ip_address and not iface.interface.startswith(("docker", "br-", "veth")):
            return iface.ip_address

    return None


# =========================================================================
# API Key Management Endpoints
# =========================================================================


@router.post("/rotate-key", response_model=RotateKeyResponse)
async def rotate_api_key(request: RotateKeyRequest) -> RotateKeyResponse:
    """
    Rotate the API secret key.

    This endpoint allows GenMaster to remotely update the API secret key
    on GenSlave. The request must be authenticated with the current valid
    API key.

    The new key is stored in the database and takes effect immediately -
    no container restart is required. Subsequent API calls must use the
    new key.

    Note: GenMaster should update its own configuration first, then call
    this endpoint. If this call succeeds, GenMaster should immediately
    start using the new key.
    """
    try:
        # Update the API secret in the database
        success = db_service.set_api_secret(request.new_key)

        if success:
            logger.info("API key rotated successfully via API call")
            return RotateKeyResponse(
                success=True,
                message="API key rotated successfully. New key is now active.",
            )
        else:
            logger.error("Failed to rotate API key - database update failed")
            return RotateKeyResponse(
                success=False,
                message="Failed to update API key in database",
            )

    except Exception as e:
        logger.error(f"Error rotating API key: {e}")
        return RotateKeyResponse(
            success=False,
            message=f"Error rotating API key: {str(e)}",
        )


# =========================================================================
# Notification Endpoints
# =========================================================================


def _mask_url(url: str) -> str:
    """Mask sensitive parts of an Apprise URL for display.

    Shows the service type but hides tokens/credentials.
    Example: tgram://123456:ABC...XYZ/chatid -> tgram://****/chatid
    """
    if "://" not in url:
        return "****"

    scheme, rest = url.split("://", 1)

    # For most services, mask everything after ://
    if "/" in rest:
        parts = rest.split("/", 1)
        return f"{scheme}://****/{ parts[1][:10]}..." if len(parts[1]) > 10 else f"{scheme}://****/{parts[1]}"
    else:
        return f"{scheme}://****"


@router.get("/notifications", response_model=NotificationConfig)
async def get_notifications() -> NotificationConfig:
    """
    Get current notification configuration.

    Returns the configured Apprise URLs (masked for security) and
    whether notifications are configured.
    """
    urls = notification_service.get_urls()
    masked_urls = [_mask_url(url) for url in urls]

    return NotificationConfig(
        apprise_urls=masked_urls,
        configured=len(urls) > 0,
    )


@router.post("/notifications", response_model=NotificationResponse)
async def update_notifications(
    request: NotificationUpdateRequest,
) -> NotificationResponse:
    """
    Update notification configuration.

    Accepts a list of Apprise URLs. Supports 80+ notification services:
    - Telegram: tgram://bottoken/chatid
    - Slack: slack://tokenA/tokenB/tokenC/channel
    - Discord: discord://webhook_id/webhook_token
    - Twilio: twilio://account_sid:auth_token@from_phone/to_phone
    - Pushover: pover://user_key@api_token
    - Email: mailto://user:pass@gmail.com
    - And many more: https://github.com/caronc/apprise/wiki

    The configuration is stored in the database and takes effect immediately.
    """
    try:
        success = notification_service.set_urls(request.apprise_urls)

        if success:
            url_count = len([u for u in request.apprise_urls if u.strip()])
            logger.info(f"Notification config updated: {url_count} URLs configured")
            return NotificationResponse(
                success=True,
                message=f"Notification configuration updated. {url_count} service(s) configured.",
            )
        else:
            return NotificationResponse(
                success=False,
                message="Failed to update notification configuration",
            )

    except Exception as e:
        logger.error(f"Error updating notifications: {e}")
        return NotificationResponse(
            success=False,
            message=f"Error updating notifications: {str(e)}",
        )


@router.post("/notifications/test", response_model=NotificationTestResponse)
async def test_notification() -> NotificationTestResponse:
    """
    Send a test notification.

    Sends a test message to all configured notification services.
    Use this to verify your notification configuration is working.
    """
    urls = notification_service.get_urls()

    if not urls:
        return NotificationTestResponse(
            success=False,
            message="No notification services configured",
            configured_services=0,
        )

    try:
        success = await notification_service.send_test()

        if success:
            return NotificationTestResponse(
                success=True,
                message="Test notification sent successfully",
                configured_services=len(urls),
            )
        else:
            return NotificationTestResponse(
                success=False,
                message="Test notification may have failed - check your service configuration",
                configured_services=len(urls),
            )

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        return NotificationTestResponse(
            success=False,
            message=f"Error sending test notification: {str(e)}",
            configured_services=len(urls),
        )
