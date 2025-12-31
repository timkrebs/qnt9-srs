# Grafana Cloud Monitoring Stack

This directory contains Kubernetes manifests for deploying Grafana Cloud observability components to the QNT9 cluster.

## Components

### Grafana Agent
- **DaemonSet**: Runs on every node to collect logs and metrics
- **Metrics Collection**: Scrapes Prometheus metrics from all pods with appropriate annotations
- **Log Collection**: Forwards container logs to Grafana Cloud Loki
- **Trace Collection**: Forwards OpenTelemetry traces to Grafana Cloud Tempo

### Kube-State-Metrics
- **Deployment**: Exports Kubernetes object metrics (deployments, pods, nodes)
- **Used by**: Grafana Agent for cluster-level monitoring

### Secrets
- **grafana-cloud-secrets**: Contains authentication tokens and endpoints for Grafana Cloud

## Prerequisites

### Grafana Cloud Setup

1. Sign up for Grafana Cloud at https://grafana.com/products/cloud/
2. Create a new stack or use existing one
3. Get the following credentials:

#### Prometheus/Mimir
- Remote Write Endpoint: `https://prometheus-prod-XX-prod-XX-region.grafana.net/api/prom/push`
- Username: Usually your instance ID (e.g., `123456`)
- Password: Access token from Grafana Cloud

#### Loki
- Endpoint: `https://logs-prod-XX-region.grafana.net/loki/api/v1/push`
- Username: Usually your instance ID
- Password: Access token from Grafana Cloud

#### Tempo
- Endpoint: `https://tempo-prod-XX-region.grafana.net/tempo`
- Username: Usually your instance ID
- Password: Access token from Grafana Cloud

## Installation

### 1. Create Namespace
```bash
kubectl apply -f namespace.yaml
```

### 2. Configure Secrets

Edit `grafana-cloud-secrets.yaml` and replace placeholders:
- `<PROMETHEUS_REMOTE_WRITE_ENDPOINT>`: Your Prometheus remote write URL
- `<PROMETHEUS_USERNAME>`: Your Prometheus username (instance ID)
- `<PROMETHEUS_PASSWORD>`: Your Prometheus API key
- `<LOKI_ENDPOINT>`: Your Loki endpoint URL
- `<LOKI_USERNAME>`: Your Loki username (instance ID)
- `<LOKI_PASSWORD>`: Your Loki API key
- `<TEMPO_ENDPOINT>`: Your Tempo endpoint URL
- `<TEMPO_USERNAME>`: Your Tempo username (instance ID)
- `<TEMPO_PASSWORD>`: Your Tempo API key

Then apply:
```bash
kubectl apply -f grafana-cloud-secrets.yaml
```

### 3. Deploy Kube-State-Metrics
```bash
kubectl apply -f kube-state-metrics.yaml
```

### 4. Deploy Grafana Agent
```bash
kubectl apply -f grafana-agent.yaml
```

### 5. Verify Deployment
```bash
# Check Grafana Agent pods
kubectl get pods -n qnt9-monitoring -l app=grafana-agent

# Check logs
kubectl logs -n qnt9-monitoring -l app=grafana-agent --tail=50

# Check kube-state-metrics
kubectl get pods -n qnt9-monitoring -l app=kube-state-metrics
```

## Configuration

### Metrics Scraping

The Grafana Agent is configured to scrape metrics from pods with the following annotations:
```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

All QNT9 services have these annotations configured in their deployment manifests.

### Log Collection

The Grafana Agent automatically collects logs from all pods in the `qnt9` namespace using Kubernetes pod logs.

### Trace Collection

Services instrumented with OpenTelemetry should send traces to the Grafana Agent at:
- Endpoint: `grafana-agent.qnt9-monitoring.svc.cluster.local:4317` (gRPC)
- Endpoint: `grafana-agent.qnt9-monitoring.svc.cluster.local:4318` (HTTP)

## Dashboards

### Pre-built Dashboards

Import these dashboards from Grafana Cloud:

1. **Kubernetes Cluster Monitoring**
   - Dashboard ID: 7249
   - Shows: Node CPU/Memory, Pod status, Network I/O

2. **Kubernetes Pods**
   - Dashboard ID: 6417
   - Shows: Individual pod metrics, resource usage

3. **FastAPI Application**
   - Custom dashboard for QNT9 services
   - Shows: Request rate, error rate, latency (RED metrics)

### Custom Service Dashboards

Create dashboards for each service tracking:
- HTTP request rate by endpoint
- HTTP error rate by status code
- Request duration percentiles (p50, p95, p99)
- Service-specific metrics (cache hits, DB queries, etc.)

## Alerting

### Recommended Alerts

1. **High Error Rate**
   ```
   rate(http_requests_total{status=~"5.."}[5m]) > 0.05
   ```

2. **High Response Time**
   ```
   histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2.0
   ```

3. **Pod Restarts**
   ```
   rate(kube_pod_container_status_restarts_total[15m]) > 0
   ```

4. **High Memory Usage**
   ```
   container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
   ```

## Troubleshooting

### Agent Not Scraping Metrics

1. Check agent logs:
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent
   ```

2. Verify service annotations:
   ```bash
   kubectl get deployment -n qnt9 <service-name> -o yaml | grep -A 3 annotations
   ```

3. Test metrics endpoint:
   ```bash
   kubectl port-forward -n qnt9 <pod-name> 8080:8080
   curl localhost:8080/metrics
   ```

### Logs Not Appearing in Loki

1. Check agent log collection:
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent | grep loki
   ```

2. Verify Loki credentials:
   ```bash
   kubectl get secret -n qnt9-monitoring grafana-cloud-secrets -o yaml
   ```

### Traces Not Appearing in Tempo

1. Check OpenTelemetry instrumentation in application code
2. Verify Tempo endpoint configuration
3. Check agent trace receiver:
   ```bash
   kubectl logs -n qnt9-monitoring -l app=grafana-agent | grep tempo
   ```

## Cost Optimization

Grafana Cloud has usage-based pricing. To optimize costs:

1. **Reduce Metric Cardinality**
   - Limit labels on metrics
   - Use histograms instead of individual timeseries
   - Drop unnecessary metrics

2. **Adjust Scrape Intervals**
   - Increase scrape interval for less critical metrics
   - Default: 15s, consider: 30s or 60s

3. **Log Filtering**
   - Filter out debug logs in production
   - Drop high-volume low-value logs
   - Use structured logging for easier filtering

4. **Trace Sampling**
   - Use head-based sampling (sample 10% of requests)
   - Use tail-based sampling (sample all errors)
   - Configure in OpenTelemetry SDK

## References

- [Grafana Agent Documentation](https://grafana.com/docs/agent/latest/)
- [Grafana Cloud Prometheus](https://grafana.com/docs/grafana-cloud/metrics-prometheus/)
- [Grafana Cloud Loki](https://grafana.com/docs/grafana-cloud/logs/)
- [Grafana Cloud Tempo](https://grafana.com/docs/grafana-cloud/traces/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
