"""
NyayamGPT - Database Session Management
=======================================
SQLAlchemy async session configuration and dependency injection.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.logging import logger


def get_async_database_url() -> str:
    """
    Convert database URL to async-compatible format.
    
    Returns:
        str: Async-compatible database URL
    """
    url = settings.database_url
    
    # Handle SQLite
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    # Handle PostgreSQL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://")
    
    return url


def create_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine.
    
    Returns:
        AsyncEngine: Configured async database engine
    """
    database_url = get_async_database_url()
    
    # SQLite specific configuration
    if "sqlite" in database_url:
        engine = create_async_engine(
            database_url,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL configuration
        engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    
    logger.info(
        "Database engine created",
        database_type="sqlite" if "sqlite" in database_url else "postgresql"
    )
    
    return engine


# Global engine instance
engine = create_engine()

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database sessions.
    
    Yields:
        AsyncSession: Database session that auto-closes after use
        
    Example:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of FastAPI dependencies.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables.
    
    Creates all tables defined in the models if they don't exist.
    """
    from app.db.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables initialized")


async def close_db() -> None:
    """
    Close database connections.
    
    Should be called during application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
