# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/network_check.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - May 11th, 2026
#
# Subnet compatibility check for cross-device WiFi configuration.
# When the user assigns a static IP to GenMaster or GenSlave, this
# checks whether the other device will still be reachable on the
# local network. Tailscale links (100.64.0.0/10) are exempt from
# the check since they tunnel regardless of LAN topology.
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Cross-device subnet compatibility check for static-IP wifi configuration."""

from __future__ import annotations

import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Tailscale's CGNAT range. Any "other device" reachable in this range is
# assumed to be using the Tailscale tunnel, so subnet matching of the local
# WiFi is irrelevant.
TAILSCALE_CGNAT = ipaddress.IPv4Network("100.64.0.0/10")

WARNING_SUBNET_MISMATCH = "subnet_mismatch"
WARNING_COULD_NOT_VERIFY = "could_not_verify_subnet"


@dataclass
class NetworkCheckWarning:
    """A warning surfaced when subnet compatibility cannot be confirmed."""

    warning_code: str
    message: str
    proposed_ip: str
    proposed_network: str
    other_device_label: str
    other_device_ip: Optional[str] = None
    other_device_network: Optional[str] = None
    resolved_from: Optional[str] = None

    def to_dict(self) -> dict:
        out = {
            "warning_code": self.warning_code,
            "message": self.message,
            "proposed_ip": self.proposed_ip,
            "proposed_network": self.proposed_network,
            "other_device_label": self.other_device_label,
        }
        if self.other_device_ip is not None:
            out["other_device_ip"] = self.other_device_ip
        if self.other_device_network is not None:
            out["other_device_network"] = self.other_device_network
        if self.resolved_from is not None:
            out["resolved_from"] = self.resolved_from
        return out


def _resolve_to_ipv4(
    host_or_url: str,
) -> tuple[Optional[ipaddress.IPv4Address], Optional[str]]:
    """Parse a URL or hostname and resolve it to an IPv4 address.

    Returns ``(address, resolved_from)`` where ``resolved_from`` is the hostname
    we had to look up via DNS (``None`` if the input was already a literal IP).
    Returns ``(None, hostname)`` if DNS resolution failed.
    """
    raw = (host_or_url or "").strip()
    if not raw:
        return None, None

    # Extract host from URL or "host:port" form
    if "://" in raw:
        host = (urlparse(raw).hostname or "").strip()
    else:
        host = raw.split(":", 1)[0].strip()

    if not host:
        return None, None

    # Literal IPv4? Use it directly.
    try:
        return ipaddress.IPv4Address(host), None
    except (ipaddress.AddressValueError, ValueError):
        pass

    # Try DNS. Use a short timeout — we don't want to block wifi-add for long
    # if DNS is broken.
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(2.0)
        resolved = socket.gethostbyname(host)
        return ipaddress.IPv4Address(resolved), host
    except (socket.gaierror, socket.timeout, OSError) as exc:
        logger.warning(
            "Could not resolve %r for subnet check: %s", host, exc
        )
        return None, host
    finally:
        socket.setdefaulttimeout(old_timeout)


def check_subnet_compatibility(
    proposed_address: str,
    other_device_url_or_ip: Optional[str],
    other_device_label: str,
) -> Optional[NetworkCheckWarning]:
    """Determine whether a static-IP assignment will leave both devices reachable.

    Args:
        proposed_address: The static IP being assigned, in CIDR form
            (e.g. ``"192.168.1.50/24"``).
        other_device_url_or_ip: The URL or IP at which the other device is
            currently reachable. May be ``None`` if not known — in which case
            the check is silently skipped.
        other_device_label: Human-readable name for the warning text — either
            ``"GenMaster"`` or ``"GenSlave"``.

    Returns:
        A :class:`NetworkCheckWarning` if the user should be warned (subnet
        mismatch, or DNS resolution failed), otherwise ``None``.
    """
    if not other_device_url_or_ip:
        return None

    try:
        proposed = ipaddress.IPv4Interface(proposed_address)
    except (ipaddress.AddressValueError, ValueError):
        # Upstream validators should reject invalid CIDRs before they get
        # this far. If something slips through, don't fail loudly here.
        return None

    other_ip, resolved_from = _resolve_to_ipv4(other_device_url_or_ip)

    if other_ip is None and resolved_from is not None:
        # Hostname couldn't be resolved. Surface as a "could not verify"
        # warning so the user can decide whether to override.
        return NetworkCheckWarning(
            warning_code=WARNING_COULD_NOT_VERIFY,
            message=(
                f"Could not resolve {resolved_from!r} to verify whether "
                f"{other_device_label} will still be reachable from the new "
                f"static IP. The configuration will be applied as requested, "
                f"but you may want to confirm DNS or use an IP address instead."
            ),
            proposed_ip=str(proposed.ip),
            proposed_network=str(proposed.network),
            other_device_label=other_device_label,
            resolved_from=resolved_from,
        )

    if other_ip is None:
        # Nothing to compare against and nothing to warn about.
        return None

    # Tailscale exemption — subnet matching does not matter when the link is
    # tunneled.
    if other_ip in TAILSCALE_CGNAT:
        return None

    # Compute the other device's network using the *proposed* prefix length —
    # the question being asked is "given the netmask the user is choosing,
    # would these two addresses still share a subnet?"
    other_interface = ipaddress.IPv4Interface(
        f"{other_ip}/{proposed.network.prefixlen}"
    )

    if proposed.network == other_interface.network:
        return None

    return NetworkCheckWarning(
        warning_code=WARNING_SUBNET_MISMATCH,
        message=(
            f"Proposed {proposed.ip} is on network {proposed.network}, but "
            f"{other_device_label} is on {other_interface.network} "
            f"({other_ip}). The two devices will not be able to reach each "
            f"other over the local network unless they share a Tailscale "
            f"link."
        ),
        proposed_ip=str(proposed.ip),
        proposed_network=str(proposed.network),
        other_device_label=other_device_label,
        other_device_ip=str(other_ip),
        other_device_network=str(other_interface.network),
        resolved_from=resolved_from,
    )
