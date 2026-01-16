# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
# /genmaster/backend/app/schemas/auth.py
#
# Part of the "RPi Generator Control" suite
# Version 1.0.0 - January 15th, 2026
#
# Richard J. Sears
# richardjsears@protonmail.com
# https://github.com/rjsears
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

"""Authentication-related Pydantic schemas."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request with username and password."""

    username: str = Field(min_length=1, max_length=50, description="Username")
    password: str = Field(min_length=1, max_length=128, description="Password")

    class Config:
        json_schema_extra = {"example": {"username": "admin", "password": "password"}}


class TokenResponse(BaseModel):
    """Token response after successful authentication."""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiry time in seconds")


class LoginResponse(BaseModel):
    """Login response with token and user info."""

    token: TokenResponse = Field(description="Authentication token")
    user: "UserResponse" = Field(description="User information")


class UserCreate(BaseModel):
    """Request to create a new user."""

    username: str = Field(min_length=3, max_length=50, description="Username")
    password: str = Field(min_length=8, max_length=128, description="Password")
    is_admin: bool = Field(default=False, description="Whether user is an admin")


class UserResponse(BaseModel):
    """User information response."""

    id: int
    username: str
    is_active: bool
    is_admin: bool
    created_at: str

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Request to change user password."""

    current_password: str = Field(
        min_length=1, max_length=128, description="Current password"
    )
    new_password: str = Field(
        min_length=8, max_length=128, description="New password"
    )


# Update forward reference
LoginResponse.model_rebuild()
