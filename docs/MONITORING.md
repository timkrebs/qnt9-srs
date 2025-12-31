# Grafana Cloud Monitoring Integration

Comprehensive monitoring solution for QNT9 Stock Recommendation System using Grafana Cloud for metrics, logs, and traces.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Grafana Cloud                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Prometheus │  │    Loki     │  │   Tempo     │         │
│  │   (Mimir)   │  │   (Logs)    │  │  (Traces)   │         │
│  └──────▲──────┘  └──────▲──────┘  └──────▲──────┘         │
└─────────│────────────────│────────────────│─────────────────┘
          │                │                │
          │ Metrics        │ Logs           │ Traces
          │                │                │
┌─────────┴────────────────┴────────────────┴─────────────────┐
│              Kubernetes Cluster (AKS)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Grafana Agent (DaemonSet)                   │   │
│  │  - Scrapes /metrics endpoints                         │   │
│  │  - Collects pod logs                                   │   │
│  │  - Receives OTLP traces                                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │        kube-state-metrics (Deployment)                │   │
│  │  - Exports Kubernetes object metrics                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │  auth-     │ │   user-    │ │ watchlist- │ ...          │
│  │  service   │ │  service   │ │  service   │              │
│  │            │ │            │ │            │              │
│  │ /metrics   │ │ /metrics   │ │ /metrics   │              │
│  │ OTLP trace │ │ OTLP trace │ │ OTLP trace │              │
│  └────────────┘ └────────────┘ └────────────┘              │
└───────────────────────────────────────────────────────────────┘
```

## Features Implemented

### Application Metrics (Prometheus)

Each service exposes a `/metrics` endpoint with the following metrics:

**HTTP Metrics** (all services)
- `{service}_http_requests_total` - Total request count by method, endpoint, status
- `{service}_http_request_duration_seconds` - Request duration histogram by method, endpoint

**Auth Service Specific**
- `auth_signup_total` - User signup count (success/failure)
- `auth_signin_total` - User sign-in count (success/failure)
- `auth_token_refresh_total` - Token refresh count
- `auth_password_reset_total` - Password reset count
- `auth_rate_limit_hits_total` - Rate limit violations by endpoint
- `auth_active_sessions` - Number of active user sessions
- `auth_db_operations_total` - Database operation count
- `auth_db_operation_duration_seconds` - Database operation duration

**User Service Specific**
- `user_profile_operations_total` - Profile operation count
- `user_cache_hits_total` / `user_cache_misses_total` - Cache performance
- `user_cache_size` - Current cache size
- `user_subscription_updates_total` - Subscription update count by tier
- `user_active_subscriptions` - Active subscriptions by tier
- `user_db_operations_total` - Database operation metrics

**Watchlist Service Specific**
- `watchlist_add_total` - Watchlist add operations by tier
- `watchlist_remove_total` - Watchlist remove operations
- `watchlist_items_per_user` - Distribution of watchlist size
- `watchlist_tier_limit_exceeded_total` - Tier limit violations
- `watchlist_active_users` - Active users with watchlists by tier
- `watchlist_db_operations_total` - Database operation metrics

**Search Service Specific**
- `search_queries_total` - Search query count by type (ISIN, WKN, symbol)
- `search_query_duration_seconds` - Search query duration
- `search_results_per_query` - Result count distribution
- `search_cache_hits_total` / `search_cache_misses_total` - Cache performance
- `search_api_calls_total` - External API call count by provider
- `search_api_fallback_total` - API fallback count
- `search_db_operations_total` - Database operation metrics

**Frontend Service Specific**
- `frontend_page_views_total` - Page view count
- `frontend_page_load_duration_seconds` - Page load duration
- `frontend_proxy_requests_total` - Backend proxy request count
- `frontend_proxy_errors_total` - Proxy error count
- `frontend_search_queries_total` - Search query count (authenticated/anonymous)
- `frontend_watchlist_operations_total` - Watchlist operation count
- `frontend_static_file_requests_total` - Static file request count

### Structured Logging (Loki)

All services use structured JSON logging with the following fields:
- `timestamp` - ISO 8601 timestamp
- `level` - Log level (DEBUG, INFO, WARNING, ERROR)
- `logger` - Logger name (module path)
- `message` - Log message
- `service` - Service name
- `request_id` - Request correlation ID (frontend-service)
- Additional context fields per service

Logs are automatically collected from all pods in the `qnt9` namespace and forwarded to Grafana Cloud Loki.

### Distributed Tracing (Tempo)

OpenTelemetry instrumentation provides automatic tracing for:
- HTTP requests (FastAPI)
- Database queries (asyncpg)
- External API calls (httpx)

Traces include:
- Request ID propagation across services
- Span timing and relationships
- Error tracking and exceptions
- Service metadata (name, version, environment)

Trace data is sent via OTLP to Grafana Agent, which forwards to Grafana Cloud Tempo.

### Kubernetes Cluster Monitoring

kube-state-metrics provides cluster-level metrics:
- Node resource utilization (CPU, memory, disk)
- Pod status and restarts
- Deployment replica counts
- HPA scaling events
- Resource quotas and limits
- PVC usage
- Network I/O

## Installation

### Prerequisites

1. **Grafana Cloud Account**
   - Sign up at https://grafana.com/products/cloud/
   - Create a stack or use existing
   - Note your org name and stack name

2. **Get API Credentials**

   **Prometheus (Mimir)**
   - Navigate to: Grafana Cloud > Connections > Add new connection > Hosted Prometheus metrics
   - Copy: Remote Write Endpoint, Username (Instance ID), Password (API Key)

   **Loki**
   - Navigate to: Grafana Cloud > Connections > Add new connection > Hosted logs
   - Copy: Endpoint URL, Username (Instance ID), Password (API Key)

   **Tempo**
   - Navigate to: Grafana Cloud > Connections > Add new connection > Hosted traces
   - Copy: Endpoint (host:port), Username (Instance ID), Password (API Key)

3. **AKS Cluster Access**
   ```bash
   az aks get-credentials --resource-group qnt9-rg --name qnt9-aks
   kubectl config current-context
   ```

### Automated Deployment

Use the deployment script for automated setup:

```bash
cd infrastructure/scripts
./deploy-monitoring.sh
```

The script will:
1. Create `qnt9-monitoring` namespace
2. Prompt for Grafana Cloud credentials (or use existing secrets)
3. Deploy kube-state-metrics
4. Deploy Grafana Agent DaemonSet
5. Verify deployment status

### Manual Deployment

If you prefer manual steps:

1. **Create Namespace**
   ```bash
   kubectl apply -f infrastructure/kubernetes/monitoring/namespace.yaml
   ```

2. **Configure Secrets**
   
   Edit `infrastructure/kubernetes/monitoring/grafana-cloud-secrets.yaml` and replace placeholders:
   ```yaml
   stringData:
     prometheus-remote-write-endpoint: "https://prometheus-prod-XX.grafana.net/api/prom/push"
     prometheus-username: "123456"
     prometheus-password: "glc_eyJhbGc..."
     loki-endpoint: "https://logs-prod-XX.grafana.net/loki/api/v1/push"
     loki-username: "123456"
     loki-password: "glc_eyJhbGc..."
     tempo-endpoint: "tempo-prod-XX.grafana.net:443"
     tempo-username: "123456"
     tempo-password: "glc_eyJhbGc..."
   ```
   
   Apply secrets:
   ```bash
   kubectl apply -f infrastructure/kubernetes/monitoring/grafana-cloud-secrets.yaml
   ```

3. **Deploy kube-state-metrics**
   ```bash
   kubectl apply -f infrastructure/kubernetes/monitoring/kube-state-metrics.yaml
   kubectl wait --for=condition=available deployment/kube-state-metrics -n qnt9-monitoring --timeout=120s
   ```

4. **Deploy Grafana Agent**
   ```bash
   kubectl apply -f infrastructure/kubernetes/monitoring/grafana-agent.yaml
   kubectl wait --for=condition=ready pod -l app=grafana-agent -n qnt9-monitoring --timeout=120s
   ```

## Verification

### Check Deployment Status

```bash
# All monitoring pods
kubectl get pods -n qnt9-monitoring

# Grafana Agent logs
kubectl logs -n qnt9-monitoring -l app=grafana-agent --tail=50

# kube-state-metrics logs
kubectl logs -n qnt9-monitoring -l app=kube-state-metrics --tail=50
```

### Test Metrics Endpoint

```bash
# Port forward to Grafana Agent
kubectl port-forward -n qnt9-monitoring svc/grafana-agent 8080:80

# Check agent metrics
curl localhost:8080/metrics

# Check service metrics
kubectl port-forward -n qnt9 svc/auth-service 8010:8010
curl localhost:8010/metrics
```

### Verify Data in Grafana Cloud

1. **Metrics**
   - Go to Grafana Cloud > Explore
   - Select Prometheus/Mimir data source
   - Query: `{__name__=~".*_http_requests_total"}`
   - Should see metrics from all services

2. **Logs**
   - Go to Grafana Cloud > Explore
   - Select Loki data source
   - Query: `{namespace="qnt9"}`
   - Should see structured JSON logs

3. **Traces**
   - Go to Grafana Cloud > Explore
   - Select Tempo data source
   - Search for recent traces
   - Should see traces from services with OpenTelemetry

## Dashboards

### Import Pre-built Dashboards

1. **Kubernetes Cluster Monitoring**
   - Dashboard ID: 7249
   - Import: Grafana > Dashboards > Import > 7249
   - Shows: Node metrics, pod status, resource usage

2. **Kubernetes Pods**
   - Dashboard ID: 6417
   - Import: Grafana > Dashboards > Import > 6417
   - Shows: Per-pod metrics, containers, restarts

### Create Custom Service Dashboards

For each service (auth, user, watchlist, search, frontend):

**RED Metrics Panel**
```promql
# Request Rate
sum(rate({service}_http_requests_total[5m])) by (app, endpoint)

# Error Rate
sum(rate({service}_http_requests_total{status=~"5.."}[5m])) by (app) 
/ sum(rate({service}_http_requests_total[5m])) by (app)

# Duration (p95, p99)
histogram_quantile(0.95, 
  rate({service}_http_request_duration_seconds_bucket[5m])
)
```

**Cache Performance Panel**
```promql
# Cache Hit Rate
sum(rate({service}_cache_hits_total[5m])) 
/ (sum(rate({service}_cache_hits_total[5m])) + sum(rate({service}_cache_misses_total[5m])))
```

**Database Performance Panel**
```promql
# DB Operation Duration (p95)
histogram_quantile(0.95, 
  rate({service}_db_operation_duration_seconds_bucket[5m])
)

# DB Operation Rate
rate({service}_db_operations_total[5m])
```

## Alerting

### Recommended Alert Rules

Create alerts in Grafana Cloud Alerting:

1. **High Error Rate**
   ```promql
   sum(rate(http_requests_total{status=~"5.."}[5m])) by (app) > 0.05
   ```
   - Threshold: > 5% error rate
   - Duration: 5 minutes
   - Severity: Critical

2. **High Latency**
   ```promql
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2.0
   ```
   - Threshold: > 2 seconds (p95)
   - Duration: 10 minutes
   - Severity: Warning

3. **Pod Restart Loop**
   ```promql
   rate(kube_pod_container_status_restarts_total[15m]) > 0
   ```
   - Threshold: > 0 restarts in 15min
   - Severity: Warning

4. **High Memory Usage**
   ```promql
   (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
   ```
   - Threshold: > 90% memory
   - Duration: 5 minutes
   - Severity: Warning

5. **Watchlist Tier Limit Exceeded**
   ```promql
   rate(watchlist_tier_limit_exceeded_total[5m]) > 0.1
   ```
   - Threshold: > 0.1 per second
   - Severity: Info

6. **Cache Performance Degradation**
   ```promql
   (sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))) < 0.7
   ```
   - Threshold: < 70% hit rate
   - Duration: 15 minutes
   - Severity: Warning

## Troubleshooting

### Metrics Not Appearing

1. **Check service metrics endpoint**
   ```bash
   kubectl port-forward -n qnt9 <pod-name> 8080:8080
   curl localhost:8080/metrics
   ```
   - Should return Prometheus text format
   - Check for Python errors in logs

2. **Verify Prometheus annotations**
   ```bash
   kubectl get deployment -n qnt9 <service> -o yaml | grep -A 3 "prometheus.io"
   ```
   - Should show: `prometheus.io/scrape: "true"`

3. **Check Grafana Agent scraping**
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent | grep -i error
   ```
   - Look for scrape errors or connection issues

4. **Verify remote write**
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent | grep "remote_write"
   ```
   - Should show successful writes

### Logs Not Appearing

1. **Check log format**
   - Logs should be valid JSON
   - Check service logs: `kubectl logs -n qnt9 <pod-name>`

2. **Verify Grafana Agent log collection**
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent | grep loki
   ```

3. **Check Loki credentials**
   ```bash
   kubectl get secret grafana-cloud-secrets -n qnt9-monitoring -o yaml
   ```

4. **Test Loki query**
   - Grafana > Explore > Loki
   - Query: `{namespace="qnt9"} | json`

### Traces Not Appearing

1. **Verify OpenTelemetry instrumentation**
   - Check service startup logs for "OpenTelemetry configured"
   - Verify `enable_tracing=True` in code

2. **Check OTLP endpoint**
   - Services should send to: `grafana-agent.qnt9-monitoring.svc.cluster.local:4317`
   - Check connectivity: `kubectl exec -n qnt9 <pod> -- nc -zv grafana-agent.qnt9-monitoring.svc.cluster.local 4317`

3. **Verify Tempo configuration**
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent | grep tempo
   ```

4. **Test trace query**
   - Grafana > Explore > Tempo
   - Search for recent traces

### Agent Pods CrashLooping

1. **Check pod events**
   ```bash
   kubectl describe pod -n qnt9-monitoring -l app=grafana-agent
   ```

2. **Check logs**
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent --previous
   ```

3. **Common issues**
   - Invalid Grafana Cloud credentials
   - Network connectivity to Grafana Cloud
   - Invalid configuration YAML

## Cost Optimization

Grafana Cloud has usage-based pricing. To minimize costs:

### 1. Reduce Metric Cardinality

**Limit labels on custom metrics:**
```python
# Avoid: Too many unique label combinations
metric.labels(user_id=user_id, request_id=req_id).inc()

# Recommended: Use aggregatable labels
metric.labels(tier=user_tier, status=status).inc()
```

**Drop high-cardinality metrics:**
```yaml
# In grafana-agent.yaml
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'high_cardinality_metric_.*'
  action: drop
```

### 2. Adjust Scrape Intervals

```yaml
# In grafana-agent.yaml metrics config
scrape_interval: 30s  # Default: 15s
```

Trade-off: Lower resolution but reduced costs

### 3. Filter Logs

**Application level (recommended):**
```python
# Only log WARNING and above in production
if settings.ENVIRONMENT == "production":
    logging.basicConfig(level=logging.WARNING)
```

**Agent level:**
```yaml
# In grafana-agent.yaml logs config
pipeline_stages:
- match:
    selector: '{level="DEBUG"}'
    action: drop
```

### 4. Trace Sampling

**Head-based sampling (sample 10%):**
```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

configure_opentelemetry(
    service_name="auth-service",
    sampler=TraceIdRatioBased(0.1),  # Sample 10%
)
```

**Tail-based sampling (sample all errors):**
```python
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

# Sample 100% of errors, 10% of success
```

### 5. Monitor Your Usage

- Grafana Cloud > Usage & Billing
- Set up usage alerts
- Review monthly reports

**Typical costs for QNT9:**
- Metrics: ~$10-30/month (5 services, 15s scrape)
- Logs: ~$5-20/month (structured logging, WARNING+)
- Traces: ~$5-15/month (10% sampling)
- **Total: ~$20-65/month**

## Performance Impact

### Application Overhead

- **Metrics collection**: ~1-2ms per request
- **Structured logging**: ~0.5-1ms per log entry
- **OpenTelemetry tracing**: ~2-5ms per trace
- **Total overhead**: ~3-8ms per request (~0.3-0.8%)

### Resource Usage

**Per Service:**
- CPU: +5-10m (0.5-1%)
- Memory: +10-20Mi (2-4%)

**Grafana Agent (per node):**
- CPU: 100-500m
- Memory: 128-512Mi

**kube-state-metrics:**
- CPU: 100-200m
- Memory: 128-256Mi

## Best Practices

### Metrics

1. Use histograms for duration/size metrics
2. Use counters for event counts
3. Use gauges for current state
4. Keep label cardinality low (<100 unique values)
5. Use consistent naming: `{service}_{metric}_{unit}`

### Logging

1. Use structured logging (JSON)
2. Include request IDs for tracing
3. Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
4. Don't log sensitive data (passwords, tokens)
5. Use consistent field names across services

### Tracing

1. Exclude health/metrics endpoints
2. Add custom spans for business logic
3. Include error details in span attributes
4. Use sampling in high-traffic environments
5. Propagate trace context across services

## References

- [Grafana Cloud Documentation](https://grafana.com/docs/grafana-cloud/)
- [Grafana Agent Documentation](https://grafana.com/docs/agent/latest/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Kubernetes Monitoring Guide](https://grafana.com/docs/grafana-cloud/kubernetes-monitoring/)
