"""
NyayamGPT - Authentication Dependencies (Production-Grade)
==========================================================
FastAPI dependencies for authentication with:
- Token validation with blacklist check
- Role-based access control
- Rate limiting awareness
- Proper error responses
"""

from typing import Optional, List, Callable
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.auth import crud
from app.auth.security import decode_token, get_token_jti
from app.core.logging import logger
from app.db.session import get_db


# HTTP Bearer security scheme (auto_error=False allows optional auth)
security = HTTPBearer(auto_error=False)
security_required = HTTPBearer(auto_error=True)


class AuthenticationError(HTTPException):
    """Custom authentication error with standardized format."""
    
    def __init__(
        self,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers or {"WWW-Authenticate": "Bearer"},
        )
        self.error_code = error_code


class AuthorizationError(HTTPException):
    """Custom authorization error for role-based access."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


# =============================================================================
# Core Authentication Dependencies
# =============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from JWT token (optional).
    
    Returns None if:
    - No token provided
    - Invalid token
    - User not found
    
    Use for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_token(token, token_type="access")
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti and await crud.is_token_blacklisted(db, jti):
        logger.warning("Blacklisted token used", jti=jti, user_id=user_id)
        return None
    
    # Fetch user
    user = await crud.get_user_by_id(db, user_id)
    
    return user


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current active user (required).
    
    Raises HTTPException if:
    - No token provided
    - Invalid/expired token
    - Token is blacklisted
    - User not found
    - User is inactive/deleted
    - Account is locked
    
    Use for endpoints that require authentication.
    """
    token = credentials.credentials
    payload = decode_token(token, token_type="access")
    
    if not payload:
        raise AuthenticationError(
            detail="Invalid or expired token",
            error_code="INVALID_TOKEN",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(
            detail="Invalid token payload",
            error_code="INVALID_PAYLOAD",
        )
    
    # Check if token is blacklisted
    jti = payload.get("jti")
    if jti and await crud.is_token_blacklisted(db, jti):
        logger.warning("Blacklisted token used", jti=jti, user_id=user_id)
        raise AuthenticationError(
            detail="Token has been revoked",
            error_code="TOKEN_REVOKED",
        )
    
    # Fetch user
    user = await crud.get_user_by_id(db, user_id)
    
    if not user:
        raise AuthenticationError(
            detail="User not found",
            error_code="USER_NOT_FOUND",
        )
    
    if not user.is_active or user.is_deleted:
        raise AuthorizationError(
            detail="Account is deactivated. Contact support.",
        )
    
    # Check if account is locked
    if user.is_locked:
        raise AuthorizationError(
            detail="Account is temporarily locked due to too many failed login attempts.",
        )
    
    return user


async def get_current_verified_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current user with verified email.
    
    Use for sensitive operations requiring email verification.
    """
    if not user.is_verified:
        raise AuthorizationError(
            detail="Email verification required for this action.",
        )
    
    return user


# =============================================================================
# Role-Based Access Control
# =============================================================================

def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(
            user: User = Depends(require_roles(UserRole.ADMIN))
        ):
            ...
    """
    async def role_checker(
        user: User = Depends(get_current_active_user),
    ) -> User:
        if user.role not in allowed_roles:
            logger.warning(
                "Access denied - insufficient role",
                user_id=user.id,
                user_role=user.role.value,
                required_roles=[r.value for r in allowed_roles],
            )
            raise AuthorizationError(
                detail=f"This action requires one of these roles: {', '.join(r.value for r in allowed_roles)}",
            )
        return user
    
    return role_checker


# Convenience dependencies for common role checks
async def get_admin_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """Require admin role."""
    if user.role != UserRole.ADMIN:
        raise AuthorizationError(detail="Admin access required")
    return user


async def get_legal_professional(
    user: User = Depends(get_current_active_user),
) -> User:
    """Require lawyer or judge role."""
    if user.role not in (UserRole.LAWYER, UserRole.JUDGE, UserRole.ADMIN):
        raise AuthorizationError(detail="Legal professional access required")
    return user


# =============================================================================
# Request Context Helpers
# =============================================================================

async def get_client_info(request: Request) -> dict:
    """
    Extract client information from request.
    
    Returns:
        dict with ip_address, user_agent, device_info
    """
    # Get IP (handle proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    
    user_agent = request.headers.get("User-Agent", "")
    
    # Simple device detection
    device_info = "unknown"
    ua_lower = user_agent.lower()
    if "mobile" in ua_lower or "android" in ua_lower or "iphone" in ua_lower:
        device_info = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_info = "tablet"
    elif any(b in ua_lower for b in ["chrome", "firefox", "safari", "edge"]):
        device_info = "desktop"
    
    return {
        "ip_address": ip_address,
        "user_agent": user_agent[:255] if user_agent else None,
        "device_info": device_info,
    }


# =============================================================================
# Token Extraction
# =============================================================================

def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extract bearer token from request headers.
    
    Useful for WebSocket authentication or custom handlers.
    """
    auth_header = request.headers.get("Authorization", "")
    
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    return None


async def validate_token(
    token: str,
    db: AsyncSession,
    token_type: str = "access",
) -> Optional[User]:
    """
    Validate a token and return the associated user.
    
    Useful for WebSocket or custom authentication flows.
    """
    payload = decode_token(token, token_type=token_type)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    # Check blacklist for access tokens
    if token_type == "access":
        jti = payload.get("jti")
        if jti and await crud.is_token_blacklisted(db, jti):
            return None
    
    return await crud.get_user_by_id(db, user_id)
