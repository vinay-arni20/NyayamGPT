"""
NyayamGPT - Logging Configuration Module
========================================
Structured logging setup for the application with JSON formatting
for production and colored console output for development.
Includes mode-aware logging and request tracing.
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, TypeVar

import structlog
from structlog.types import Processor

from app.core.config import settings


# Context variables for request tracking
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
session_id_ctx: ContextVar[str] = ContextVar("session_id", default="")
mode_ctx: ContextVar[str] = ContextVar("mode", default="normal")


def add_timestamp(
    logger: logging.Logger, 
    method_name: str, 
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO format timestamp to log entries."""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def add_app_context(
    logger: logging.Logger, 
    method_name: str, 
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add application context to log entries."""
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["environment"] = settings.environment
    return event_dict


def add_request_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add request-scoped context to log entries."""
    request_id = request_id_ctx.get()
    user_id = user_id_ctx.get()
    session_id = session_id_ctx.get()
    mode = mode_ctx.get()
    
    if request_id:
        event_dict["request_id"] = request_id
    if user_id:
        event_dict["user_id"] = user_id
    if session_id:
        event_dict["session_id"] = session_id
    if mode:
        event_dict["mode"] = mode
        
    return event_dict


def setup_logging() -> None:
    """
    Configure structured logging for the application.
    
    In development: Colored console output with pretty printing
    In production: JSON formatted logs for log aggregation systems
    """
    
    # Shared processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        add_timestamp,
        add_app_context,
        add_request_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.environment == "production":
        # Production: JSON output
        processors: list[Processor] = shared_processors + [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development: Colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name, typically __name__
        
    Returns:
        structlog.BoundLogger: Configured logger instance
    """
    return structlog.get_logger(name)


def set_request_context(
    request_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    mode: str | None = None
) -> None:
    """
    Set request-scoped context for logging.
    
    Args:
        request_id: Unique request identifier
        user_id: User ID for the request
        session_id: Session ID for the request
        mode: Chat mode (normal, lawyer, qa, web, deep)
    """
    if request_id:
        request_id_ctx.set(request_id)
    if user_id:
        user_id_ctx.set(user_id)
    if session_id:
        session_id_ctx.set(session_id)
    if mode:
        mode_ctx.set(mode)


def clear_request_context() -> None:
    """Clear all request-scoped context."""
    request_id_ctx.set("")
    user_id_ctx.set("")
    session_id_ctx.set("")
    mode_ctx.set("normal")


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def log_execution(operation: str) -> Callable[[F], F]:
    """
    Decorator to log function execution with timing.
    
    Args:
        operation: Name of the operation being logged
        
    Returns:
        Decorated function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = datetime.utcnow()
            logger.info(f"[{operation}] Starting...")
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                logger.info(f"[{operation}] Completed", duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                logger.error(f"[{operation}] Failed", error=str(e), duration_ms=duration_ms)
                raise
        
        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = datetime.utcnow()
            logger.info(f"[{operation}] Starting...")
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                logger.info(f"[{operation}] Completed", duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
                logger.error(f"[{operation}] Failed", error=str(e), duration_ms=duration_ms)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


# Initialize logging on module import
setup_logging()

# Default logger instance
logger = get_logger("nyayamgpt")

# Export context functions and variables
__all__ = [
    "logger",
    "get_logger",
    "setup_logging",
    "set_request_context",
    "clear_request_context",
    "generate_request_id",
    "log_execution",
    "request_id_ctx",
    "user_id_ctx",
    "session_id_ctx",
    "mode_ctx",
]
