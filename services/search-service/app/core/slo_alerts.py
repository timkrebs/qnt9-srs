"""
SLO (Service Level Objective) alerting configuration.

Defines alerting rules for Prometheus to monitor SLO compliance
and error budget consumption.
"""

SLO_ALERTING_RULES = """
groups:
  - name: search_service_slo
    interval: 30s
    rules:
      # Availability SLO: 99.9% uptime (error rate < 0.1%)
      - alert: SLOAvailabilityBreach
        expr: |
          (
            sum(rate(search_requests_total{result_status="success"}[5m])) 
            / 
            sum(rate(search_requests_total[5m]))
          ) < 0.999
        for: 5m
        labels:
          severity: critical
          slo_type: availability
        annotations:
          summary: "Availability SLO breached (< 99.9%)"
          description: "Current availability: {{ $value | humanizePercentage }}"
          runbook_url: "https://runbooks.example.com/slo-availability"
      
      # Latency SLO: P95 < 500ms for search
      - alert: SLOLatencyP95Breach
        expr: |
          histogram_quantile(0.95, 
            rate(search_latency_seconds_bucket{endpoint="/api/v1/search"}[5m])
          ) > 0.5
        for: 5m
        labels:
          severity: warning
          slo_type: latency
          percentile: p95
        annotations:
          summary: "P95 latency SLO breached (> 500ms)"
          description: "Current P95 latency: {{ $value | humanizeDuration }}"
          runbook_url: "https://runbooks.example.com/slo-latency"
      
      # Latency SLO: P99 < 1000ms for search
      - alert: SLOLatencyP99Breach
        expr: |
          histogram_quantile(0.99, 
            rate(search_latency_seconds_bucket{endpoint="/api/v1/search"}[5m])
          ) > 1.0
        for: 5m
        labels:
          severity: warning
          slo_type: latency
          percentile: p99
        annotations:
          summary: "P99 latency SLO breached (> 1000ms)"
          description: "Current P99 latency: {{ $value | humanizeDuration }}"
          runbook_url: "https://runbooks.example.com/slo-latency"
      
      # Autocomplete Latency SLO: P95 < 100ms
      - alert: SLOAutocompleteLatencyP95Breach
        expr: |
          histogram_quantile(0.95, 
            rate(search_latency_seconds_bucket{endpoint="/api/v1/autocomplete"}[5m])
          ) > 0.1
        for: 5m
        labels:
          severity: warning
          slo_type: latency
          service: autocomplete
          percentile: p95
        annotations:
          summary: "Autocomplete P95 latency SLO breached (> 100ms)"
          description: "Current P95 latency: {{ $value | humanizeDuration }}"
          runbook_url: "https://runbooks.example.com/slo-autocomplete-latency"
      
      # Autocomplete Latency SLO: P99 < 250ms
      - alert: SLOAutocompleteLatencyP99Breach
        expr: |
          histogram_quantile(0.99, 
            rate(search_latency_seconds_bucket{endpoint="/api/v1/autocomplete"}[5m])
          ) > 0.25
        for: 5m
        labels:
          severity: warning
          slo_type: latency
          service: autocomplete
          percentile: p99
        annotations:
          summary: "Autocomplete P99 latency SLO breached (> 250ms)"
          description: "Current P99 latency: {{ $value | humanizeDuration }}"
          runbook_url: "https://runbooks.example.com/slo-autocomplete-latency"
      
      # Error Budget: Alert when 50% consumed
      - alert: SLOErrorBudget50PercentConsumed
        expr: slo_budget_remaining{slo_type="availability"} < 50
        for: 10m
        labels:
          severity: warning
          slo_type: error_budget
        annotations:
          summary: "Error budget 50% consumed"
          description: "Only {{ $value }}% of error budget remaining"
          runbook_url: "https://runbooks.example.com/slo-error-budget"
      
      # Error Budget: Alert when 75% consumed
      - alert: SLOErrorBudget75PercentConsumed
        expr: slo_budget_remaining{slo_type="availability"} < 25
        for: 5m
        labels:
          severity: warning
          slo_type: error_budget
        annotations:
          summary: "Error budget 75% consumed (CRITICAL)"
          description: "Only {{ $value }}% of error budget remaining"
          runbook_url: "https://runbooks.example.com/slo-error-budget"
      
      # Error Budget: Alert when fully exhausted
      - alert: SLOErrorBudgetExhausted
        expr: slo_budget_remaining{slo_type="availability"} <= 0
        for: 1m
        labels:
          severity: critical
          slo_type: error_budget
        annotations:
          summary: "Error budget EXHAUSTED"
          description: "Error budget fully consumed - incident response required"
          runbook_url: "https://runbooks.example.com/slo-error-budget-exhausted"
      
      # Cache Hit Rate SLO: > 70%
      - alert: SLOCacheHitRateLow
        expr: |
          (
            sum(rate(cache_hits_total[5m])) 
            / 
            (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
          ) < 0.7
        for: 10m
        labels:
          severity: warning
          slo_type: cache_performance
        annotations:
          summary: "Cache hit rate below target (< 70%)"
          description: "Current hit rate: {{ $value | humanizePercentage }}"
          runbook_url: "https://runbooks.example.com/slo-cache-performance"
      
      # Redis Availability
      - alert: RedisUnavailable
        expr: up{job="search-service-redis"} == 0
        for: 1m
        labels:
          severity: critical
          component: redis
        annotations:
          summary: "Redis is unavailable"
          description: "Redis connection failed - fallback to local rate limiting"
          runbook_url: "https://runbooks.example.com/redis-unavailable"
      
      # Meilisearch Availability
      - alert: MeilisearchUnavailable
        expr: up{job="search-service-meilisearch"} == 0
        for: 1m
        labels:
          severity: warning
          component: meilisearch
        annotations:
          summary: "Meilisearch is unavailable"
          description: "Autocomplete service degraded"
          runbook_url: "https://runbooks.example.com/meilisearch-unavailable"
      
      # Rate Limit Abuse
      - alert: HighRateLimitViolations
        expr: |
          sum(rate(rate_limit_hits_total[5m])) by (tier) > 10
        for: 5m
        labels:
          severity: warning
          security: rate_limiting
        annotations:
          summary: "High rate limit violations for tier {{ $labels.tier }}"
          description: "{{ $value }} violations/sec"
          runbook_url: "https://runbooks.example.com/rate-limit-abuse"
      
      # External API Latency
      - alert: ExternalAPIHighLatency
        expr: |
          histogram_quantile(0.95,
            rate(external_api_latency_seconds_bucket[5m])
          ) > 5.0
        for: 5m
        labels:
          severity: warning
          component: external_api
        annotations:
          summary: "High latency for external API {{ $labels.api_name }}"
          description: "P95 latency: {{ $value | humanizeDuration }}"
          runbook_url: "https://runbooks.example.com/external-api-latency"
"""


SLO_RECORDING_RULES = """
groups:
  - name: search_service_slo_recording
    interval: 30s
    rules:
      # Record availability over multiple windows
      - record: slo:availability:5m
        expr: |
          sum(rate(search_requests_total{result_status="success"}[5m])) 
          / 
          sum(rate(search_requests_total[5m]))
      
      - record: slo:availability:1h
        expr: |
          sum(rate(search_requests_total{result_status="success"}[1h])) 
          / 
          sum(rate(search_requests_total[1h]))
      
      - record: slo:availability:24h
        expr: |
          sum(rate(search_requests_total{result_status="success"}[24h])) 
          / 
          sum(rate(search_requests_total[24h]))
      
      # Record latency percentiles
      - record: slo:latency:p95:5m
        expr: |
          histogram_quantile(0.95, 
            rate(search_latency_seconds_bucket[5m])
          )
      
      - record: slo:latency:p99:5m
        expr: |
          histogram_quantile(0.99, 
            rate(search_latency_seconds_bucket[5m])
          )
      
      # Record cache hit rate
      - record: slo:cache_hit_rate:5m
        expr: |
          sum(rate(cache_hits_total[5m])) 
          / 
          (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
      
      # Record error rate
      - record: slo:error_rate:5m
        expr: |
          sum(rate(search_requests_total{result_status="error"}[5m])) 
          / 
          sum(rate(search_requests_total[5m]))
"""


def get_alerting_rules_yaml() -> str:
    """Get Prometheus alerting rules YAML."""
    return SLO_ALERTING_RULES


def get_recording_rules_yaml() -> str:
    """Get Prometheus recording rules YAML."""
    return SLO_RECORDING_RULES


def get_all_rules_yaml() -> str:
    """Get combined alerting and recording rules."""
    return SLO_ALERTING_RULES + "\n\n" + SLO_RECORDING_RULES
