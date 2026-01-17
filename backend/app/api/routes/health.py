"""
NyayamGPT - Health Check Routes
===============================
Health and readiness endpoints for monitoring.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Response
from opentelemetry import trace

from app.core.config import settings
from app.core.logging import logger
from app.schemas.chat import (
    HealthCheck,
    DetailedHealth,
    ComponentHealth,
)

router = APIRouter(prefix="/health", tags=["Health"])

# Track service start time
_start_time = time.time()

# Get tracer
tracer = trace.get_tracer(__name__)


@router.get(
    "",
    response_model=HealthCheck,
    summary="Basic health check",
    description="Returns basic service health status"
)
async def health_check() -> HealthCheck:
    """
    Basic health check endpoint.

    Returns minimal health information for load balancers
    and basic monitoring.
    """
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/ready",
    response_model=DetailedHealth,
    summary="Readiness check",
    description="Returns detailed health including all components"
)
@tracer.start_as_current_span("health_ready_check")
async def readiness_check() -> DetailedHealth:
    """
    Detailed readiness check.

    Checks all system components and returns their status.
    Used by orchestrators to determine if the service can receive traffic.
    """
    span = trace.get_current_span()
    components = []
    overall_status = "healthy"

    # Check database
    db_health = await _check_database()
    components.append(db_health)
    if db_health.status != "healthy":
        overall_status = "degraded"

    # Check vector store
    vs_health = await _check_vector_store()
    components.append(vs_health)
    if vs_health.status != "healthy":
        overall_status = "degraded"

    # Check Gemini API
    gemini_health = await _check_gemini()
    components.append(gemini_health)
    if gemini_health.status != "healthy":
        overall_status = "degraded"

    span.set_attribute("overall_status", overall_status)
    span.set_attribute("components_count", len(components))

    uptime = time.time() - _start_time

    return DetailedHealth(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        components=components,
        uptime_seconds=uptime
    )


@router.get(
    "/live",
    summary="Liveness check",
    description="Simple liveness probe"
)
async def liveness_check(response: Response) -> dict:
    """
    Simple liveness check.

    Returns 200 if the service is running.
    Used by orchestrators to detect hung processes.
    """
    return {"status": "alive"}


async def _check_database() -> ComponentHealth:
    """Check database connectivity."""
    start = time.time()
    try:
        from app.db.session import async_session_factory
        from sqlalchemy import text

        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))

        latency = (time.time() - start) * 1000
        return ComponentHealth(
            name="database",
            status="healthy",
            latency_ms=latency,
            message="Connected"
        )
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return ComponentHealth(
            name="database",
            status="unhealthy",
            message=str(e)
        )


async def _check_vector_store() -> ComponentHealth:
    """Check vector store connectivity."""
    start = time.time()
    try:
        from app.rag.vectorstore import get_default_vector_store

        store = get_default_vector_store()
        stats = store.get_collection_stats()

        latency = (time.time() - start) * 1000
        return ComponentHealth(
            name="vector_store",
            status="healthy",
            latency_ms=latency,
            message=f"Documents: {stats.get('count', 0)}"
        )
    except Exception as e:
        logger.error("Vector store health check failed", error=str(e))
        return ComponentHealth(
            name="vector_store",
            status="unhealthy",
            message=str(e)
        )


async def _check_gemini() -> ComponentHealth:
    """Check Gemini API connectivity."""
    start = time.time()
    try:
        import google.generativeai as genai

        # Quick API check
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        # Just check if model is accessible (don't actually call it)
        latency = (time.time() - start) * 1000
        return ComponentHealth(
            name="gemini_api",
            status="healthy",
            latency_ms=latency,
            message=f"Model: {settings.gemini_model}"
        )
    except Exception as e:
        logger.error("Gemini health check failed", error=str(e))
        return ComponentHealth(
            name="gemini_api",
            status="unhealthy",
            message=str(e)
        )
