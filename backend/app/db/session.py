"""
NyayamGPT - Database Session Management (Production-Grade)
==========================================================
Enterprise-level async SQLAlchemy session management with:
- Connection pooling with health checks
- Unit of Work pattern
- Automatic retry with exponential backoff
- Proper transaction management
- Connection lifecycle hooks
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional, TypeVar, Callable
import asyncio
import functools

from sqlalchemy import event, text
from sqlalchemy.exc import (
    DBAPIError,
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from app.core.config import settings
from app.core.logging import logger


T = TypeVar("T")


class DatabaseConfig:
    """Database configuration with environment-aware defaults."""
    
    def __init__(self):
        self.url = self._get_async_url()
        self.is_sqlite = "sqlite" in self.url
        self.is_postgres = "postgresql" in self.url
        
    def _get_async_url(self) -> str:
        """Convert database URL to async-compatible format."""
        url = settings.database_url

        # Log the original URL for troubleshooting startup hangs
        logger.info("Database URL loaded", url=url)
        
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://")
        
        return url
    
    @property
    def pool_settings(self) -> dict:
        """Get pool settings based on environment."""
        if self.is_sqlite:
            return {"poolclass": NullPool}
        
        if settings.environment == "production":
            return {
                "poolclass": AsyncAdaptedQueuePool,
                "pool_size": 20,
                "max_overflow": 40,
                "pool_timeout": 30,
                "pool_recycle": 1800,
                "pool_pre_ping": True,
            }
        elif settings.environment == "staging":
            return {
                "poolclass": AsyncAdaptedQueuePool,
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 30,
                "pool_recycle": 1800,
                "pool_pre_ping": True,
            }
        else:
            return {
                "poolclass": AsyncAdaptedQueuePool,
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "pool_pre_ping": True,
            }
    
    @property
    def engine_settings(self) -> dict:
        """Get engine settings."""
        base = {
            "echo": settings.debug and settings.environment == "development",
            **self.pool_settings,
        }
        
        if self.is_sqlite:
            base["connect_args"] = {"check_same_thread": False}
        
        return base


db_config = DatabaseConfig()


class DatabaseManager:
    """
    Production-grade database connection manager.
    
    Features:
    - Lazy engine initialization
    - Connection health monitoring
    - Graceful shutdown
    - Statistics tracking
    """
    
    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None
    _is_initialized: bool = False
    _lock: asyncio.Lock = asyncio.Lock()
    
    _stats = {
        "connections_created": 0,
        "connections_reused": 0,
        "queries_executed": 0,
        "errors_count": 0,
    }
    
    @classmethod
    async def get_engine(cls) -> AsyncEngine:
        """Get or create the database engine (thread-safe)."""
        if cls._engine is None:
            async with cls._lock:
                if cls._engine is None:
                    logger.info("Creating async engine", url=db_config.url, pool_settings=db_config.pool_settings)
                    cls._engine = create_async_engine(
                        db_config.url,
                        **db_config.engine_settings,
                    )
                    logger.info("Async engine created")
                    cls._setup_engine_events()
                    logger.info(
                        "Database engine created",
                        database_type="sqlite" if db_config.is_sqlite else "postgresql",
                        environment=settings.environment,
                    )
        return cls._engine
    
    @classmethod
    def _setup_engine_events(cls):
        """Setup SQLAlchemy engine events for monitoring."""
        if cls._engine is None:
            return
            
        @event.listens_for(cls._engine.sync_engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            cls._stats["connections_reused"] += 1
        
        @event.listens_for(cls._engine.sync_engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            cls._stats["connections_created"] += 1
    
    @classmethod
    async def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """Get or create the session factory."""
        if cls._session_factory is None:
            engine = await cls.get_engine()
            cls._session_factory = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return cls._session_factory
    
    @classmethod
    async def health_check(cls) -> dict:
        """Perform database health check."""
        try:
            engine = await cls.get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.close()
            
            return {
                "status": "healthy",
                "database_type": "sqlite" if db_config.is_sqlite else "postgresql",
                "stats": cls._stats.copy(),
            }
        except Exception as e:
            cls._stats["errors_count"] += 1
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    @classmethod
    async def initialize(cls) -> None:
        """Initialize database (create tables)."""
        logger.info("DatabaseManager.initialize() called")
        if cls._is_initialized:
            logger.info("Database already initialized")
            return
        
        # Avoid lock if possible, or use a timeout
        try:
            logger.info("Importing models...")
            from app.db.models import Base
            from app.auth.models import User
            logger.info("Models imported")
            
            logger.info("Getting engine...")
            engine = await cls.get_engine()
            logger.info(f"Engine obtained: {engine.url}")
            
            logger.info("Creating tables...")
            logger.info("Running metadata.create_all")
            
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Tables created successfully")
            
            cls._is_initialized = True
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    @classmethod
    async def shutdown(cls) -> None:
        """Gracefully shutdown database connections."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            cls._is_initialized = False
            logger.info("Database connections closed")
    
    @classmethod
    def get_stats(cls) -> dict:
        """Get connection statistics."""
        return cls._stats.copy()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Automatic commit on success, rollback on exception.
    """
    session_factory = await DatabaseManager.get_session_factory()
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except IntegrityError as e:
            await session.rollback()
            logger.warning("Database integrity error", error=str(e))
            raise
        except SQLAlchemyError as e:
            await session.rollback()
            DatabaseManager._stats["errors_count"] += 1
            logger.error("Database error", error=str(e))
            raise
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions outside FastAPI."""
    session_factory = await DatabaseManager.get_session_factory()
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class UnitOfWork:
    """
    Unit of Work pattern for complex transactions.
    
    Usage:
        async with UnitOfWork() as uow:
            user = await create_user(uow.session, user_data)
            await uow.commit()
    """
    
    def __init__(self):
        self._session: Optional[AsyncSession] = None
        self._session_factory: Optional[async_sessionmaker] = None
    
    async def __aenter__(self) -> "UnitOfWork":
        self._session_factory = await DatabaseManager.get_session_factory()
        self._session = self._session_factory()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        await self._session.close()
    
    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork not initialized. Use 'async with'.")
        return self._session
    
    async def commit(self) -> None:
        await self._session.commit()
    
    async def rollback(self) -> None:
        await self._session.rollback()
    
    async def flush(self) -> None:
        await self._session.flush()


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (OperationalError, DBAPIError),
):
    """Decorator for retrying database operations with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            "Database operation failed, retrying",
                            attempt=attempt + 1,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)
                        delay = min(delay * exponential_base, max_delay)
                    else:
                        logger.error(
                            "Database operation failed after retries",
                            attempts=max_retries + 1,
                            error=str(e),
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


# Legacy aliases
async def init_db() -> None:
    """Initialize database tables."""
    await DatabaseManager.initialize()


async def close_db() -> None:
    """Close database connections."""
    await DatabaseManager.shutdown()
