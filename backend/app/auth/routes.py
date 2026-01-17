"""
NyayamGPT - Authentication Routes (Production-Grade)
====================================================
API endpoints for authentication with:
- Proper error handling with error codes
- Audit logging for security events
- Account locking on failed attempts
- Token rotation on refresh
- Secure logout with token revocation
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import crud
from app.auth.dependencies import (
    get_current_active_user,
    get_current_verified_user,
    get_client_info,
    AuthenticationError,
    AuthorizationError,
)
from app.auth.models import User
from app.auth.schemas import (
    AuthError,
    MessageResponse,
    PasswordChange,
    TokenOnlyResponse,
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
    get_token_expiry_seconds,
    get_refresh_token_expiry_seconds,
    hash_password,
    verify_password,
    get_token_jti,
)
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db


router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# Registration
# =============================================================================

@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": AuthError, "description": "Validation error"},
        409: {"model": AuthError, "description": "Email already exists"},
    },
    summary="Create a new account",
    description="Register a new user with email and password.",
)
async def signup(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Create a new user account.
    
    - Validates email uniqueness
    - Validates password strength
    - Creates user with hashed password
    - Returns access and refresh tokens
    """
    # Check email uniqueness
    if await crud.check_email_exists(db, user_data.email):
        logger.warning(
            "Signup attempt with existing email",
            email=user_data.email,
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    
    # Create user
    user = await crud.create_user(db, user_data)
    
    # Get client info for token storage
    client_info = await get_client_info(request)
    
    # Generate tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Store refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    await crud.store_refresh_token(
        db=db,
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
        device_info=client_info.get("device_info"),
        ip_address=client_info.get("ip_address"),
    )
    
    # Update last login
    await crud.update_last_login(db, user.id)
    
    logger.info(
        "User signup successful",
        user_id=user.id,
        email=user.email,
        ip=client_info.get("ip_address"),
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
        user=UserResponse.model_validate(user),
    )


# =============================================================================
# Login
# =============================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": AuthError, "description": "Invalid credentials"},
        403: {"model": AuthError, "description": "Account locked or deactivated"},
    },
    summary="Login to account",
    description="Authenticate with email and password.",
)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    
    - Verifies email exists
    - Checks account status (active, not locked)
    - Verifies password
    - Updates failed attempt counter on failure
    - Returns access and refresh tokens on success
    """
    client_info = await get_client_info(request)
    
    # Find user
    user = await crud.get_user_by_email(db, credentials.email)
    
    if not user:
        logger.warning(
            "Login attempt with unknown email",
            email=credentials.email,
            ip=client_info.get("ip_address"),
        )
        # Use generic message to prevent email enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Check if account is locked
    if await crud.is_account_locked(db, user.id):
        logger.warning(
            "Login attempt on locked account",
            user_id=user.id,
            email=user.email,
            ip=client_info.get("ip_address"),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked due to too many failed attempts. Please try again later.",
        )
    
    # Check if account is active
    if not user.is_active or user.is_deleted:
        logger.warning(
            "Login attempt on deactivated account",
            user_id=user.id,
            email=user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash or ""):
        # Record failed attempt
        attempt_count = await crud.record_failed_login(db, user.id)
        
        logger.warning(
            "Login failed - wrong password",
            user_id=user.id,
            email=user.email,
            attempt=attempt_count,
            ip=client_info.get("ip_address"),
        )
        
        # Generic message
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Successful login - reset failed attempts
    await crud.reset_failed_login_attempts(db, user.id)
    
    # Check and rehash password if needed (Argon2 migration)
    await crud.check_and_rehash_password(db, user, credentials.password)
    
    # Generate tokens
    token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Store refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    await crud.store_refresh_token(
        db=db,
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
        device_info=client_info.get("device_info"),
        ip_address=client_info.get("ip_address"),
    )
    
    # Update last login
    await crud.update_last_login(db, user.id)
    
    logger.info(
        "User login successful",
        user_id=user.id,
        email=user.email,
        ip=client_info.get("ip_address"),
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
        user=UserResponse.model_validate(user),
    )


# =============================================================================
# Token Refresh
# =============================================================================

@router.post(
    "/refresh",
    response_model=TokenOnlyResponse,
    responses={
        401: {"model": AuthError, "description": "Invalid refresh token"},
    },
    summary="Refresh access token",
    description="Get new access token using refresh token.",
)
async def refresh_token(
    token_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenOnlyResponse:
    """
    Refresh access token.
    
    - Validates refresh token
    - Checks if token is revoked
    - Issues new access token
    - Optionally rotates refresh token
    """
    # Validate token format
    payload = decode_token(token_data.refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Check if token exists and is valid in database
    stored_token = await crud.get_refresh_token(db, token_data.refresh_token)
    
    if not stored_token:
        logger.warning(
            "Invalid refresh token used",
            user_id=user_id,
            ip=request.client.host if request.client else None,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has been revoked",
        )
    
    # Get user
    user = await crud.get_user_by_id(db, user_id)
    
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is no longer valid",
        )
    
    # Update token usage
    await crud.update_refresh_token_usage(db, token_data.refresh_token)
    
    # Generate new tokens
    new_token_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value,
    }
    new_access_token = create_access_token(new_token_data)
    new_refresh_token = create_refresh_token(new_token_data)
    
    # Token rotation: revoke old, create new
    await crud.revoke_refresh_token(db, token_data.refresh_token)
    
    client_info = await get_client_info(request)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    await crud.store_refresh_token(
        db=db,
        user_id=user.id,
        token=new_refresh_token,
        expires_at=expires_at,
        device_info=client_info.get("device_info"),
        ip_address=client_info.get("ip_address"),
    )
    
    logger.debug("Token refreshed", user_id=user.id)
    
    return TokenOnlyResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
    )


# =============================================================================
# Logout
# =============================================================================

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout from current session",
    description="Revoke current refresh token.",
)
async def logout(
    token_data: TokenRefresh,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Logout from current session.
    
    - Revokes the provided refresh token
    - Access token will expire naturally
    """
    await crud.revoke_refresh_token(db, token_data.refresh_token)
    
    logger.info("User logged out", user_id=current_user.id)
    
    return MessageResponse(message="Successfully logged out")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Logout from all devices",
    description="Revoke all refresh tokens for the user.",
)
async def logout_all(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Logout from all devices.
    
    - Revokes all refresh tokens for the user
    - All sessions will be terminated
    """
    count = await crud.revoke_all_user_tokens(db, current_user.id)
    
    logger.info(
        "User logged out from all devices",
        user_id=current_user.id,
        sessions_terminated=count,
    )
    
    return MessageResponse(
        message=f"Successfully logged out from {count} session(s)"
    )


# =============================================================================
# User Profile
# =============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get the authenticated user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Get current user's profile information."""
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update user profile",
    description="Update the authenticated user's profile.",
)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user's profile."""
    updated_user = await crud.update_user(db, current_user.id, user_data)
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    logger.info("User profile updated", user_id=current_user.id)
    
    return UserResponse.model_validate(updated_user)


# =============================================================================
# Password Management
# =============================================================================

@router.post(
    "/change-password",
    response_model=MessageResponse,
    responses={
        400: {"model": AuthError, "description": "Invalid current password"},
    },
    summary="Change password",
    description="Change the authenticated user's password.",
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Change user's password.
    
    - Verifies current password
    - Updates to new password
    - Optionally revokes all tokens
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash or ""):
        logger.warning(
            "Password change failed - wrong current password",
            user_id=current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    # Update password
    new_hash = hash_password(password_data.new_password)
    await crud.update_user_password(db, current_user.id, new_hash)
    
    # Revoke all existing sessions for security
    await crud.revoke_all_user_tokens(db, current_user.id)
    
    logger.info("User password changed", user_id=current_user.id)
    
    return MessageResponse(
        message="Password changed successfully. Please login again."
    )


# =============================================================================
# Health Check
# =============================================================================

@router.get(
    "/health",
    summary="Auth service health check",
    description="Check if the authentication service is healthy.",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Check auth service health."""
    from app.db.session import DatabaseManager
    
    db_health = await DatabaseManager.health_check()
    
    return {
        "status": "healthy" if db_health["status"] == "healthy" else "degraded",
        "auth_service": "operational",
        "database": db_health["status"],
        "version": settings.app_version,
    }
