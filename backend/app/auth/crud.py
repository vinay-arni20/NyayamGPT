"""
NyayamGPT - Authentication CRUD (Production-Grade)
==================================================
Database operations for user management with:
- Proper error handling
- Audit logging
- Account locking
- Token management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole, RefreshToken, TokenBlacklist, AuthProvider
from app.auth.schemas import UserCreate, UserUpdate
from app.auth.security import hash_password, hash_token, needs_rehash
from app.core.logging import logger


# =============================================================================
# Constants
# =============================================================================

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


# =============================================================================
# User Queries
# =============================================================================

async def get_user_by_id(
    db: AsyncSession,
    user_id: str,
    include_deleted: bool = False,
) -> Optional[User]:
    """
    Get user by ID.
    
    Args:
        db: Database session
        user_id: User UUID
        include_deleted: Whether to include soft-deleted users
        
    Returns:
        User or None
    """
    query = select(User).where(User.id == user_id)
    
    if not include_deleted:
        query = query.where(User.is_deleted == False)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
    include_deleted: bool = False,
) -> Optional[User]:
    """
    Get user by email address.
    
    Args:
        db: Database session
        email: Email address (case-insensitive)
        include_deleted: Whether to include soft-deleted users
        
    Returns:
        User or None
    """
    query = select(User).where(User.email == email.lower())
    
    if not include_deleted:
        query = query.where(User.is_deleted == False)
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_email_exists(
    db: AsyncSession,
    email: str,
    exclude_user_id: Optional[str] = None,
) -> bool:
    """
    Check if email is already registered.
    
    Args:
        db: Database session
        email: Email to check
        exclude_user_id: Optional user ID to exclude from check
        
    Returns:
        bool: True if email exists
    """
    query = select(User.id).where(
        and_(
            User.email == email.lower(),
            User.is_deleted == False,
        )
    )
    
    if exclude_user_id:
        query = query.where(User.id != exclude_user_id)
    
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


# =============================================================================
# User Creation
# =============================================================================

async def create_user(
    db: AsyncSession,
    user_data: UserCreate,
    auth_provider: AuthProvider = AuthProvider.LOCAL,
    auth_provider_id: Optional[str] = None,
    is_verified: bool = False,
) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        user_data: User creation data
        auth_provider: Authentication provider (local, google, etc.)
        auth_provider_id: External provider user ID
        is_verified: Whether email is pre-verified (OAuth)
        
    Returns:
        User: Created user
    """
    user = User(
        full_name=user_data.full_name,
        email=user_data.email.lower(),
        password_hash=hash_password(user_data.password) if user_data.password else None,
        role=user_data.role,
        preferred_language=user_data.preferred_language,
        auth_provider=auth_provider,
        auth_provider_id=auth_provider_id,
        is_active=True,
        is_verified=is_verified,
        is_deleted=False,
    )
    
    db.add(user)
    await db.flush()
    await db.refresh(user)
    
    logger.info(
        "User created",
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        provider=auth_provider.value,
    )
    
    return user


# =============================================================================
# User Updates
# =============================================================================

async def update_user(
    db: AsyncSession,
    user_id: str,
    user_data: UserUpdate,
) -> Optional[User]:
    """
    Update user profile.
    
    Args:
        db: Database session
        user_id: User UUID
        user_data: Fields to update
        
    Returns:
        Updated User or None
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    
    update_data = user_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await db.flush()
    await db.refresh(user)
    
    logger.info("User updated", user_id=user_id, fields=list(update_data.keys()))
    
    return user


async def update_last_login(db: AsyncSession, user_id: str) -> None:
    """Update user's last login timestamp."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login=datetime.now(timezone.utc))
    )


async def update_user_password(
    db: AsyncSession,
    user_id: str,
    new_password_hash: str,
) -> bool:
    """
    Update user's password.
    
    Args:
        db: Database session
        user_id: User UUID
        new_password_hash: New hashed password
        
    Returns:
        bool: Success status
    """
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            password_hash=new_password_hash,
            password_changed_at=datetime.now(timezone.utc),
            failed_login_attempts=0,
            locked_until=None,
        )
    )
    
    if result.rowcount > 0:
        logger.info("User password updated", user_id=user_id)
        return True
    
    return False


async def verify_user_email(db: AsyncSession, user_id: str) -> bool:
    """Mark user's email as verified."""
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_verified=True)
    )
    
    if result.rowcount > 0:
        logger.info("User email verified", user_id=user_id)
        return True
    
    return False


async def deactivate_user(db: AsyncSession, user_id: str) -> bool:
    """Deactivate user account (soft delete)."""
    result = await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            is_active=False,
            is_deleted=True,
        )
    )
    
    if result.rowcount > 0:
        logger.info("User deactivated", user_id=user_id)
        return True
    
    return False


# =============================================================================
# Account Locking
# =============================================================================

async def record_failed_login(db: AsyncSession, user_id: str) -> int:
    """
    Record a failed login attempt.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        int: Current failed attempt count
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        return 0
    
    new_count = user.failed_login_attempts + 1
    
    update_values = {"failed_login_attempts": new_count}
    
    # Lock account after max attempts
    if new_count >= MAX_FAILED_ATTEMPTS:
        lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        update_values["locked_until"] = lock_until
        logger.warning(
            "User account locked",
            user_id=user_id,
            locked_until=lock_until.isoformat(),
        )
    
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(**update_values)
    )
    
    return new_count


async def reset_failed_login_attempts(db: AsyncSession, user_id: str) -> None:
    """Reset failed login counter on successful login."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            failed_login_attempts=0,
            locked_until=None,
        )
    )


async def is_account_locked(db: AsyncSession, user_id: str) -> bool:
    """Check if account is currently locked."""
    user = await get_user_by_id(db, user_id)
    if not user:
        return False
    
    if user.locked_until is None:
        return False
    
    if datetime.now(timezone.utc) > user.locked_until:
        # Lock expired, reset
        await reset_failed_login_attempts(db, user_id)
        return False
    
    return True


# =============================================================================
# Refresh Token Management
# =============================================================================

async def store_refresh_token(
    db: AsyncSession,
    user_id: str,
    token: str,
    expires_at: datetime,
    device_info: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> RefreshToken:
    """
    Store a refresh token.
    
    Args:
        db: Database session
        user_id: User UUID
        token: Raw refresh token (will be hashed)
        expires_at: Token expiration time
        device_info: Optional device identifier
        ip_address: Optional IP address
        
    Returns:
        RefreshToken: Stored token record
    """
    token_record = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(token),
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at,
        is_revoked=False,
    )
    
    db.add(token_record)
    await db.flush()
    
    return token_record


async def get_refresh_token(
    db: AsyncSession,
    token: str,
) -> Optional[RefreshToken]:
    """
    Get refresh token by raw token value.
    
    Args:
        db: Database session
        token: Raw refresh token
        
    Returns:
        RefreshToken or None
    """
    token_hash = hash_token(token)
    
    result = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
    )
    
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
    """Revoke a specific refresh token."""
    token_hash = hash_token(token)
    
    result = await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(is_revoked=True)
    )
    
    return result.rowcount > 0


async def revoke_all_user_tokens(db: AsyncSession, user_id: str) -> int:
    """Revoke all refresh tokens for a user (logout all devices)."""
    result = await db.execute(
        update(RefreshToken)
        .where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            )
        )
        .values(is_revoked=True)
    )
    
    if result.rowcount > 0:
        logger.info("All user tokens revoked", user_id=user_id, count=result.rowcount)
    
    return result.rowcount


async def update_refresh_token_usage(
    db: AsyncSession,
    token: str,
) -> None:
    """Update last used timestamp for refresh token."""
    token_hash = hash_token(token)
    
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(last_used_at=datetime.now(timezone.utc))
    )


async def cleanup_expired_tokens(db: AsyncSession) -> int:
    """Remove expired refresh tokens."""
    result = await db.execute(
        delete(RefreshToken)
        .where(RefreshToken.expires_at < datetime.now(timezone.utc))
    )
    
    if result.rowcount > 0:
        logger.info("Expired tokens cleaned up", count=result.rowcount)
    
    return result.rowcount


# =============================================================================
# Token Blacklist
# =============================================================================

async def blacklist_token(
    db: AsyncSession,
    token_jti: str,
    user_id: str,
    expires_at: datetime,
    reason: Optional[str] = None,
) -> TokenBlacklist:
    """
    Add access token to blacklist.
    
    Args:
        db: Database session
        token_jti: JWT ID
        user_id: User UUID
        expires_at: Token expiration time
        reason: Optional reason for blacklisting
        
    Returns:
        TokenBlacklist: Blacklist record
    """
    blacklist_entry = TokenBlacklist(
        token_jti=token_jti,
        user_id=user_id,
        expires_at=expires_at,
        reason=reason,
    )
    
    db.add(blacklist_entry)
    await db.flush()
    
    logger.info("Token blacklisted", jti=token_jti, user_id=user_id, reason=reason)
    
    return blacklist_entry


async def is_token_blacklisted(
    db: AsyncSession,
    token_jti: str,
) -> bool:
    """Check if access token is blacklisted."""
    result = await db.execute(
        select(TokenBlacklist.id)
        .where(TokenBlacklist.token_jti == token_jti)
    )
    
    return result.scalar_one_or_none() is not None


async def cleanup_expired_blacklist(db: AsyncSession) -> int:
    """Remove expired entries from blacklist."""
    result = await db.execute(
        delete(TokenBlacklist)
        .where(TokenBlacklist.expires_at < datetime.now(timezone.utc))
    )
    
    return result.rowcount


# =============================================================================
# Password Rehashing
# =============================================================================

async def check_and_rehash_password(
    db: AsyncSession,
    user: User,
    plain_password: str,
) -> None:
    """
    Check if password needs rehashing and update if necessary.
    
    Called after successful password verification.
    """
    if user.password_hash and needs_rehash(user.password_hash):
        new_hash = hash_password(plain_password)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(password_hash=new_hash)
        )
        logger.info("User password rehashed", user_id=user.id)
