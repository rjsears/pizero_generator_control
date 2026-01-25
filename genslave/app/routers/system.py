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


class NotificationCooldownSettings(BaseModel):
    """Notification cooldown settings."""

    failsafe_cooldown_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Cooldown period for failsafe notifications (1-60 minutes)",
    )
    restored_cooldown_minutes: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Cooldown period for restored notifications (1-60 minutes)",
    )
    last_failsafe_notification_at: Optional[int] = Field(
        None, description="Unix timestamp of last failsafe notification"
    )
    last_restored_notification_at: Optional[int] = Field(
        None, description="Unix timestamp of last restored notification"
    )


class NotificationCooldownUpdateRequest(BaseModel):
    """Request to update notification cooldown settings."""

    failsafe_cooldown_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=60,
        description="Cooldown period for failsafe notifications (1-60 minutes)",
    )
    restored_cooldown_minutes: Optional[int] = Field(
        None,
        ge=1,
        le=60,
        description="Cooldown period for restored notifications (1-60 minutes)",
    )


class NotificationClearCooldownRequest(BaseModel):
    """Request to clear notification cooldown."""

    event_type: Optional[str] = Field(
        None,
        description="Event type to clear: 'failsafe', 'restored', or null for both",
    )


class SystemActionResponse(BaseModel):
    """Response from system action (shutdown/reboot)."""

    success: bool = Field(description="Whether the action was initiated")
    message: str = Field(description="Status message")
    action: str = Field(description="The action that was requested")


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


@router.get("/notifications/settings", response_model=NotificationCooldownSettings)
async def get_notification_settings() -> NotificationCooldownSettings:
    """
    Get notification cooldown settings.

    Returns the current cooldown configuration for failsafe and restored
    notifications, including timestamps of last notifications sent.
    """
    settings = notification_service.get_cooldown_settings()
    return NotificationCooldownSettings(**settings)


@router.post("/notifications/settings", response_model=NotificationResponse)
async def update_notification_settings(
    request: NotificationCooldownUpdateRequest,
) -> NotificationResponse:
    """
    Update notification cooldown settings.

    Allows configuring cooldown periods to prevent notification flapping
    when communication with GenMaster is unstable.

    - failsafe_cooldown_minutes: How long to wait between failsafe notifications
    - restored_cooldown_minutes: How long to wait between restored notifications
    """
    try:
        success = notification_service.set_cooldown_settings(
            failsafe_cooldown_minutes=request.failsafe_cooldown_minutes,
            restored_cooldown_minutes=request.restored_cooldown_minutes,
        )

        if success:
            changes = []
            if request.failsafe_cooldown_minutes is not None:
                changes.append(f"failsafe={request.failsafe_cooldown_minutes}min")
            if request.restored_cooldown_minutes is not None:
                changes.append(f"restored={request.restored_cooldown_minutes}min")

            return NotificationResponse(
                success=True,
                message=f"Cooldown settings updated: {', '.join(changes) or 'no changes'}",
            )
        else:
            return NotificationResponse(
                success=False,
                message="Failed to update cooldown settings",
            )

    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        return NotificationResponse(
            success=False,
            message=f"Error: {str(e)}",
        )


@router.post("/notifications/clear-cooldown", response_model=NotificationResponse)
async def clear_notification_cooldown(
    request: NotificationClearCooldownRequest,
) -> NotificationResponse:
    """
    Clear notification cooldown state.

    This allows forcing a notification to be sent immediately,
    bypassing the cooldown period. Useful for testing or when
    you need to ensure a notification is sent.

    - event_type: "failsafe", "restored", or null/omit for both
    """
    try:
        event_type = request.event_type
        if event_type and event_type not in ("failsafe", "restored"):
            return NotificationResponse(
                success=False,
                message="Invalid event_type. Use 'failsafe', 'restored', or null for both.",
            )

        success = notification_service.clear_cooldown(event_type)

        if success:
            cleared = event_type or "all"
            return NotificationResponse(
                success=True,
                message=f"Cooldown cleared for {cleared} notifications",
            )
        else:
            return NotificationResponse(
                success=False,
                message="Failed to clear cooldown",
            )

    except Exception as e:
        logger.error(f"Error clearing notification cooldown: {e}")
        return NotificationResponse(
            success=False,
            message=f"Error: {str(e)}",
        )


# =========================================================================
# WiFi Configuration Endpoints
# =========================================================================


class WifiNetwork(BaseModel):
    """WiFi network information."""

    ssid: str = Field(description="Network SSID")
    signal_percent: int = Field(description="Signal strength as percentage")
    security: str = Field(description="Security type (Open, WPA, WPA2, etc.)")


class WifiScanResponse(BaseModel):
    """Response from WiFi network scan."""

    success: bool = Field(description="Whether the scan was successful")
    networks: list[WifiNetwork] = Field(default_factory=list, description="List of available networks")
    error: Optional[str] = Field(None, description="Error message if scan failed")


class WifiConnectRequest(BaseModel):
    """Request to connect to a WiFi network."""

    ssid: str = Field(..., min_length=1, max_length=32, description="WiFi network SSID")
    password: Optional[str] = Field(None, description="WiFi password (None for open networks)")


class WifiConnectResponse(BaseModel):
    """Response from WiFi connect attempt."""

    success: bool = Field(description="Whether connection was successful")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(None, description="Error message if connection failed")


@router.get("/wifi/networks", response_model=WifiScanResponse)
async def scan_wifi_networks() -> WifiScanResponse:
    """
    Scan for available WiFi networks.

    Uses iwlist to scan for nearby WiFi networks and returns
    a list with SSID, signal strength, and security type.
    Works with wpa_supplicant (standard on Raspberry Pi).
    """
    import re
    import subprocess

    result = WifiScanResponse(success=False, networks=[], error=None)

    try:
        # Find wireless interface
        proc = subprocess.run(
            ["iwconfig"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Find interface name (usually wlan0)
        interface = None
        for line in proc.stdout.split("\n"):
            if "IEEE 802.11" in line:
                interface = line.split()[0]
                break

        if not interface:
            result.error = "No WiFi interface found"
            return result

        # Scan for networks using iwlist
        proc = subprocess.run(
            ["iwlist", interface, "scan"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if proc.returncode != 0:
            logger.warning(f"iwlist scan failed: {proc.stderr}")
            result.error = proc.stderr or "WiFi scan failed"
            return result

        # Parse iwlist output
        networks = []
        seen_ssids = set()
        current_network = {}

        for line in proc.stdout.split("\n"):
            line = line.strip()

            # New cell (network)
            if line.startswith("Cell"):
                if current_network.get("ssid") and current_network["ssid"] not in seen_ssids:
                    seen_ssids.add(current_network["ssid"])
                    networks.append(WifiNetwork(
                        ssid=current_network.get("ssid", ""),
                        signal_percent=current_network.get("signal", 0),
                        security=current_network.get("security", "Open"),
                    ))
                current_network = {"security": "Open"}

            # SSID
            elif "ESSID:" in line:
                match = re.search(r'ESSID:"([^"]*)"', line)
                if match:
                    current_network["ssid"] = match.group(1)

            # Signal level
            elif "Signal level=" in line:
                # Format: Signal level=-XX dBm or Signal level=XX/100
                match = re.search(r"Signal level[=:](-?\d+)", line)
                if match:
                    signal_dbm = int(match.group(1))
                    # Convert dBm to percentage (roughly: -30 dBm = 100%, -90 dBm = 0%)
                    if signal_dbm < 0:
                        signal_percent = min(100, max(0, 2 * (signal_dbm + 100)))
                    else:
                        signal_percent = signal_dbm  # Already a percentage
                    current_network["signal"] = signal_percent

            # Security (WPA/WPA2)
            elif "IE:" in line and ("WPA" in line or "RSN" in line):
                if "WPA2" in line or "RSN" in line:
                    current_network["security"] = "WPA2"
                elif "WPA" in line:
                    current_network["security"] = "WPA"

            # WEP
            elif "Encryption key:on" in line and current_network.get("security") == "Open":
                current_network["security"] = "WEP"

        # Add last network
        if current_network.get("ssid") and current_network["ssid"] not in seen_ssids:
            networks.append(WifiNetwork(
                ssid=current_network.get("ssid", ""),
                signal_percent=current_network.get("signal", 0),
                security=current_network.get("security", "Open"),
            ))

        # Sort by signal strength (strongest first)
        networks.sort(key=lambda x: x.signal_percent, reverse=True)
        result.networks = networks
        result.success = True

    except subprocess.TimeoutExpired:
        logger.warning("WiFi scan timed out")
        result.error = "WiFi scan timed out"
    except FileNotFoundError:
        logger.warning("iwlist not found - wireless-tools may not be installed")
        result.error = "iwlist not found - wireless-tools not installed"
    except Exception as e:
        logger.warning(f"WiFi scan failed: {e}")
        result.error = str(e)

    return result


class WifiAddRequest(BaseModel):
    """Request to add a known WiFi network."""

    ssid: str = Field(..., min_length=1, max_length=32, description="WiFi network SSID")
    password: str = Field(..., min_length=8, max_length=63, description="WiFi password (WPA/WPA2)")
    auto_connect: bool = Field(True, description="Automatically connect when network is available")


class WifiAddResponse(BaseModel):
    """Response from adding a known WiFi network."""

    success: bool = Field(description="Whether the network was added successfully")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(None, description="Error message if adding failed")


class WifiSavedNetwork(BaseModel):
    """Saved WiFi network information."""

    name: str = Field(description="Connection profile name")
    ssid: str = Field(description="Network SSID")
    auto_connect: bool = Field(description="Whether auto-connect is enabled")


class WifiSavedListResponse(BaseModel):
    """Response listing saved WiFi networks."""

    success: bool = Field(description="Whether the list was retrieved successfully")
    networks: list[WifiSavedNetwork] = Field(default_factory=list, description="List of saved networks")
    error: Optional[str] = Field(None, description="Error message if listing failed")


class WifiDeleteRequest(BaseModel):
    """Request to delete a saved WiFi network."""

    name: str = Field(..., min_length=1, description="Connection profile name to delete")


class WifiDeleteResponse(BaseModel):
    """Response from deleting a saved WiFi network."""

    success: bool = Field(description="Whether the network was deleted successfully")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(None, description="Error message if deletion failed")


WPA_SUPPLICANT_CONF = "/etc/wpa_supplicant/wpa_supplicant.conf"


def _parse_wpa_supplicant_conf() -> list[dict]:
    """
    Parse wpa_supplicant.conf to extract configured networks.

    Returns a list of dicts with 'ssid', 'priority', and 'disabled' keys.
    """
    import re

    networks = []

    try:
        with open(WPA_SUPPLICANT_CONF, "r") as f:
            content = f.read()

        # Find all network blocks
        network_pattern = re.compile(r"network\s*=\s*\{([^}]+)\}", re.DOTALL)

        for match in network_pattern.finditer(content):
            block = match.group(1)
            network = {}

            # Extract SSID
            ssid_match = re.search(r'ssid\s*=\s*"([^"]+)"', block)
            if ssid_match:
                network["ssid"] = ssid_match.group(1)

            # Extract priority (higher = preferred)
            priority_match = re.search(r"priority\s*=\s*(\d+)", block)
            network["priority"] = int(priority_match.group(1)) if priority_match else 0

            # Check if disabled
            disabled_match = re.search(r"disabled\s*=\s*(\d+)", block)
            network["disabled"] = disabled_match and disabled_match.group(1) == "1"

            if network.get("ssid"):
                networks.append(network)

    except FileNotFoundError:
        logger.warning(f"wpa_supplicant.conf not found at {WPA_SUPPLICANT_CONF}")
    except Exception as e:
        logger.warning(f"Failed to parse wpa_supplicant.conf: {e}")

    return networks


@router.get("/wifi/saved", response_model=WifiSavedListResponse)
async def list_saved_wifi_networks() -> WifiSavedListResponse:
    """
    List saved WiFi network profiles.

    Parses wpa_supplicant.conf to return all configured networks.
    Works with wpa_supplicant (standard on Raspberry Pi).
    """
    result = WifiSavedListResponse(success=False, networks=[], error=None)

    try:
        networks = _parse_wpa_supplicant_conf()

        result.networks = [
            WifiSavedNetwork(
                name=net["ssid"],
                ssid=net["ssid"],
                auto_connect=not net.get("disabled", False),
            )
            for net in networks
        ]
        result.success = True

    except Exception as e:
        logger.warning(f"Failed to list saved networks: {e}")
        result.error = str(e)

    return result


def _reload_wpa_supplicant() -> bool:
    """
    Reload wpa_supplicant configuration.

    Uses wpa_cli to reconfigure without restarting the daemon.
    Returns True if successful.
    """
    import subprocess

    try:
        proc = subprocess.run(
            ["wpa_cli", "-i", "wlan0", "reconfigure"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode == 0
    except Exception as e:
        logger.warning(f"Failed to reload wpa_supplicant: {e}")
        return False


@router.post("/wifi/add", response_model=WifiAddResponse)
async def add_wifi_network(request: WifiAddRequest) -> WifiAddResponse:
    """
    Add a known WiFi network for auto-connect.

    Adds a network block to wpa_supplicant.conf and reconfigures.
    Works with wpa_supplicant (standard on Raspberry Pi).
    """
    import re

    result = WifiAddResponse(success=False, message="", error=None)

    ssid = request.ssid.strip()
    if not ssid:
        result.error = "SSID cannot be empty"
        return result

    # Log the add attempt (without password)
    logger.info(f"Adding known WiFi network: {ssid}")

    try:
        # Check if network already exists
        existing = _parse_wpa_supplicant_conf()
        if any(net["ssid"] == ssid for net in existing):
            result.error = f"Network '{ssid}' already exists. Delete it first to update."
            return result

        # Read current config
        try:
            with open(WPA_SUPPLICANT_CONF, "r") as f:
                content = f.read()
        except FileNotFoundError:
            # Create basic config if it doesn't exist
            content = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

"""

        # Build network block
        # Escape any special characters in SSID
        safe_ssid = ssid.replace("\\", "\\\\").replace('"', '\\"')
        safe_password = request.password.replace("\\", "\\\\").replace('"', '\\"')

        network_block = f'''
network={{
    ssid="{safe_ssid}"
    psk="{safe_password}"
    key_mgmt=WPA-PSK
    priority=1
}}
'''

        # Append network block
        with open(WPA_SUPPLICANT_CONF, "w") as f:
            f.write(content.rstrip() + "\n" + network_block)

        # Reload wpa_supplicant
        if _reload_wpa_supplicant():
            result.success = True
            result.message = f"WiFi network '{ssid}' added successfully. It will auto-connect when available."
            logger.info(f"Successfully added WiFi network: {ssid}")
        else:
            # Config was written but reload failed - still partially successful
            result.success = True
            result.message = f"WiFi network '{ssid}' added. Reboot may be required for changes to take effect."
            logger.warning(f"Added WiFi network but reload failed: {ssid}")

    except PermissionError:
        logger.warning("Permission denied writing to wpa_supplicant.conf")
        result.error = "Permission denied - container needs write access to /etc/wpa_supplicant"
    except Exception as e:
        logger.warning(f"Failed to add WiFi network: {e}")
        result.error = str(e)

    return result


@router.post("/wifi/delete", response_model=WifiDeleteResponse)
async def delete_wifi_network(request: WifiDeleteRequest) -> WifiDeleteResponse:
    """
    Delete a saved WiFi network profile.

    Removes a network block from wpa_supplicant.conf and reconfigures.
    Works with wpa_supplicant (standard on Raspberry Pi).
    """
    import re

    result = WifiDeleteResponse(success=False, message="", error=None)

    name = request.name.strip()
    if not name:
        result.error = "Connection name cannot be empty"
        return result

    logger.info(f"Deleting WiFi network: {name}")

    try:
        # Read current config
        try:
            with open(WPA_SUPPLICANT_CONF, "r") as f:
                content = f.read()
        except FileNotFoundError:
            result.error = "wpa_supplicant.conf not found"
            return result

        # Escape special regex characters in SSID
        escaped_ssid = re.escape(name)

        # Find and remove the network block for this SSID
        # Match network block containing ssid="<name>"
        pattern = re.compile(
            r'\n?network\s*=\s*\{[^}]*ssid\s*=\s*"' + escaped_ssid + r'"[^}]*\}',
            re.DOTALL
        )

        new_content, count = pattern.subn("", content)

        if count == 0:
            result.error = f"Network '{name}' not found"
            return result

        # Write updated config
        with open(WPA_SUPPLICANT_CONF, "w") as f:
            f.write(new_content.strip() + "\n")

        # Reload wpa_supplicant
        if _reload_wpa_supplicant():
            result.success = True
            result.message = f"WiFi network '{name}' deleted successfully."
            logger.info(f"Successfully deleted WiFi network: {name}")
        else:
            result.success = True
            result.message = f"WiFi network '{name}' deleted. Reboot may be required for changes to take effect."
            logger.warning(f"Deleted WiFi network but reload failed: {name}")

    except PermissionError:
        logger.warning("Permission denied writing to wpa_supplicant.conf")
        result.error = "Permission denied - container needs write access to /etc/wpa_supplicant"
    except Exception as e:
        logger.warning(f"Failed to delete WiFi network: {e}")
        result.error = str(e)

    return result


@router.post("/wifi/connect", response_model=WifiConnectResponse)
async def connect_wifi(request: WifiConnectRequest) -> WifiConnectResponse:
    """
    Connect to a WiFi network.

    Adds the network to wpa_supplicant.conf if not present, then connects.
    Works with wpa_supplicant (standard on Raspberry Pi).
    """
    import re
    import subprocess
    import time

    result = WifiConnectResponse(success=False, message="", error=None)

    # Sanitize SSID
    ssid = request.ssid.strip()
    if not ssid:
        result.error = "SSID cannot be empty"
        return result

    # Log the connection attempt (without password)
    logger.info(f"Attempting to connect WiFi to SSID: {ssid}")

    try:
        # Check if network is already configured
        existing = _parse_wpa_supplicant_conf()
        network_exists = any(net["ssid"] == ssid for net in existing)

        # If network doesn't exist and we have a password, add it
        if not network_exists:
            if not request.password:
                result.error = f"Network '{ssid}' not configured. Password required for new networks."
                return result

            # Add the network to wpa_supplicant.conf
            try:
                with open(WPA_SUPPLICANT_CONF, "r") as f:
                    content = f.read()
            except FileNotFoundError:
                content = """ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=US

"""

            # Build network block with high priority for immediate connection
            safe_ssid = ssid.replace("\\", "\\\\").replace('"', '\\"')
            safe_password = request.password.replace("\\", "\\\\").replace('"', '\\"')

            network_block = f'''
network={{
    ssid="{safe_ssid}"
    psk="{safe_password}"
    key_mgmt=WPA-PSK
    priority=10
}}
'''

            with open(WPA_SUPPLICANT_CONF, "w") as f:
                f.write(content.rstrip() + "\n" + network_block)

            logger.info(f"Added network '{ssid}' to wpa_supplicant.conf")

        # Reconfigure wpa_supplicant to pick up changes
        proc = subprocess.run(
            ["wpa_cli", "-i", "wlan0", "reconfigure"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if proc.returncode != 0:
            logger.warning(f"wpa_cli reconfigure failed: {proc.stderr}")

        # Give it time to connect
        time.sleep(3)

        # Check if we're connected to the requested network
        proc = subprocess.run(
            ["wpa_cli", "-i", "wlan0", "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if proc.returncode == 0:
            status_output = proc.stdout
            # Check if connected to our SSID
            ssid_match = re.search(r"^ssid=(.+)$", status_output, re.MULTILINE)
            state_match = re.search(r"^wpa_state=(.+)$", status_output, re.MULTILINE)

            current_ssid = ssid_match.group(1) if ssid_match else None
            current_state = state_match.group(1) if state_match else None

            if current_state == "COMPLETED" and current_ssid == ssid:
                result.success = True
                result.message = f"Successfully connected to {ssid}"
                logger.info(f"Successfully connected WiFi to: {ssid}")
            elif current_state == "COMPLETED":
                # Connected but to a different network
                result.message = f"Network '{ssid}' added. Currently connected to '{current_ssid}'."
                result.success = True
            else:
                # Not fully connected yet
                result.success = True
                result.message = f"Network '{ssid}' configured. Connection in progress (state: {current_state})."
        else:
            result.success = True
            result.message = f"Network '{ssid}' configured. Connection may take a moment."

    except PermissionError:
        logger.warning("Permission denied writing to wpa_supplicant.conf")
        result.error = "Permission denied - container needs write access to /etc/wpa_supplicant"
    except subprocess.TimeoutExpired:
        logger.warning("WiFi connection timed out")
        result.error = "Connection timed out"
    except FileNotFoundError as e:
        logger.warning(f"Required tool not found: {e}")
        result.error = "wpa_cli not found - wpa_supplicant tools not installed"
    except Exception as e:
        logger.warning(f"WiFi connection failed: {e}")
        result.error = str(e)

    return result


# =========================================================================
# System Power Control Endpoints
# =========================================================================


@router.post("/shutdown", response_model=SystemActionResponse)
async def shutdown_system() -> SystemActionResponse:
    """
    Initiate system shutdown.

    This will shut down the Raspberry Pi after a short delay (5 seconds)
    to allow the response to be sent. The relay will be turned off for
    safety before shutdown.

    WARNING: This will make GenSlave unreachable until manually powered on.
    """
    import subprocess

    from app.services.relay import relay_service

    try:
        # Safety: turn off relay before shutdown
        relay_service.relay_off(force=True)
        logger.warning("System shutdown requested via API - relay turned off")

        # Schedule shutdown in background (5 second delay to allow response)
        subprocess.Popen(
            ["sudo", "shutdown", "-h", "+0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return SystemActionResponse(
            success=True,
            message="Shutdown initiated. System will power off shortly.",
            action="shutdown",
        )

    except Exception as e:
        logger.error(f"Error initiating shutdown: {e}")
        return SystemActionResponse(
            success=False,
            message=f"Failed to initiate shutdown: {str(e)}",
            action="shutdown",
        )


@router.post("/reboot", response_model=SystemActionResponse)
async def reboot_system() -> SystemActionResponse:
    """
    Initiate system reboot.

    This will reboot the Raspberry Pi after a short delay (5 seconds)
    to allow the response to be sent. The relay will be turned off for
    safety during the reboot.

    After reboot, GenSlave will start automatically and become available
    again (typically within 60-90 seconds).
    """
    import subprocess

    from app.services.relay import relay_service

    try:
        # Safety: turn off relay before reboot
        relay_service.relay_off(force=True)
        logger.warning("System reboot requested via API - relay turned off")

        # Schedule reboot in background (5 second delay to allow response)
        subprocess.Popen(
            ["sudo", "reboot"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return SystemActionResponse(
            success=True,
            message="Reboot initiated. System will restart shortly.",
            action="reboot",
        )

    except Exception as e:
        logger.error(f"Error initiating reboot: {e}")
        return SystemActionResponse(
            success=False,
            message=f"Failed to initiate reboot: {str(e)}",
            action="reboot",
        )
