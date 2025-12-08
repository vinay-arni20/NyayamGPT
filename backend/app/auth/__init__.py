"""
NyayamGPT - Authentication Module
=================================
Complete authentication system with JWT, roles, and password hashing.
"""

from app.auth.models import User, UserRole
from app.auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    require_role,
)

__all__ = [
    "User",
    "UserRole",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenRefresh",
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_current_user",
    "get_current_active_user",
    "require_role",
]
