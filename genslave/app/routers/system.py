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
    netmask: Optional[str] = Field(None, description="Network mask")
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
    temperature_fahrenheit: Optional[float] = Field(
        None, description="CPU temperature in Fahrenheit"
    )
    uptime_seconds: int = Field(description="System uptime in seconds")
    ip_address: Optional[str] = Field(None, description="Primary IP address")
    default_gateway: Optional[str] = Field(None, description="Default gateway IP address")
    dns_servers: list[str] = Field(
        default_factory=list, description="DNS server IP addresses"
    )
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
    enabled: bool = Field(description="Whether notifications are enabled")


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


class NotificationEnableRequest(BaseModel):
    """Request to enable or disable notifications."""

    enabled: bool = Field(description="True to enable, False to disable notifications")


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

    # CPU usage - use interval=None for cached non-blocking value
    cpu_percent = psutil.cpu_percent(interval=None)
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
    temperature_f = None
    if temperature:
        temperature_f = round((temperature * 9 / 5) + 32, 1)
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
    default_gateway = _get_default_gateway()
    dns_servers = _get_dns_servers()

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
        temperature_fahrenheit=temperature_f,
        uptime_seconds=_get_uptime(),
        ip_address=primary_ip,
        default_gateway=default_gateway,
        dns_servers=dns_servers,
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


def _get_default_gateway() -> Optional[str]:
    """Get default gateway IP address."""
    try:
        # Read from /proc/net/route
        with open("/proc/net/route", "r") as f:
            for line in f.readlines()[1:]:  # Skip header
                parts = line.strip().split()
                if len(parts) >= 3:
                    # Default route has destination 00000000
                    if parts[1] == "00000000":
                        # Gateway is in hex, little-endian
                        gateway_hex = parts[2]
                        # Convert hex to IP (little-endian)
                        gateway_bytes = bytes.fromhex(gateway_hex)
                        gateway_ip = ".".join(str(b) for b in reversed(gateway_bytes))
                        return gateway_ip
    except Exception:
        pass

    # Fallback: try ip route command
    try:
        import subprocess
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Format: "default via 192.168.1.1 dev eth0"
            parts = result.stdout.strip().split()
            if len(parts) >= 3 and parts[0] == "default" and parts[1] == "via":
                return parts[2]
    except Exception:
        pass

    return None


def _get_dns_servers() -> list[str]:
    """Get DNS server IP addresses."""
    dns_servers = []

    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        dns_servers.append(parts[1])
    except Exception:
        pass

    return dns_servers


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
            netmask = None
            mac_address = None

            for addr in addrs:
                # IPv4 address
                if addr.family.name == "AF_INET":
                    ip_address = addr.address
                    netmask = addr.netmask
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
                    netmask=netmask,
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
    """Get WiFi information for an interface."""
    import subprocess

    info = {}

    # Try iwgetid for SSID (simpler and more reliable)
    try:
        result = subprocess.run(
            ["iwgetid", interface, "-r"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            info["ssid"] = result.stdout.strip()
    except Exception:
        pass

    # Try /proc/net/wireless for signal strength
    try:
        with open("/proc/net/wireless", "r") as f:
            for line in f.readlines()[2:]:  # Skip headers
                parts = line.split()
                if len(parts) >= 4:
                    iface = parts[0].rstrip(":")
                    if iface == interface:
                        # Signal level is in column 3 (can be dBm or relative)
                        signal_str = parts[3].rstrip(".")
                        signal_val = int(float(signal_str))
                        # If value is negative, it's dBm; if positive, convert
                        if signal_val > 0:
                            signal_dbm = signal_val - 256 if signal_val > 63 else signal_val - 100
                        else:
                            signal_dbm = signal_val
                        info["signal_dbm"] = signal_dbm
                        info["signal_percent"] = max(0, min(100, int((signal_dbm + 90) * 100 / 60)))
                        break
    except Exception:
        pass

    # Fallback: try iw command
    if "ssid" not in info or "signal_dbm" not in info:
        try:
            result = subprocess.run(
                ["iw", "dev", interface, "link"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if "SSID:" in line and "ssid" not in info:
                        info["ssid"] = line.split("SSID:")[1].strip()
                    elif "signal:" in line and "signal_dbm" not in info:
                        signal_str = line.split("signal:")[1].strip().split()[0]
                        signal_dbm = int(signal_str)
                        info["signal_dbm"] = signal_dbm
                        info["signal_percent"] = max(0, min(100, int((signal_dbm + 90) * 100 / 60)))
        except Exception:
            pass

    # Final fallback: iwconfig
    if "ssid" not in info or "signal_dbm" not in info:
        try:
            result = subprocess.run(
                ["iwconfig", interface],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                output = result.stdout
                if 'ESSID:"' in output and "ssid" not in info:
                    essid_start = output.index('ESSID:"') + 7
                    essid_end = output.index('"', essid_start)
                    info["ssid"] = output[essid_start:essid_end]
                if "Signal level=" in output and "signal_dbm" not in info:
                    signal_part = output.split("Signal level=")[1].split()[0]
                    if "dBm" in signal_part:
                        signal_dbm = int(signal_part.replace("dBm", ""))
                    else:
                        signal_dbm = int(signal_part.split("/")[0]) - 100
                    info["signal_dbm"] = signal_dbm
                    info["signal_percent"] = max(0, min(100, int((signal_dbm + 90) * 100 / 60)))
        except Exception:
            pass

    return info if info else None


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

    Returns the configured Apprise URLs (masked for security),
    whether notifications are configured, and whether they are enabled.
    """
    urls = notification_service.get_urls()
    masked_urls = [_mask_url(url) for url in urls]

    return NotificationConfig(
        apprise_urls=masked_urls,
        configured=len(urls) > 0,
        enabled=notification_service.is_enabled(),
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


@router.post("/notifications/enable", response_model=NotificationResponse)
async def set_notifications_enabled(
    request: NotificationEnableRequest,
) -> NotificationResponse:
    """
    Enable or disable notifications.

    When disabled, no notifications will be sent (except test notifications).
    This allows temporarily muting notifications without removing the configuration.
    """
    try:
        success = notification_service.set_enabled(request.enabled)

        if success:
            state = "enabled" if request.enabled else "disabled"
            logger.info(f"Notifications {state} via API")
            return NotificationResponse(
                success=True,
                message=f"Notifications {state}",
            )
        else:
            return NotificationResponse(
                success=False,
                message="Failed to update notification state",
            )

    except Exception as e:
        logger.error(f"Error setting notification state: {e}")
        return NotificationResponse(
            success=False,
            message=f"Error: {str(e)}",
        )
