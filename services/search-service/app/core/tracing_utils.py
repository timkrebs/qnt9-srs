"""
Enhanced tracing utilities for distributed tracing.

Provides custom spans and trace enrichment for detailed
performance analysis and debugging.
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)


tracer = trace.get_tracer(__name__)


@contextmanager
def trace_operation(
    operation_name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[trace.Span, None, None]:
    """
    Context manager for tracing operations with attributes.

    Args:
        operation_name: Name of operation
        attributes: Optional attributes to add to span

    Yields:
        Active span

    Example:
        with trace_operation("database_query", {"table": "stocks"}):
            results = await session.execute(query)
    """
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def add_span_attributes(attributes: dict[str, Any]) -> None:
    """
    Add attributes to current active span.

    Args:
        attributes: Attributes to add
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> None:
    """
    Add event to current active span.

    Args:
        name: Event name
        attributes: Optional event attributes
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


@contextmanager
def trace_cache_operation(
    cache_layer: str,
    operation: str,
    key: str,
) -> Generator[trace.Span, None, None]:
    """
    Trace cache operation.

    Args:
        cache_layer: Cache layer (memory, redis, postgres)
        operation: Operation (get, set, delete)
        key: Cache key

    Yields:
        Active span
    """
    with trace_operation(
        f"cache.{operation}",
        {
            "cache.layer": cache_layer,
            "cache.operation": operation,
            "cache.key": key,
        },
    ) as span:
        yield span


@contextmanager
def trace_database_query(
    query_type: str,
    table: str | None = None,
) -> Generator[trace.Span, None, None]:
    """
    Trace database query.

    Args:
        query_type: Query type (select, insert, update, delete)
        table: Optional table name

    Yields:
        Active span
    """
    attributes = {
        "db.system": "postgresql",
        "db.operation": query_type,
    }

    if table:
        attributes["db.sql.table"] = table

    with trace_operation(f"db.{query_type}", attributes) as span:
        yield span


@contextmanager
def trace_external_api_call(
    service_name: str,
    endpoint: str,
    method: str = "GET",
) -> Generator[trace.Span, None, None]:
    """
    Trace external API call.

    Args:
        service_name: External service name
        endpoint: API endpoint
        method: HTTP method

    Yields:
        Active span
    """
    with trace_operation(
        f"external.{service_name}",
        {
            "http.method": method,
            "http.url": endpoint,
            "peer.service": service_name,
        },
    ) as span:
        yield span


@contextmanager
def trace_search_operation(
    query: str,
    query_type: str,
    cache_layer: str | None = None,
) -> Generator[trace.Span, None, None]:
    """
    Trace search operation with query details.

    Args:
        query: Search query
        query_type: Query type (symbol, isin, wkn, name)
        cache_layer: Cache layer if hit (memory, redis, postgres, api)

    Yields:
        Active span
    """
    attributes = {
        "search.query": query,
        "search.type": query_type,
    }

    if cache_layer:
        attributes["search.cache_layer"] = cache_layer

    with trace_operation("search.execute", attributes) as span:
        yield span


def record_search_result(
    result_count: int,
    latency_ms: float,
    cache_hit: bool = False,
) -> None:
    """
    Record search result metrics in current span.

    Args:
        result_count: Number of results found
        latency_ms: Query latency in milliseconds
        cache_hit: Whether result was from cache
    """
    add_span_attributes(
        {
            "search.result_count": result_count,
            "search.latency_ms": latency_ms,
            "search.cache_hit": cache_hit,
        }
    )


def record_error(
    error_type: str,
    error_message: str,
) -> None:
    """
    Record error in current span.

    Args:
        error_type: Error type/category
        error_message: Error message
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.ERROR, error_message))
        span.set_attribute("error.type", error_type)
        span.set_attribute("error.message", error_message)
