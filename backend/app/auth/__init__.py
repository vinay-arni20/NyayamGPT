"""
NyayamGPT - Authentication Module (Production-Grade)
====================================================
Complete authentication system with:
- Argon2id password hashing
- JWT with token revocation
- Role-based access control
- Account locking
- Refresh token rotation
"""

from app.auth.models import User, UserRole, AuthProvider, RefreshToken, TokenBlacklist
from app.auth.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenOnlyResponse,
    TokenRefresh,
    PasswordChange,
    UserUpdate,
    MessageResponse,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry_seconds,
)
from app.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_verified_user,
    require_roles,
    get_admin_user,
    get_legal_professional,
)

__all__ = [
    # Models
    "User",
    "UserRole",
    "AuthProvider",
    "RefreshToken",
    "TokenBlacklist",
    # Schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "TokenOnlyResponse",
    "TokenRefresh",
    "PasswordChange",
    "UserUpdate",
    "MessageResponse",
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_token_expiry_seconds",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_verified_user",
    "require_roles",
    "get_admin_user",
    "get_legal_professional",
]
