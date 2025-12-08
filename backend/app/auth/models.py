"""
NyayamGPT - User Model
======================
SQLAlchemy model for user authentication and authorization.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models import Base


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


class User(Base):
    """
    User model for authentication.
    
    Attributes:
        id: Unique user identifier (UUID)
        full_name: User's full name
        email: Unique email address
        phone: Optional phone number
        password_hash: Bcrypt hashed password
        role: User role (citizen, lawyer, judge, admin)
        preferred_language: Preferred language for responses
        is_active: Whether the account is active
        is_verified: Whether email is verified
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        last_login: Last login timestamp
    """
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.CITIZEN,
        nullable=False
    )
    preferred_language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    chat_sessions = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ChatSession.user_id"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
