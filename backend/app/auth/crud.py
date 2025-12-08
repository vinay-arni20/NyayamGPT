"""
NyayamGPT - Authentication CRUD Operations
==========================================
Database operations for user management.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User, UserRole
from app.auth.schemas import UserCreate
from app.auth.security import hash_password
from app.core.logging import logger


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email address."""
    result = await db.execute(
        select(User).where(User.email == email.lower())
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
    """
    Create a new user.
    
    Args:
        db: Database session
        user_data: User creation data
        
    Returns:
        User: Created user
    """
    user = User(
        full_name=user_data.full_name,
        email=user_data.email.lower(),
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        preferred_language=user_data.preferred_language,
        is_active=True,
        is_verified=False
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(
        "User created",
        user_id=user.id,
        email=user.email,
        role=user.role.value
    )
    
    return user


async def update_last_login(db: AsyncSession, user_id: str) -> None:
    """Update user's last login timestamp."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_login=datetime.now(timezone.utc))
    )
    await db.commit()


async def update_user_password(
    db: AsyncSession,
    user_id: str,
    new_password_hash: str
) -> None:
    """Update user's password."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=new_password_hash)
    )
    await db.commit()
    
    logger.info("Password updated", user_id=user_id)


async def update_user_profile(
    db: AsyncSession,
    user_id: str,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    preferred_language: Optional[str] = None
) -> Optional[User]:
    """Update user profile fields."""
    update_data = {}
    
    if full_name is not None:
        update_data["full_name"] = full_name
    if phone is not None:
        update_data["phone"] = phone
    if preferred_language is not None:
        update_data["preferred_language"] = preferred_language
    
    if update_data:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**update_data)
        )
        await db.commit()
    
    return await get_user_by_id(db, user_id)


async def deactivate_user(db: AsyncSession, user_id: str) -> None:
    """Deactivate a user account."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
    await db.commit()
    
    logger.info("User deactivated", user_id=user_id)


async def verify_user_email(db: AsyncSession, user_id: str) -> None:
    """Mark user's email as verified."""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_verified=True)
    )
    await db.commit()
    
    logger.info("User email verified", user_id=user_id)


async def check_email_exists(db: AsyncSession, email: str) -> bool:
    """Check if email is already registered."""
    result = await db.execute(
        select(User.id).where(User.email == email.lower())
    )
    return result.scalar_one_or_none() is not None
