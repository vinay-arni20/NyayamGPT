"""
NyayamGPT - Authentication Schemas
==================================
Pydantic models for authentication request/response validation.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth.models import UserRole


# =============================================================================
# Request Schemas
# =============================================================================

class UserCreate(BaseModel):
    """Schema for user registration."""
    
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User's full name"
    )
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)"
    )
    confirm_password: str = Field(
        ...,
        description="Password confirmation"
    )
    role: UserRole = Field(
        default=UserRole.CITIZEN,
        description="User role"
    )
    preferred_language: str = Field(
        default="en",
        max_length=10,
        description="Preferred language code"
    )
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v
    
    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Validate password confirmation matches."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v
    
    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Sanitize and validate full name."""
        # Remove extra whitespace
        v = " ".join(v.split())
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Rahul Sharma",
                "email": "rahul@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "role": "citizen",
                "preferred_language": "en"
            }
        }


class UserLogin(BaseModel):
    """Schema for user login."""
    
    email: EmailStr = Field(
        ...,
        description="User's email address"
    )
    password: str = Field(
        ...,
        description="User's password"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "rahul@example.com",
                "password": "SecurePass123!"
            }
        }


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    
    refresh_token: str = Field(
        ...,
        description="Refresh token"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class PasswordChange(BaseModel):
    """Schema for password change."""
    
    current_password: str = Field(
        ...,
        description="Current password"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password"
    )
    confirm_new_password: str = Field(
        ...,
        description="Confirm new password"
    )
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v


# =============================================================================
# Response Schemas
# =============================================================================

class UserResponse(BaseModel):
    """Schema for user response."""
    
    id: str = Field(description="User ID")
    full_name: str = Field(description="User's full name")
    email: str = Field(description="User's email")
    phone: Optional[str] = Field(default=None, description="Phone number")
    role: UserRole = Field(description="User role")
    preferred_language: str = Field(description="Preferred language")
    is_active: bool = Field(description="Account active status")
    is_verified: bool = Field(description="Email verification status")
    created_at: datetime = Field(description="Account creation date")
    last_login: Optional[datetime] = Field(default=None, description="Last login time")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "full_name": "Rahul Sharma",
                "email": "rahul@example.com",
                "phone": "+919876543210",
                "role": "citizen",
                "preferred_language": "en",
                "is_active": True,
                "is_verified": False,
                "created_at": "2024-01-15T10:30:00Z",
                "last_login": "2024-01-20T14:45:00Z"
            }
        }


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    
    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Access token expiry in seconds")
    user: UserResponse = Field(description="User details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "full_name": "Rahul Sharma",
                    "email": "rahul@example.com",
                    "role": "citizen"
                }
            }
        }


class AuthError(BaseModel):
    """Schema for authentication errors."""
    
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: Optional[list[str]] = Field(default=None, description="Additional details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Invalid credentials",
                "details": ["Email or password is incorrect"]
            }
        }
