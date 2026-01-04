"""
Enhanced metrics and SLO tracking for search service.

Implements comprehensive observability with search-specific metrics,
SLO tracking, and performance monitoring.
"""

import logging
import time
from enum import Enum
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, Summary

logger = logging.getLogger(__name__)


class SearchMetrics:
    """
    Search-specific Prometheus metrics.

    Tracks all search operations with detailed labels for analysis.
    """

    search_requests_total = Counter(
        "search_requests_total",
        "Total number of search requests",
        ["endpoint", "query_type", "result_status", "tier"],
    )

    search_latency_seconds = Histogram(
        "search_latency_seconds",
        "Search request latency in seconds",
        ["endpoint", "cache_layer"],
        buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0],
    )

    cache_hits_total = Counter(
        "cache_hits_total",
        "Total cache hits by layer",
        ["cache_layer"],
    )

    cache_misses_total = Counter(
        "cache_misses_total",
        "Total cache misses by layer",
        ["cache_layer"],
    )

    external_api_calls_total = Counter(
        "external_api_calls_total",
        "Total external API calls",
        ["api_name", "status"],
    )

    external_api_latency_seconds = Histogram(
        "external_api_latency_seconds",
        "External API call latency",
        ["api_name"],
        buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
    )

    rate_limit_hits_total = Counter(
        "rate_limit_hits_total",
        "Total rate limit violations",
        ["tier", "endpoint"],
    )

    active_connections = Gauge(
        "active_connections",
        "Current number of active connections",
        ["connection_type"],
    )

    search_results_count = Histogram(
        "search_results_count",
        "Number of results returned per search",
        ["query_type"],
        buckets=[0, 1, 5, 10, 20, 50, 100],
    )

    fuzzy_match_score = Summary(
        "fuzzy_match_score",
        "Fuzzy matching relevance scores",
        ["match_type"],
    )


class SLOMetrics:
    """
    Service Level Objective (SLO) tracking metrics.

    Monitors SLO compliance for availability, latency, and error rates.
    """

    slo_latency_p95_seconds = Gauge(
        "slo_latency_p95_seconds",
        "P95 latency SLO threshold",
        ["endpoint"],
    )

    slo_latency_p99_seconds = Gauge(
        "slo_latency_p99_seconds",
        "P99 latency SLO threshold",
        ["endpoint"],
    )

    slo_error_rate = Gauge(
        "slo_error_rate",
        "Error rate SLO (errors/total requests)",
        ["endpoint"],
    )

    slo_availability = Gauge(
        "slo_availability",
        "Service availability SLO (successful/total requests)",
    )

    slo_budget_remaining = Gauge(
        "slo_budget_remaining",
        "Remaining error budget percentage",
        ["slo_type"],
    )


class CacheLayer(str, Enum):
    """Cache layer identifiers."""

    MEMORY = "memory"
    REDIS = "redis"
    POSTGRES = "postgres"
    API = "api"


class MetricsTracker:
    """
    High-level metrics tracking with automatic SLO calculation.

    Provides convenient methods for tracking operations and
    automatically updating SLO metrics.
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self.metrics = SearchMetrics()
        self.slo = SLOMetrics()

        self._slo_thresholds = {
            "autocomplete_p95": 0.1,
            "autocomplete_p99": 0.25,
            "search_p95": 0.5,
            "search_p99": 1.0,
        }

        self._error_budget_target = 0.999

    def track_search_request(
        self,
        endpoint: str,
        query_type: str,
        tier: str,
        duration_seconds: float,
        cache_layer: str,
        result_status: str,
        result_count: int = 0,
    ) -> None:
        """
        Track a search request with all relevant metrics.

        Args:
            endpoint: API endpoint path
            query_type: Type of query (symbol, name, isin, wkn)
            tier: User tier (anonymous, free, paid)
            duration_seconds: Request duration
            cache_layer: Cache layer that served the request
            result_status: success, not_found, error
            result_count: Number of results returned
        """
        self.metrics.search_requests_total.labels(
            endpoint=endpoint,
            query_type=query_type,
            result_status=result_status,
            tier=tier,
        ).inc()

        self.metrics.search_latency_seconds.labels(
            endpoint=endpoint,
            cache_layer=cache_layer,
        ).observe(duration_seconds)

        if result_count > 0:
            self.metrics.search_results_count.labels(
                query_type=query_type,
            ).observe(result_count)

    def track_cache_operation(self, cache_layer: CacheLayer, hit: bool) -> None:
        """
        Track cache hit or miss.

        Args:
            cache_layer: Cache layer (memory, redis, postgres)
            hit: True for cache hit, False for miss
        """
        if hit:
            self.metrics.cache_hits_total.labels(
                cache_layer=cache_layer.value,
            ).inc()
        else:
            self.metrics.cache_misses_total.labels(
                cache_layer=cache_layer.value,
            ).inc()

    def track_external_api_call(
        self, api_name: str, duration_seconds: float, success: bool
    ) -> None:
        """
        Track external API call.

        Args:
            api_name: Name of external API (yahoo_finance, etc.)
            duration_seconds: Call duration
            success: True if successful, False if error
        """
        status = "success" if success else "error"

        self.metrics.external_api_calls_total.labels(
            api_name=api_name,
            status=status,
        ).inc()

        self.metrics.external_api_latency_seconds.labels(
            api_name=api_name,
        ).observe(duration_seconds)

    def track_rate_limit_hit(self, tier: str, endpoint: str) -> None:
        """
        Track rate limit violation.

        Args:
            tier: User tier
            endpoint: Endpoint that was rate limited
        """
        self.metrics.rate_limit_hits_total.labels(
            tier=tier,
            endpoint=endpoint,
        ).inc()

    def update_connection_count(self, connection_type: str, count: int) -> None:
        """
        Update active connection gauge.

        Args:
            connection_type: Type of connection (database, redis, etc.)
            count: Current count
        """
        self.metrics.active_connections.labels(
            connection_type=connection_type,
        ).set(count)

    def track_fuzzy_match(self, match_type: str, score: float) -> None:
        """
        Track fuzzy matching score.

        Args:
            match_type: Type of match (exact, prefix, fuzzy, etc.)
            score: Relevance score (0-1)
        """
        self.metrics.fuzzy_match_score.labels(
            match_type=match_type,
        ).observe(score)

    def update_slo_metrics(
        self,
        endpoint: str,
        p95_latency: float,
        p99_latency: float,
        error_rate: float,
    ) -> None:
        """
        Update SLO tracking metrics.

        Args:
            endpoint: API endpoint
            p95_latency: P95 latency in seconds
            p99_latency: P99 latency in seconds
            error_rate: Error rate (0-1)
        """
        self.slo.slo_latency_p95_seconds.labels(endpoint=endpoint).set(p95_latency)
        self.slo.slo_latency_p99_seconds.labels(endpoint=endpoint).set(p99_latency)
        self.slo.slo_error_rate.labels(endpoint=endpoint).set(error_rate)

        availability = 1.0 - error_rate
        self.slo.slo_availability.set(availability)

        budget_remaining = max(0, (availability - self._error_budget_target) * 100)
        self.slo.slo_budget_remaining.labels(slo_type="availability").set(
            budget_remaining
        )


_metrics_tracker = MetricsTracker()


def get_metrics_tracker() -> MetricsTracker:
    """Get global metrics tracker instance."""
    return _metrics_tracker


class SearchTimer:
    """
    Context manager for timing search operations.

    Automatically tracks duration and updates metrics.
    """

    def __init__(
        self,
        endpoint: str,
        query_type: str,
        tier: str = "anonymous",
    ):
        """
        Initialize timer.

        Args:
            endpoint: API endpoint
            query_type: Query type
            tier: User tier
        """
        self.endpoint = endpoint
        self.query_type = query_type
        self.tier = tier
        self.start_time: Optional[float] = None
        self.cache_layer = CacheLayer.API.value
        self.result_status = "success"
        self.result_count = 0

    def __enter__(self) -> "SearchTimer":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop timing and record metrics."""
        if self.start_time is None:
            return

        duration = time.time() - self.start_time

        if exc_type is not None:
            self.result_status = "error"

        tracker = get_metrics_tracker()
        tracker.track_search_request(
            endpoint=self.endpoint,
            query_type=self.query_type,
            tier=self.tier,
            duration_seconds=duration,
            cache_layer=self.cache_layer,
            result_status=self.result_status,
            result_count=self.result_count,
        )
