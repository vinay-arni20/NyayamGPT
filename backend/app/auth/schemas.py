"""
NyayamGPT - Authentication Schemas (Production-Grade)
=====================================================
Pydantic models for request/response validation with:
- Strong password validation
- Input sanitization
- Comprehensive error messages
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
)

from app.auth.models import UserRole, AuthProvider


# =============================================================================
# Password Validation
# =============================================================================

class PasswordMixin:
    """Mixin for password validation."""
    
    @staticmethod
    def validate_password_strength(password: str) -> str:
        """Validate password meets security requirements."""
        errors = []
        
        if len(password) < 8:
            errors.append("at least 8 characters")
        if len(password) > 128:
            errors.append("at most 128 characters")
        if not re.search(r"[A-Z]", password):
            errors.append("one uppercase letter")
        if not re.search(r"[a-z]", password):
            errors.append("one lowercase letter")
        if not re.search(r"\d", password):
            errors.append("one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\;'/`~]", password):
            errors.append("one special character")
        
        if errors:
            raise ValueError(f"Password must contain: {', '.join(errors)}")
        
        return password


# =============================================================================
# Request Schemas
# =============================================================================

class UserCreate(BaseModel, PasswordMixin):
    """Schema for user registration."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Rahul Sharma",
                "email": "rahul@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
                "role": "citizen",
                "preferred_language": "en",
            }
        }
    )
    
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="User's full name",
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, must include uppercase, lowercase, digit, special char)",
    )
    confirm_password: str = Field(
        ...,
        description="Password confirmation",
    )
    role: UserRole = Field(
        default=UserRole.CITIZEN,
        description="User role",
    )
    preferred_language: str = Field(
        default="en",
        max_length=10,
        description="Preferred language code (en, hi, etc.)",
    )
    
    @field_validator("password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return PasswordMixin.validate_password_strength(v)
    
    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        # Remove extra whitespace and control characters
        v = " ".join(v.split())
        # Basic XSS prevention
        v = re.sub(r"[<>\"']", "", v)
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()
    
    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class UserLogin(BaseModel):
    """Schema for user login."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "rahul@example.com",
                "password": "SecurePass123!",
            }
        }
    )
    
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )
    
    refresh_token: str = Field(..., description="Refresh token")


class PasswordChange(BaseModel, PasswordMixin):
    """Schema for password change."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecure456!",
                "confirm_new_password": "NewSecure456!",
            }
        }
    )
    
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password",
    )
    confirm_new_password: str = Field(..., description="Confirm new password")
    
    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return PasswordMixin.validate_password_strength(v)
    
    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")
        return self


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    
    email: EmailStr = Field(..., description="Email address for password reset")
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower().strip()


class PasswordResetConfirm(BaseModel, PasswordMixin):
    """Schema for confirming password reset."""
    
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password",
    )
    confirm_new_password: str = Field(..., description="Confirm new password")
    
    @field_validator("new_password")
    @classmethod
    def check_password_strength(cls, v: str) -> str:
        return PasswordMixin.validate_password_strength(v)
    
    @model_validator(mode="after")
    def check_passwords_match(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    preferred_language: Optional[str] = Field(None, max_length=10)
    
    @field_validator("full_name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.split())
        v = re.sub(r"[<>\"']", "", v)
        return v
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Allow only digits, spaces, dashes, plus
        cleaned = re.sub(r"[^\d\s\-+()]", "", v)
        if len(cleaned) < 10:
            raise ValueError("Invalid phone number")
        return cleaned


# =============================================================================
# Response Schemas
# =============================================================================

class UserResponse(BaseModel):
    """User data in API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole
    preferred_language: str
    auth_provider: AuthProvider
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Token response for login/signup."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class TokenOnlyResponse(BaseModel):
    """Token response without user data."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MessageResponse(BaseModel):
    """Generic message response."""
    
    message: str
    success: bool = True


class AuthError(BaseModel):
    """Error response for authentication errors."""
    
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    database: str
    version: str
