"""
NyayamGPT - Authentication Routes
=================================
API endpoints for user authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import crud
from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.auth.schemas import (
    AuthError,
    PasswordChange,
    TokenRefresh,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry_seconds,
    hash_password,
    verify_password,
)
from app.core.logging import logger
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": AuthError, "description": "Validation error"},
        409: {"model": AuthError, "description": "Email already exists"}
    },
    summary="Create a new account",
    description="Register a new user account with email, password, and profile information."
)
async def signup(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Create a new user account.
    
    - Validates email uniqueness
    - Validates password strength
    - Creates user with hashed password
    - Returns access and refresh tokens
    """
    # Check if email exists
    if await crud.check_email_exists(db, user_data.email):
        logger.warning("Signup attempt with existing email", email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists"
        )
    
    # Create user
    user = await crud.create_user(db, user_data)
    
    # Generate tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Update last login
    await crud.update_last_login(db, user.id)
    
    logger.info("User signup successful", user_id=user.id, email=user.email)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        401: {"model": AuthError, "description": "Invalid credentials"},
        403: {"model": AuthError, "description": "Account deactivated"}
    },
    summary="Login to account",
    description="Authenticate with email and password to receive access tokens."
)
async def login(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Authenticate user and return tokens.
    
    - Verifies email exists
    - Verifies password hash
    - Updates last login time
    - Returns access and refresh tokens
    """
    # Find user by email
    user = await crud.get_user_by_email(db, credentials.email)
    
    if not user:
        logger.warning("Login attempt with unknown email", email=credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning("Login attempt with wrong password", email=credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is active
    if not user.is_active:
        logger.warning("Login attempt to deactivated account", email=credentials.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support."
        )
    
    # Generate tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    # Update last login
    await crud.update_last_login(db, user.id)
    
    logger.info("User login successful", user_id=user.id, email=user.email)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
        user=UserResponse.model_validate(user)
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        401: {"model": AuthError, "description": "Invalid refresh token"}
    },
    summary="Refresh access token",
    description="Use refresh token to get a new access token."
)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh the access token using a valid refresh token.
    """
    # Decode refresh token
    payload = decode_token(token_data.refresh_token, token_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user
    user = await crud.get_user_by_id(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Generate new tokens
    new_token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    access_token = create_access_token(new_token_data)
    new_refresh_token = create_refresh_token(new_token_data)
    
    logger.debug("Token refreshed", user_id=user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=get_token_expiry_seconds(),
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": AuthError, "description": "Not authenticated"}
    },
    summary="Get current user",
    description="Get the currently authenticated user's profile."
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    Get the current authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": AuthError, "description": "Invalid current password"},
        401: {"model": AuthError, "description": "Not authenticated"}
    },
    summary="Change password",
    description="Change the current user's password."
)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Change the current user's password.
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Verify new passwords match
    if password_data.new_password != password_data.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match"
        )
    
    # Update password
    new_hash = hash_password(password_data.new_password)
    await crud.update_user_password(db, current_user.id, new_hash)
    
    logger.info("Password changed", user_id=current_user.id)
    
    return {"message": "Password changed successfully"}


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout",
    description="Logout the current user (client should discard tokens)."
)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Logout endpoint.
    
    Note: JWT tokens are stateless, so this endpoint mainly serves
    as a signal for the client to discard tokens. For true token
    invalidation, implement a token blacklist.
    """
    logger.info("User logout", user_id=current_user.id)
    return {"message": "Logged out successfully"}
