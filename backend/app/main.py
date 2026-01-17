"""
NyayamGPT - FastAPI Main Application
====================================
Main application entry point with full configuration, tracing, and caching.
"""

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.config import settings
from app.core.logging import (
    logger,
    set_request_context,
    clear_request_context,
    generate_request_id,
)
from app.core.tracing import setup_tracing
from app.core.limiter import limiter
from app.core.cache import get_cache_service, close_cache_service
from app.db.session import DatabaseManager
from app.rag.indexing import initialize_vector_store
from app.api.routes import chat, health, documents
from app.auth.routes import router as auth_router



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler.
    
    Handles startup and shutdown events:
    - Startup: Initialize database, cache, vector store, and tracing
    - Shutdown: Close all connections
    """
    # Startup
    logger.info(
        "Starting NyayamGPT",
        version=settings.app_version,
        environment=settings.environment
    )
    
    # Setup tracing
    setup_tracing()
    logger.info("Tracing setup complete")
    
    # Initialize database
    logger.info("Initializing database...")
    await DatabaseManager.initialize()
    logger.info("Database initialized")
    
    # Database health check
    db_health = await DatabaseManager.health_check()
    if db_health["status"] == "healthy":
        logger.info("Database connection healthy", **db_health)
    else:
        logger.warning("Database health check failed", **db_health)
    
    # Initialize cache
    cache = await get_cache_service()
    if cache.is_connected:
        logger.info("Cache service initialized")
    else:
        logger.warning("Cache service unavailable, running without caching")
    
    # Initialize vector store in background to not block startup
    try:
        # Run in background task
        import asyncio
        asyncio.create_task(initialize_vector_store())
        logger.info("Vector store initialization started in background")
    except Exception as e:
        logger.warning(f"Vector store initialization warning: {e}")
    
    logger.info("NyayamGPT started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NyayamGPT")
    await close_cache_service()
    await DatabaseManager.shutdown()
    logger.info("NyayamGPT shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    🏛️ NyayamGPT - Indian Legal AI Assistant
    
    A multilingual, citation-backed legal assistant for India using:
    - Agentic RAG with LangGraph
    - Google Gemini for reasoning
    - Validator loops for accuracy
    - Chroma/FAISS vector store
    
    Features:
    - Explains Indian laws in simple language
    - Provides exact IPC/CrPC citations
    - Never hallucinates legal sections
    - Uses retrieval + reasoning + verification
    """,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Set up rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# =============================================================================
# Request Context Middleware
# =============================================================================

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Add request context for logging and tracing."""
    # Generate request ID
    request_id = request.headers.get("X-Request-ID", generate_request_id())
    
    # Set context for logging
    set_request_context(
        request_id=request_id,
        user_id=getattr(request.state, "user_id", None),
    )
    
    # Track request timing
    start_time = time.time()
    
    try:
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log request completion
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Request completed",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Request failed",
            path=request.url.path,
            method=request.method,
            error=str(e),
            duration_ms=round(duration_ms, 2),
        )
        raise
    finally:
        clear_request_context()

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Include routers
app.include_router(health.router)
app.include_router(auth_router)
app.include_router(chat.router)
app.include_router(documents.router, prefix="/documents", tags=["Documents"])



# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None
        }
    )


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Indian Legal AI Assistant",
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health"
    }


# =============================================================================
# OpenAPI Customization
# =============================================================================

def custom_openapi():
    """Customize OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# =============================================================================
# Development Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
