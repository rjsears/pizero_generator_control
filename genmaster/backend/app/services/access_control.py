# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/services/access_control.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""
Access Control Service - Manages nginx geo block configuration for IP-based access control.

This service provides functions to:
- Parse the nginx.conf geo block to extract IP ranges
- Generate a properly formatted geo block from IP ranges
- Update the nginx.conf file with new IP ranges
- Reload nginx configuration without container restart
"""

import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.schemas.access_control import IPRange

logger = logging.getLogger(__name__)

# Path to nginx config - can be overridden via environment variable
NGINX_CONFIG_PATH = os.environ.get(
    "NGINX_CONFIG_PATH", "/app/nginx/nginx.conf"
)

# Nginx container name for reload command
NGINX_CONTAINER = os.environ.get("NGINX_CONTAINER", "genmaster_nginx")

# Protected IP ranges that cannot be deleted
PROTECTED_IP_RANGES = ["127.0.0.1/32"]

# Default IP ranges for quick-add functionality
DEFAULT_IP_RANGES = [
    IPRange(
        cidr="127.0.0.1/32",
        description="Localhost (protected)",
        access_level="internal",
        protected=True,
    ),
    IPRange(
        cidr="10.0.0.0/8",
        description="RFC1918 Class A (Docker default)",
        access_level="internal",
        protected=False,
    ),
    IPRange(
        cidr="172.16.0.0/12",
        description="RFC1918 Class B (Docker networks)",
        access_level="internal",
        protected=False,
    ),
    IPRange(
        cidr="192.168.0.0/16",
        description="RFC1918 Class C (Local networks)",
        access_level="internal",
        protected=False,
    ),
    IPRange(
        cidr="100.64.0.0/10",
        description="Tailscale CGNAT range",
        access_level="internal",
        protected=False,
    ),
]

# Regex pattern to match the geo block in nginx.conf
GEO_BLOCK_PATTERN = re.compile(
    r'geo\s+\$access_level\s*\{([^}]+)\}',
    re.DOTALL
)

# Regex pattern to parse individual IP range lines in the geo block
IP_RANGE_LINE_PATTERN = re.compile(
    r'^\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\s+"(internal|external)";\s*(?:#\s*(.*))?$'
)


def parse_nginx_geo_block(config_content: str) -> list[IPRange]:
    """
    Parse the geo block from nginx config content.

    Args:
        config_content: The full nginx.conf content as a string

    Returns:
        List of IPRange objects parsed from the geo block
    """
    match = GEO_BLOCK_PATTERN.search(config_content)
    if not match:
        logger.warning("No geo block found in nginx config")
        return []

    geo_content = match.group(1)
    ip_ranges = []

    for line in geo_content.strip().split('\n'):
        line = line.strip()

        # Skip empty lines and default directive
        if not line or line.startswith('default'):
            continue

        # Try to parse the line
        line_match = IP_RANGE_LINE_PATTERN.match(line)
        if line_match:
            cidr = line_match.group(1)
            access_level = line_match.group(2)
            description = line_match.group(3) or ""

            ip_ranges.append(IPRange(
                cidr=cidr,
                description=description.strip(),
                access_level=access_level,
                protected=cidr in PROTECTED_IP_RANGES,
            ))
        else:
            # Try simpler parsing for lines without comments
            simple_match = re.match(
                r'^\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})\s+"?(internal|external)"?;?\s*$',
                line
            )
            if simple_match:
                cidr = simple_match.group(1)
                access_level = simple_match.group(2)
                ip_ranges.append(IPRange(
                    cidr=cidr,
                    description="",
                    access_level=access_level,
                    protected=cidr in PROTECTED_IP_RANGES,
                ))

    return ip_ranges


def generate_nginx_geo_block(ip_ranges: list[IPRange]) -> str:
    """
    Generate a properly formatted nginx geo block from IP ranges.

    Args:
        ip_ranges: List of IPRange objects to include in the geo block

    Returns:
        Formatted geo block string ready for nginx.conf
    """
    lines = [
        '    geo $access_level {',
        '        default          "external";',
    ]

    for ip_range in ip_ranges:
        # Pad CIDR to align columns (16 chars)
        padded_cidr = f'{ip_range.cidr:<16}'
        line = f'        {padded_cidr} "{ip_range.access_level}";'

        if ip_range.description:
            # Add description as comment
            line += f'  # {ip_range.description}'

        lines.append(line)

    lines.append('    }')

    return '\n'.join(lines)


def update_nginx_config_geo_block(
    config_path: str,
    ip_ranges: list[IPRange]
) -> tuple[bool, str]:
    """
    Update the nginx.conf file with a new geo block.

    Args:
        config_path: Path to nginx.conf file
        ip_ranges: List of IPRange objects for the new geo block

    Returns:
        Tuple of (success, message)
    """
    try:
        # Read current config
        path = Path(config_path)
        if not path.exists():
            return False, f"Nginx config not found at {config_path}"

        content = path.read_text()

        # Generate new geo block
        new_geo_block = generate_nginx_geo_block(ip_ranges)

        # Check if geo block exists
        match = GEO_BLOCK_PATTERN.search(content)
        if match:
            # Replace existing geo block
            # Find the full match including 'geo $access_level {'
            start = content.find('geo $access_level')
            if start == -1:
                return False, "Could not find geo block start position"

            # Find the closing brace
            brace_count = 0
            end = start
            in_block = False
            for i, char in enumerate(content[start:]):
                if char == '{':
                    brace_count += 1
                    in_block = True
                elif char == '}':
                    brace_count -= 1
                    if in_block and brace_count == 0:
                        end = start + i + 1
                        break

            # Replace the geo block
            new_content = content[:start] + new_geo_block + content[end:]
        else:
            # Insert new geo block before the server block
            server_pos = content.find('server {')
            if server_pos == -1:
                return False, "Could not find server block to insert geo block before"

            # Find a good insertion point (before server, after http directives)
            new_content = (
                content[:server_pos] +
                new_geo_block + '\n\n    ' +
                content[server_pos:]
            )

        # Backup original config
        backup_path = path.with_suffix('.conf.bak')
        path.rename(backup_path)

        try:
            # Write new config
            path.write_text(new_content)
            logger.info(f"Updated nginx geo block with {len(ip_ranges)} IP ranges")
            return True, f"Nginx config updated with {len(ip_ranges)} IP ranges"
        except Exception as write_error:
            # Restore backup on write failure
            backup_path.rename(path)
            raise write_error

    except Exception as e:
        logger.error(f"Failed to update nginx config: {e}")
        return False, f"Failed to update nginx config: {str(e)}"


def reload_nginx() -> tuple[bool, str, Optional[str]]:
    """
    Reload nginx configuration using docker exec.

    Returns:
        Tuple of (success, message, output)
    """
    try:
        # First, test the config
        test_result = subprocess.run(
            ['docker', 'exec', NGINX_CONTAINER, 'nginx', '-t'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if test_result.returncode != 0:
            error_msg = test_result.stderr or test_result.stdout
            logger.error(f"Nginx config test failed: {error_msg}")
            return False, "Nginx configuration test failed", error_msg

        # Config is valid, reload nginx
        reload_result = subprocess.run(
            ['docker', 'exec', NGINX_CONTAINER, 'nginx', '-s', 'reload'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if reload_result.returncode == 0:
            logger.info("Nginx reloaded successfully")
            return True, "Nginx reloaded successfully", reload_result.stdout

        error_msg = reload_result.stderr or reload_result.stdout
        logger.error(f"Nginx reload failed: {error_msg}")
        return False, "Nginx reload failed", error_msg

    except subprocess.TimeoutExpired:
        logger.error("Nginx reload timed out")
        return False, "Nginx reload timed out after 30 seconds", None
    except FileNotFoundError:
        logger.error("Docker command not found")
        return False, "Docker command not found - is Docker installed?", None
    except Exception as e:
        logger.error(f"Nginx reload error: {e}")
        return False, f"Nginx reload error: {str(e)}", None


def get_config_last_modified(config_path: str) -> Optional[datetime]:
    """
    Get the last modification time of the nginx config file.

    Args:
        config_path: Path to nginx.conf

    Returns:
        datetime of last modification or None if file doesn't exist
    """
    try:
        path = Path(config_path)
        if path.exists():
            return datetime.fromtimestamp(path.stat().st_mtime)
        return None
    except Exception:
        return None


def get_default_ip_ranges() -> list[IPRange]:
    """
    Get the default IP ranges for quick-add functionality.

    Returns:
        List of default IPRange objects
    """
    return DEFAULT_IP_RANGES.copy()


def is_protected_range(cidr: str) -> bool:
    """
    Check if a CIDR is a protected range that cannot be deleted.

    Args:
        cidr: CIDR notation IP range

    Returns:
        True if the range is protected
    """
    return cidr in PROTECTED_IP_RANGES
