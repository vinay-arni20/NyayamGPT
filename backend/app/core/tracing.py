"""
NyayamGPT - Tracing Setup Module
================================
OpenTelemetry tracing configuration for the application.
"""

import socket

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

from app.core.config import settings
from app.core.logging import logger


def is_collector_available(host: str = "localhost", port: int = 4318, timeout: float = 0.5) -> bool:
    """Check if the OTLP collector is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def setup_tracing() -> None:
    """
    Configure OpenTelemetry tracing for the application.
    
    Sets up:
    - OTLP exporter to send traces to AI Toolkit or other collectors
    - Service resource attributes
    - Batch span processor for efficient trace export
    """
    # Create resource with service information
    resource = Resource.create({
        SERVICE_NAME: settings.app_name,
        SERVICE_VERSION: settings.app_version,
        "deployment.environment": settings.environment,
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Check if collector is available before configuring exporter
    if not is_collector_available():
        logger.info(
            "OTLP collector not available, tracing will be local only",
            endpoint="http://localhost:4318/v1/traces"
        )
        trace.set_tracer_provider(provider)
        return
    
    # Configure OTLP exporter
    # AI Toolkit's OTLP endpoint is http://localhost:4318 (HTTP)
    otlp_endpoint = "http://localhost:4318/v1/traces"
    
    try:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        
        # Add batch processor for efficient export
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        # Set as global provider
        trace.set_tracer_provider(provider)
        
        logger.info(
            "Tracing configured",
            endpoint=otlp_endpoint,
            service=settings.app_name
        )
    except Exception as e:
        logger.warning(
            "Failed to configure OTLP exporter, tracing disabled",
            error=str(e)
        )
        # Still set the provider for local tracing
        trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for the given name.
    
    Args:
        name: Tracer name (typically __name__)
        
    Returns:
        trace.Tracer: Tracer instance
    """
    return trace.get_tracer(name)
