from prometheus_client import Counter, Histogram, Gauge
import time


emails_sent_total = Counter(
    "notification_emails_sent_total",
    "Total number of emails sent",
    ["notification_type", "status"],
)

price_alerts_triggered_total = Counter(
    "notification_price_alerts_triggered_total",
    "Total number of price alerts triggered",
    ["symbol", "direction"],
)

email_delivery_duration_seconds = Histogram(
    "notification_email_delivery_duration_seconds",
    "Email delivery duration in seconds",
    ["notification_type"],
)

notification_failures_total = Counter(
    "notification_failures_total",
    "Total number of notification failures",
    ["notification_type", "error_type"],
)

active_price_alerts = Gauge(
    "notification_active_price_alerts",
    "Number of active price alerts being monitored",
)

watchlist_items_checked_total = Counter(
    "notification_watchlist_items_checked_total",
    "Total number of watchlist items checked for alerts",
)


class MetricsTracker:
    """Helper class for tracking metrics with timing."""

    def __init__(self, notification_type: str):
        self.notification_type = notification_type
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            email_delivery_duration_seconds.labels(
                notification_type=self.notification_type
            ).observe(duration)


def record_email_sent(notification_type: str, success: bool):
    """Record email sent metric."""
    status = "success" if success else "failed"
    emails_sent_total.labels(
        notification_type=notification_type, status=status
    ).inc()


def record_price_alert(symbol: str, direction: str):
    """Record price alert triggered."""
    price_alerts_triggered_total.labels(symbol=symbol, direction=direction).inc()


def record_failure(notification_type: str, error_type: str):
    """Record notification failure."""
    notification_failures_total.labels(
        notification_type=notification_type, error_type=error_type
    ).inc()
