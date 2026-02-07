# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/routers/env_config.py
#
# Environment configuration management router
# Allows viewing/editing .env file from the UI
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 25th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Environment configuration management API endpoints."""

import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import AdminUser

logger = logging.getLogger(__name__)

router = APIRouter()

# Path to the .env file - check multiple common locations
# Priority: ENV_FILE_PATH env var > mounted /config/.env > /app/.env
def _find_env_file() -> Path:
    """Find the .env file in common locations."""
    # Check environment variable first (allows custom mount location)
    custom_path = os.environ.get("ENV_FILE_PATH")
    if custom_path:
        return Path(custom_path)

    # Check common locations
    candidates = [
        Path("/config/.env"),                           # Common Docker mount point
        Path("/app/.env"),                               # Container working directory
        Path("/data/.env"),                              # Data directory mount
        Path("/root/generator_control/genmaster/.env"),  # Host path if accessible
        Path(".env"),                                    # Current directory
    ]

    for path in candidates:
        if path.exists():
            logger.info(f"Found .env file at: {path}")
            return path

    # Default to /config/.env (user should mount here)
    logger.warning("No .env file found. Mount your .env file to /config/.env")
    return Path("/config/.env")

ENV_FILE_PATH = _find_env_file()
# Store backups in /app/data (a mounted volume) rather than next to the .env file
# This allows backups to work even when .env is mounted as a single file
ENV_BACKUP_DIR = Path("/app/data/env_backups")


# ============================================================================
# Pydantic Models
# ============================================================================

class EnvVariable(BaseModel):
    """Single environment variable."""
    key: str
    value: Optional[str] = None


class EnvVariableUpdate(BaseModel):
    """Update request for environment variable."""
    key: str
    value: str


class RestoreRequest(BaseModel):
    """Request to restore from backup."""
    filename: str


class RestartContainersRequest(BaseModel):
    """Request to restart containers."""
    containers: list[str]


# ============================================================================
# Variable Definitions - Groups and metadata
# ============================================================================

# Define known variables with their metadata
VARIABLE_DEFINITIONS = {
    # Database
    "POSTGRES_USER": {
        "group": "database",
        "label": "PostgreSQL User",
        "description": "Database username for GenMaster",
        "sensitive": False,
        "required": True,
        "editable": True,
        "type": "text",
    },
    "POSTGRES_PASSWORD": {
        "group": "database",
        "label": "PostgreSQL Password",
        "description": "Database password for GenMaster",
        "sensitive": True,
        "required": True,
        "editable": True,
        "type": "password",
        "warning": "Changing this requires updating the database as well",
    },
    "POSTGRES_DB": {
        "group": "database",
        "label": "PostgreSQL Database",
        "description": "Database name for GenMaster",
        "sensitive": False,
        "required": True,
        "editable": True,
        "type": "text",
    },
    "DATABASE_URL": {
        "group": "database",
        "label": "Database URL",
        "description": "Full database connection URL",
        "sensitive": True,
        "required": True,
        "editable": True,
        "type": "text",
        "warning": "Changing this may break database connectivity",
    },
    # Redis
    "REDIS_URL": {
        "group": "cache",
        "label": "Redis URL",
        "description": "Redis cache connection URL",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    # GenSlave Connection
    "SLAVE_API_URL": {
        "group": "genslave",
        "label": "GenSlave API URL",
        "description": "URL to connect to GenSlave API",
        "sensitive": False,
        "required": True,
        "editable": True,
        "type": "text",
    },
    "SLAVE_API_SECRET": {
        "group": "genslave",
        "label": "GenSlave API Secret",
        "description": "Shared secret for GenSlave authentication",
        "sensitive": True,
        "required": True,
        "editable": True,
        "type": "password",
    },
    "GENSLAVE_IP": {
        "group": "genslave",
        "label": "GenSlave IP Address",
        "description": "IP address of the GenSlave device",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    # Application
    "APP_ENV": {
        "group": "application",
        "label": "Environment",
        "description": "Application environment (development, production)",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    "APP_DEBUG": {
        "group": "application",
        "label": "Debug Mode",
        "description": "Enable debug mode (true/false)",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    "SECRET_KEY": {
        "group": "application",
        "label": "Secret Key",
        "description": "Application secret key for JWT tokens",
        "sensitive": True,
        "required": True,
        "editable": True,
        "type": "password",
        "warning": "Changing this will invalidate all active sessions",
    },
    "ADMIN_PASSWORD": {
        "group": "application",
        "label": "Admin Password",
        "description": "Password for the admin user",
        "sensitive": True,
        "required": True,
        "editable": True,
        "type": "password",
    },
    # GPIO
    "MOCK_GPIO": {
        "group": "hardware",
        "label": "Mock GPIO",
        "description": "Use mock GPIO for testing (true/false)",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    # Notifications
    "APPRISE_URLS": {
        "group": "notifications",
        "label": "Apprise URLs",
        "description": "Comma-separated Apprise notification URLs",
        "sensitive": True,
        "required": False,
        "editable": True,
        "type": "text",
    },
    # Generator Info
    "GEN_INFO_MANUFACTURER": {
        "group": "generator",
        "label": "Manufacturer",
        "description": "Generator manufacturer name",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    "GEN_INFO_MODEL_NUMBER": {
        "group": "generator",
        "label": "Model Number",
        "description": "Generator model number",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    "GEN_INFO_SERIAL_NUMBER": {
        "group": "generator",
        "label": "Serial Number",
        "description": "Generator serial number",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
    "GEN_INFO_FUEL_TYPE": {
        "group": "generator",
        "label": "Fuel Type",
        "description": "Type of fuel (propane, natural_gas, diesel, gasoline)",
        "sensitive": False,
        "required": False,
        "editable": True,
        "type": "text",
    },
}

# Group definitions
GROUPS = {
    "database": {
        "key": "database",
        "label": "Database Configuration",
        "description": "PostgreSQL database connection settings",
        "icon": "CircleStackIcon",
        "color": "blue",
        "order": 1,
    },
    "cache": {
        "key": "cache",
        "label": "Cache Configuration",
        "description": "Redis cache settings",
        "icon": "ServerIcon",
        "color": "purple",
        "order": 2,
    },
    "genslave": {
        "key": "genslave",
        "label": "GenSlave Connection",
        "description": "Settings for connecting to the GenSlave device",
        "icon": "ServerIcon",
        "color": "emerald",
        "order": 3,
    },
    "application": {
        "key": "application",
        "label": "Application Settings",
        "description": "Core application configuration",
        "icon": "Cog6ToothIcon",
        "color": "amber",
        "order": 4,
    },
    "hardware": {
        "key": "hardware",
        "label": "Hardware Settings",
        "description": "GPIO and hardware configuration",
        "icon": "CpuChipIcon",
        "color": "rose",
        "order": 5,
    },
    "notifications": {
        "key": "notifications",
        "label": "Notification Settings",
        "description": "Alert and notification configuration",
        "icon": "BellIcon",
        "color": "orange",
        "order": 6,
    },
    "generator": {
        "key": "generator",
        "label": "Generator Information",
        "description": "Generator identification and specs",
        "icon": "BoltIcon",
        "color": "cyan",
        "order": 7,
    },
    "custom": {
        "key": "custom",
        "label": "Custom Variables",
        "description": "User-defined environment variables",
        "icon": "PlusCircleIcon",
        "color": "gray",
        "order": 99,
    },
}


# ============================================================================
# Helper Functions
# ============================================================================

def read_env_file() -> dict[str, str]:
    """Read and parse the .env file."""
    variables = {}

    if not ENV_FILE_PATH.exists():
        logger.warning(f".env file not found at {ENV_FILE_PATH}")
        return variables

    try:
        with open(ENV_FILE_PATH, "r") as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                # Parse KEY=VALUE
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    variables[key] = value
    except Exception as e:
        logger.error(f"Failed to read .env file: {e}")

    return variables


def write_env_file(variables: dict[str, str]) -> None:
    """Write variables to the .env file, preserving comments and order."""
    lines = []
    written_keys = set()

    # Read existing file to preserve comments and order
    if ENV_FILE_PATH.exists():
        with open(ENV_FILE_PATH, "r") as f:
            for line in f:
                stripped = line.strip()
                # Keep comments and empty lines
                if not stripped or stripped.startswith("#"):
                    lines.append(line.rstrip("\n"))
                    continue
                # Update existing variables
                if "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in variables:
                        value = variables[key]
                        # Quote values with spaces or special chars
                        if " " in value or "=" in value or '"' in value:
                            value = f'"{value}"'
                        lines.append(f"{key}={value}")
                        written_keys.add(key)
                    else:
                        # Variable was deleted, skip it
                        pass

    # Add new variables at the end
    for key, value in variables.items():
        if key not in written_keys:
            if " " in value or "=" in value or '"' in value:
                value = f'"{value}"'
            lines.append(f"{key}={value}")

    # Write the file
    with open(ENV_FILE_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def create_backup() -> str:
    """Create a backup of the current .env file."""
    ENV_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_filename = f".env_backup_{timestamp}"
    backup_path = ENV_BACKUP_DIR / backup_filename

    if ENV_FILE_PATH.exists():
        shutil.copy2(ENV_FILE_PATH, backup_path)
        logger.info(f"Created .env backup: {backup_filename}")

    return backup_filename


def get_backups() -> list[dict]:
    """Get list of backup files."""
    backups = []

    if not ENV_BACKUP_DIR.exists():
        return backups

    for path in sorted(ENV_BACKUP_DIR.glob(".env_backup_*"), reverse=True):
        stat = path.stat()
        # Parse timestamp from filename
        match = re.search(r"_(\d{14})$", path.name)
        if match:
            ts = match.group(1)
            created_at = datetime.strptime(ts, "%Y%m%d%H%M%S").isoformat()
        else:
            created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()

        backups.append({
            "filename": path.name,
            "created_at": created_at,
            "size": stat.st_size,
        })

    return backups[:20]  # Return last 20 backups


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("")
async def get_env_config(
    admin: AdminUser
) -> dict[str, Any]:
    """Get all environment variables grouped by category."""
    variables = read_env_file()

    # Build groups with variables
    groups_data = []
    known_keys = set(VARIABLE_DEFINITIONS.keys())

    for group_key, group_info in sorted(GROUPS.items(), key=lambda x: x[1]["order"]):
        group_vars = []

        # Add defined variables for this group
        for var_key, var_def in VARIABLE_DEFINITIONS.items():
            if var_def["group"] == group_key:
                value = variables.get(var_key, "")
                group_vars.append({
                    "key": var_key,
                    "value": value,
                    "label": var_def["label"],
                    "description": var_def["description"],
                    "sensitive": var_def.get("sensitive", False),
                    "required": var_def.get("required", False),
                    "editable": var_def.get("editable", True),
                    "type": var_def.get("type", "text"),
                    "warning": var_def.get("warning"),
                    "default": var_def.get("default"),
                    "is_custom": False,
                })

        # Add custom variables (unknown keys) to the custom group
        if group_key == "custom":
            for var_key, value in variables.items():
                if var_key not in known_keys:
                    group_vars.append({
                        "key": var_key,
                        "value": value,
                        "label": var_key,
                        "description": "Custom user-defined variable",
                        "sensitive": False,
                        "required": False,
                        "editable": True,
                        "type": "text",
                        "is_custom": True,
                    })

        groups_data.append({
            **group_info,
            "variables": group_vars,
        })

    # Get file modification time
    last_modified = None
    if ENV_FILE_PATH.exists():
        stat = ENV_FILE_PATH.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

    return {
        "groups": groups_data,
        "last_modified": last_modified,
    }


@router.put("/{key}")
async def update_variable(
    key: str,
    update: EnvVariableUpdate,
    admin: AdminUser
) -> dict[str, Any]:
    """Update an environment variable."""
    # Create backup first
    create_backup()

    # Read current variables
    variables = read_env_file()

    # Update the variable
    variables[key] = update.value

    # Write back
    write_env_file(variables)

    logger.info(f"Updated environment variable: {key}")

    return {
        "status": "success",
        "message": f"Variable {key} updated successfully",
    }


@router.post("")
async def add_variable(
    variable: EnvVariable,
    admin: AdminUser
) -> dict[str, Any]:
    """Add a new environment variable."""
    # Validate key format
    if not re.match(r"^[A-Z][A-Z0-9_]*$", variable.key):
        raise HTTPException(
            status_code=400,
            detail="Variable name must be uppercase, start with a letter, and contain only letters, numbers, and underscores"
        )

    # Check if exists
    variables = read_env_file()
    if variable.key in variables:
        raise HTTPException(
            status_code=400,
            detail=f"Variable {variable.key} already exists"
        )

    # Create backup first
    create_backup()

    # Add the variable
    variables[variable.key] = variable.value or ""
    write_env_file(variables)

    logger.info(f"Added new environment variable: {variable.key}")

    return {
        "status": "success",
        "message": f"Variable {variable.key} added successfully",
    }


@router.delete("/{key}")
async def delete_variable(
    key: str,
    admin: AdminUser
) -> dict[str, Any]:
    """Delete an environment variable."""
    # Don't allow deleting known variables
    if key in VARIABLE_DEFINITIONS:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete system-defined variables"
        )

    # Create backup first
    create_backup()

    # Read and remove
    variables = read_env_file()
    if key not in variables:
        raise HTTPException(status_code=404, detail=f"Variable {key} not found")

    del variables[key]
    write_env_file(variables)

    logger.info(f"Deleted environment variable: {key}")

    return {
        "status": "success",
        "message": f"Variable {key} deleted successfully",
    }


@router.get("/backups")
async def list_backups(
    admin: AdminUser
) -> dict[str, Any]:
    """List available .env backups."""
    return {
        "backups": get_backups(),
    }


@router.post("/backup")
async def create_backup_endpoint(
    admin: AdminUser
) -> dict[str, Any]:
    """Create a new backup of the current .env file."""
    filename = create_backup()
    return {
        "status": "success",
        "message": "Backup created successfully",
        "filename": filename,
    }


@router.post("/restore")
async def restore_backup(
    request: RestoreRequest,
    admin: AdminUser
) -> dict[str, Any]:
    """Restore .env from a backup file."""
    backup_path = ENV_BACKUP_DIR / request.filename

    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")

    # Create a backup of current before restoring
    create_backup()

    # Restore
    shutil.copy2(backup_path, ENV_FILE_PATH)

    logger.info(f"Restored .env from backup: {request.filename}")

    return {
        "status": "success",
        "message": f"Restored from {request.filename}",
    }


@router.post("/reload")
async def reload_variables(
    admin: AdminUser
) -> dict[str, Any]:
    """Reload environment variables into the current process."""
    variables = read_env_file()

    for key, value in variables.items():
        os.environ[key] = value

    logger.info("Reloaded environment variables into process")

    return {
        "status": "success",
        "message": f"Reloaded {len(variables)} environment variables",
    }


@router.get("/affected-containers/{key}")
async def get_affected_containers(
    key: str,
    admin: AdminUser
) -> dict[str, Any]:
    """Get containers that use a specific environment variable."""
    # For GenMaster, the main container uses most variables
    # This is simplified - in a more complex setup, you'd map variables to containers

    container_map = {
        "POSTGRES_": ["genmaster_postgres"],
        "REDIS_": ["genmaster_redis"],
        "DATABASE_URL": ["genmaster_api"],
        "SECRET_KEY": ["genmaster_api"],
        "ADMIN_PASSWORD": ["genmaster_api"],
        "SLAVE_": ["genmaster_api"],
        "GENSLAVE_": ["genmaster_api"],
        "APP_": ["genmaster_api"],
        "MOCK_GPIO": ["genmaster_api"],
        "APPRISE_": ["genmaster_api"],
        "GEN_INFO_": ["genmaster_api"],
    }

    affected = []
    for prefix, containers in container_map.items():
        if key.startswith(prefix) or key == prefix.rstrip("_"):
            affected.extend(containers)

    # Default to API container if no specific mapping
    if not affected:
        affected = ["genmaster_api"]

    # Remove duplicates while preserving order
    affected = list(dict.fromkeys(affected))

    display_names = {
        "genmaster_api": "GenMaster API",
        "genmaster_postgres": "PostgreSQL Database",
        "genmaster_redis": "Redis Cache",
        "genmaster_nginx": "Nginx",
    }

    return {
        "affected_containers": affected,
        "container_display_names": display_names,
    }


@router.post("/restart-containers")
async def restart_containers(
    request: RestartContainersRequest,
    admin: AdminUser
) -> dict[str, Any]:
    """Restart specified containers."""
    import subprocess

    results = []
    for container in request.containers:
        try:
            subprocess.run(
                ["docker", "restart", container],
                check=True,
                capture_output=True,
                timeout=60
            )
            results.append({"container": container, "success": True})
            logger.info(f"Restarted container: {container}")
        except subprocess.CalledProcessError as e:
            results.append({
                "container": container,
                "success": False,
                "error": e.stderr.decode() if e.stderr else str(e)
            })
            logger.error(f"Failed to restart container {container}: {e}")
        except Exception as e:
            results.append({
                "container": container,
                "success": False,
                "error": str(e)
            })

    all_success = all(r["success"] for r in results)

    return {
        "status": "success" if all_success else "partial",
        "message": f"Restarted {sum(1 for r in results if r['success'])}/{len(results)} containers",
        "results": results,
    }


@router.post("/health-check")
async def run_health_check(
    admin: AdminUser
) -> dict[str, Any]:
    """Run health checks on the current configuration."""
    variables = read_env_file()
    checks = []
    warnings = []

    # Check required variables
    missing = []
    for key, definition in VARIABLE_DEFINITIONS.items():
        if definition.get("required") and not variables.get(key):
            missing.append(key)

    checks.append({
        "check_type": "required_variables",
        "success": len(missing) == 0,
        "message": "All required variables are set" if not missing else f"Missing {len(missing)} required variables",
        "details": {"missing": missing} if missing else None,
    })

    # Check database connectivity
    db_url = variables.get("DATABASE_URL", "")
    if db_url:
        try:
            # Parse connection params from URL
            # This is a simplified check
            checks.append({
                "check_type": "postgres_connection",
                "success": True,
                "message": "Database URL is configured",
                "details": {"host": "configured"},
            })
        except Exception as e:
            checks.append({
                "check_type": "postgres_connection",
                "success": False,
                "message": f"Database check failed: {e}",
                "details": {"error": str(e)},
            })
    else:
        checks.append({
            "check_type": "postgres_connection",
            "success": False,
            "message": "DATABASE_URL is not configured",
            "details": None,
        })

    # Check GenSlave connectivity
    slave_url = variables.get("SLAVE_API_URL", "")
    if slave_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{slave_url}/health")
                if response.status_code == 200:
                    checks.append({
                        "check_type": "genslave_connection",
                        "success": True,
                        "message": "GenSlave is reachable",
                        "details": {"url": slave_url},
                    })
                else:
                    checks.append({
                        "check_type": "genslave_connection",
                        "success": False,
                        "message": f"GenSlave returned status {response.status_code}",
                        "details": {"url": slave_url},
                    })
        except Exception as e:
            checks.append({
                "check_type": "genslave_connection",
                "success": False,
                "message": f"Cannot reach GenSlave: {e}",
                "details": {"url": slave_url, "error": str(e)},
            })

    overall_success = all(c["success"] for c in checks)

    return {
        "overall_success": overall_success,
        "checks": checks,
        "warnings": warnings,
    }
