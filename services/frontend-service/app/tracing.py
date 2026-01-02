"""
OpenTelemetry instrumentation configuration for FastAPI services.

Provides automatic tracing for HTTP requests and external API calls.
"""

import os
from typing import Optional

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_opentelemetry(
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    enable_tracing: bool = True,
) -> None:
    """
    Configure OpenTelemetry instrumentation for the service.

    Args:
        service_name: Name of the service (e.g., "auth-service")
        service_version: Version of the service
        otlp_endpoint: OTLP endpoint URL (defaults to Grafana Agent in Kubernetes)
        enable_tracing: Whether to enable tracing (can be disabled for local dev)
    """
    if not enable_tracing:
        return

    # Default to Grafana Agent service in Kubernetes
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "grafana-agent.qnt9-monitoring.svc.cluster.local:4317"
        )

    # Create resource with service information
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
            "k8s.cluster.name": "qnt9-aks",
        }
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Create OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )

    # Add batch span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Instrument httpx for external API calls
    HTTPXClientInstrumentor().instrument()


def instrument_fastapi(app: FastAPI, excluded_urls: Optional[str] = None) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
        excluded_urls: Comma-separated list of URL patterns to exclude from tracing
    """
    if excluded_urls is None:
        excluded_urls = "/health,/metrics"

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=excluded_urls,
        tracer_provider=trace.get_tracer_provider(),
    )
