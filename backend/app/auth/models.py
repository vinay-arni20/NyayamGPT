"""
NyayamGPT - User Model (Production-Grade)
=========================================
SQLAlchemy model for user authentication with:
- Proper indexes for query optimization
- Soft delete support
- Audit timestamps
- Token blacklist for secure logout
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Index,
    String,
    Text,
    func,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models import Base

if TYPE_CHECKING:
    from app.db.models import ChatSession


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


class UserRole(str, PyEnum):
    """
    User roles for authorization.
    
    - citizen: Default role for general users
    - lawyer: Legal professionals with advanced features
    - judge: Judicial officers with deeper insights
    - admin: System administrators
    """
    CITIZEN = "citizen"
    LAWYER = "lawyer"
    JUDGE = "judge"
    ADMIN = "admin"


class AuthProvider(str, PyEnum):
    """Authentication provider types."""
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class User(Base):
    """
    User model for authentication.
    
    Features:
    - UUID primary key for security
    - Soft delete support (is_deleted flag)
    - Multiple auth provider support (OAuth ready)
    - Proper indexing for performance
    - Audit trail (created_at, updated_at, last_login)
    """
    
    __tablename__ = "users"
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    
    # Profile
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    
    # Authentication
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # Nullable for OAuth users
    )
    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider),
        default=AuthProvider.LOCAL,
        nullable=False,
    )
    auth_provider_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,  # External provider user ID
    )
    
    # Authorization
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.CITIZEN,
        nullable=False,
    )
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    
    # Security
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ChatSession.user_id",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active", "is_deleted"),
        Index("ix_users_provider", "auth_provider", "auth_provider_id"),
        Index("ix_users_role", "role"),
        Index("ix_users_created", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    @property
    def is_locked(self) -> bool:
        """Check if account is temporarily locked."""
        if self.locked_until is None:
            return False
        return datetime.now(self.locked_until.tzinfo) < self.locked_until


class RefreshToken(Base):
    """
    Refresh token storage for token revocation.
    
    Enables:
    - Secure logout (revoke all tokens)
    - Device tracking
    - Token rotation
    """
    
    __tablename__ = "refresh_tokens"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),  # SHA-256 hash
        unique=True,
        nullable=False,
    )
    device_info: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_refresh_tokens_user", "user_id", "is_revoked"),
        Index("ix_refresh_tokens_expires", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"


class TokenBlacklist(Base):
    """
    Token blacklist for invalidated access tokens.
    
    Used for:
    - Immediate logout before token expiry
    - Security revocation
    """
    
    __tablename__ = "token_blacklist"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )
    token_jti: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    blacklisted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    __table_args__ = (
        Index("ix_token_blacklist_jti", "token_jti"),
        Index("ix_token_blacklist_expires", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<TokenBlacklist(jti={self.token_jti})>"
