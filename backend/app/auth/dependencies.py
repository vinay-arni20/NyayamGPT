"""
NyayamGPT - Authentication Dependencies
=======================================
FastAPI dependencies for authentication and authorization.
"""

from functools import wraps
from typing import Callable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.auth.security import decode_token
from app.core.logging import logger
from app.db.session import get_db

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Authenticated user or None
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
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    return user


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get the current active authenticated user.
    
    Raises HTTPException if:
    - No token provided
    - Invalid token
    - User not found
    - User is inactive
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        User: Authenticated active user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    payload = decode_token(token, token_type="access")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin")
        async def admin_only(user: User = Depends(require_role(UserRole.ADMIN))):
            ...
    
    Args:
        allowed_roles: Roles allowed to access the endpoint
        
    Returns:
        Dependency function
    """
    async def role_checker(
        user: User = Depends(get_current_active_user)
    ) -> User:
        if user.role not in allowed_roles:
            logger.warning(
                "Access denied - insufficient role",
                user_id=user.id,
                user_role=user.role,
                required_roles=[r.value for r in allowed_roles]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(r.value for r in allowed_roles)}"
            )
        return user
    
    return role_checker


def require_any_role(*allowed_roles: UserRole):
    """Alias for require_role - user must have any of the specified roles."""
    return require_role(*allowed_roles)


def require_admin():
    """Shorthand for requiring admin role."""
    return require_role(UserRole.ADMIN)


def require_lawyer_or_above():
    """Require lawyer, judge, or admin role."""
    return require_role(UserRole.LAWYER, UserRole.JUDGE, UserRole.ADMIN)


def require_judge_or_admin():
    """Require judge or admin role."""
    return require_role(UserRole.JUDGE, UserRole.ADMIN)


# Optional authentication - returns user if authenticated, None otherwise
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.
    
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = decode_token(token, token_type="access")
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.is_active:
            return user
        return None
        
    except Exception:
        return None
