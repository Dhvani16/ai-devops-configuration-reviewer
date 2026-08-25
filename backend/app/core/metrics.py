"""Prometheus metrics counters and histograms."""

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests by method, endpoint, and status",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

ANALYSES_TOTAL = Counter(
    "analyses_total",
    "Total number of analyses completed",
)

AI_FAILURES_TOTAL = Counter(
    "ai_provider_failures_total",
    "Total number of AI provider failures",
)
