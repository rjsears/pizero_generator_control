# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/access_control.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 19th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Pydantic schemas for access control management."""

import ipaddress
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class IPRange(BaseModel):
    """IP range configuration for access control."""

    cidr: str = Field(description="CIDR notation IP range (e.g., 10.0.0.0/8)")
    description: Optional[str] = Field(None, description="Description of this IP range")
    access_level: str = Field(
        default="internal",
        description="Access level: 'internal' or 'external'",
        pattern=r"^(internal|external)$",
    )
    protected: bool = Field(
        default=False, description="If true, this range cannot be deleted"
    )

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Validate CIDR format."""
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR format: {e}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "cidr": "10.0.0.0/8",
                "description": "Docker default network",
                "access_level": "internal",
                "protected": False,
            }
        }


class AccessControlResponse(BaseModel):
    """Response containing current access control configuration."""

    enabled: bool = Field(description="Whether access control is enabled")
    ip_ranges: list[IPRange] = Field(
        default_factory=list, description="List of configured IP ranges"
    )
    nginx_config_path: str = Field(description="Path to nginx configuration file")
    last_updated: Optional[datetime] = Field(
        None, description="Last update timestamp"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "ip_ranges": [
                    {
                        "cidr": "127.0.0.1/32",
                        "description": "Localhost (protected)",
                        "access_level": "internal",
                        "protected": True,
                    },
                    {
                        "cidr": "10.0.0.0/8",
                        "description": "Docker default",
                        "access_level": "internal",
                        "protected": False,
                    },
                ],
                "nginx_config_path": "/etc/nginx/nginx.conf",
                "last_updated": "2026-01-19T12:00:00Z",
            }
        }


class AccessControlUpdateRequest(BaseModel):
    """Request to replace all IP ranges at once."""

    ip_ranges: list[IPRange] = Field(description="Complete list of IP ranges to set")


class AddIPRangeRequest(BaseModel):
    """Request to add a single IP range."""

    cidr: str = Field(description="CIDR notation IP range")
    description: Optional[str] = Field(None, description="Description of this IP range")
    access_level: str = Field(
        default="internal",
        description="Access level: 'internal' or 'external'",
        pattern=r"^(internal|external)$",
    )

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        """Validate CIDR format."""
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR format: {e}")
        return v


class UpdateIPRangeRequest(BaseModel):
    """Request to update an IP range's description."""

    description: str = Field(description="New description for the IP range")


class IPRangeActionResponse(BaseModel):
    """Response for IP range add/update/delete actions."""

    success: bool
    message: str
    nginx_test_passed: Optional[bool] = Field(
        None, description="Whether nginx -t passed"
    )
    nginx_reloaded: Optional[bool] = Field(
        None, description="Whether nginx was successfully reloaded"
    )
    nginx_output: Optional[str] = Field(
        None, description="Nginx test/reload output"
    )


class NginxReloadResponse(BaseModel):
    """Response for nginx reload action."""

    success: bool
    message: str
    output: Optional[str] = Field(None, description="Command output if any")
