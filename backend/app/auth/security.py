"""
NyayamGPT - Security Utilities (Production-Grade)
=================================================
Enterprise-level security with:
- Argon2id password hashing (OWASP recommended)
- JWT with JTI for token revocation
- Secure token generation
- Constant-time comparison
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4
import hashlib
import secrets

try:
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
    )
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

import bcrypt
import jwt

from app.core.config import settings
from app.core.logging import logger


# =============================================================================
# Configuration
# =============================================================================

JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


# =============================================================================
# Password Hashing (Argon2id with bcrypt fallback)
# =============================================================================

if ARGON2_AVAILABLE:
    # Argon2id configuration (OWASP recommended)
    _password_hasher = PasswordHasher(
        time_cost=3,           # Number of iterations
        memory_cost=65536,     # 64 MB memory
        parallelism=4,         # Number of parallel threads
        hash_len=32,           # Hash output length
        salt_len=16,           # Salt length
        type=Type.ID,          # Argon2id variant (hybrid)
    )
    
    def hash_password(password: str) -> str:
        """
        Hash password using Argon2id (OWASP recommended).
        
        Args:
            password: Plain text password
            
        Returns:
            str: Argon2id hash
        """
        try:
            return _password_hasher.hash(password)
        except Exception as e:
            logger.error("Password hashing failed", error=str(e))
            raise ValueError("Password hashing failed")
    
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against Argon2id or bcrypt hash.
        
        Supports:
        - Argon2id hashes (new)
        - bcrypt hashes (legacy migration)
        
        Args:
            plain_password: Plain text password
            hashed_password: Stored hash
            
        Returns:
            bool: True if password matches
        """
        try:
            # Check if it's a bcrypt hash (legacy)
            if hashed_password.startswith("$2"):
                return _verify_bcrypt(plain_password, hashed_password)
            
            # Argon2id verification
            _password_hasher.verify(hashed_password, plain_password)
            return True
            
        except VerifyMismatchError:
            return False
        except (VerificationError, InvalidHashError) as e:
            logger.warning("Password verification error", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected password verification error", error=str(e))
            return False
    
    def needs_rehash(hashed_password: str) -> bool:
        """
        Check if password hash needs to be rehashed.
        
        Returns True if:
        - Using old bcrypt hash
        - Argon2 parameters have changed
        
        Args:
            hashed_password: Stored hash
            
        Returns:
            bool: True if rehash is needed
        """
        # bcrypt hashes should be migrated
        if hashed_password.startswith("$2"):
            return True
        
        try:
            return _password_hasher.check_needs_rehash(hashed_password)
        except Exception:
            return True

else:
    # Fallback to bcrypt if argon2 not available
    logger.warning("argon2-cffi not installed, using bcrypt fallback")
    
    def hash_password(password: str) -> str:
        """Hash password using bcrypt (fallback)."""
        password_bytes = password.encode('utf-8')[:72]  # bcrypt limit
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash."""
        return _verify_bcrypt(plain_password, hashed_password)
    
    def needs_rehash(hashed_password: str) -> bool:
        """bcrypt doesn't support automatic rehashing detection."""
        return False


def _verify_bcrypt(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash (for legacy support)."""
    try:
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error("bcrypt verification error", error=str(e))
        return False


# =============================================================================
# JWT Token Management
# =============================================================================

def generate_jti() -> str:
    """Generate unique JWT ID for token revocation support."""
    return str(uuid4())


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (must include 'sub' for user ID)
        expires_delta: Optional custom expiration
        jti: Optional JWT ID (auto-generated if not provided)
        
    Returns:
        str: Encoded JWT access token
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,  # Not valid before
        "type": "access",
        "jti": jti or generate_jti(),
    })
    
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Payload data (must include 'sub' for user ID)
        expires_delta: Optional custom expiration
        jti: Optional JWT ID
        
    Returns:
        str: Encoded JWT refresh token
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    
    expire = now + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "type": "refresh",
        "jti": jti or generate_jti(),
    })
    
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(
    token: str,
    token_type: str = "access",
    verify_exp: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        token_type: Expected type ('access' or 'refresh')
        verify_exp: Whether to verify expiration
        
    Returns:
        dict: Decoded payload or None if invalid
    """
    try:
        options = {"verify_exp": verify_exp}
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options=options,
        )
        
        # Validate token type
        if payload.get("type") != token_type:
            logger.warning(
                "Token type mismatch",
                expected=token_type,
                got=payload.get("type"),
            )
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e))
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get expiration time from token without validation."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_jti(token: str) -> Optional[str]:
    """Get JTI from token without validation."""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("jti")
    except jwt.InvalidTokenError:
        return None


def get_token_expiry_seconds() -> int:
    """Get access token expiry in seconds."""
    return ACCESS_TOKEN_EXPIRE_MINUTES * 60


def get_refresh_token_expiry_seconds() -> int:
    """Get refresh token expiry in seconds."""
    return REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


# =============================================================================
# Token Hashing (for storage)
# =============================================================================

def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.
    
    Uses SHA-256 for fast, collision-resistant hashing.
    
    Args:
        token: Token to hash
        
    Returns:
        str: Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(token.encode()).hexdigest()


# =============================================================================
# Secure Token Generation
# =============================================================================

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Number of bytes (output will be 2x in hex)
        
    Returns:
        str: Hex-encoded random token
    """
    return secrets.token_hex(length)


def generate_verification_code(length: int = 6) -> str:
    """
    Generate a numeric verification code.
    
    Args:
        length: Number of digits
        
    Returns:
        str: Numeric verification code
    """
    return "".join(secrets.choice("0123456789") for _ in range(length))


# =============================================================================
# Constant-Time Comparison
# =============================================================================

def secure_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        bool: True if strings are equal
    """
    return secrets.compare_digest(a.encode(), b.encode())
