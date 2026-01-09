# finio Monitoring Stack - Dokploy Setup Guide

This guide explains how to set up the Grafana monitoring stack for finio in your Dokploy production environment.

## Overview

The monitoring stack includes:
- **Grafana** - Visualization and dashboards (v10.2.3)
- **Prometheus** - Metrics collection and storage (v2.48.1)
- **Loki** - Log aggregation (v2.9.3)
- **Promtail** - Log collection agent (v2.9.3)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Dokploy Network                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Auth Service │    │ User Service │    │Search Service│          │
│  │   :8010      │    │    :8011     │    │    :8000     │          │
│  │  /metrics    │    │   /metrics   │    │   /metrics   │          │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             │                                       │
│                             ▼                                       │
│                    ┌────────────────┐                               │
│                    │   Prometheus   │◄─── Scrapes metrics           │
│                    │     :9090      │                               │
│                    └────────┬───────┘                               │
│                             │                                       │
│                             ▼                                       │
│                    ┌────────────────┐                               │
│                    │    Grafana     │◄─── Visualizes data           │
│                    │     :3000      │                               │
│                    └────────────────┘                               │
│                             ▲                                       │
│                             │                                       │
│                    ┌────────┴───────┐                               │
│                    │      Loki      │◄─── Stores logs               │
│                    │     :3100      │                               │
│                    └────────────────┘                               │
│                             ▲                                       │
│                             │                                       │
│                    ┌────────┴───────┐                               │
│                    │    Promtail    │◄─── Collects logs             │
│                    │    (agent)     │                               │
│                    └────────────────┘                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. Dokploy installed and running
2. finio services deployed (auth-service, user-service, watchlist-service, search-service)
3. Domain configured for Grafana (e.g., `grafana.finio.cloud`)
4. Domain configured for Prometheus (e.g., `prometheus.finio.cloud`)

## Step-by-Step Dokploy Setup

### Step 1: Create DNS Records

Add the following DNS A records pointing to your Dokploy server:
- `grafana.finio.cloud` → Your Server IP
- `prometheus.finio.cloud` → Your Server IP

### Step 2: Create Monitoring Application in Dokploy

1. Log into Dokploy admin panel (e.g., `admin.finio.cloud`)
2. Click **"Create Application"** or **"+"** button
3. Select **"Compose"** as the application type
4. Name it: `finio-monitoring`

### Step 3: Upload Configuration Files

You need to upload the configuration files to your server. You can do this via:

**Option A: Using Dokploy's file manager** (if available)

**Option B: SSH into your server:**

```bash
# SSH into your server
ssh your-user@your-server

# Create the monitoring directory
mkdir -p /opt/dokploy/monitoring/{prometheus/alerts,loki,promtail,grafana/provisioning/{datasources,dashboards},grafana/dashboards}

# Copy all config files (you can also use scp/rsync from your local machine)
```

### Step 4: Copy Configuration Files to Server

From your local machine, copy the monitoring configs:

```bash
# From the project root directory
scp -r infrastructure/monitoring/* your-user@your-server:/opt/dokploy/monitoring/
```

### Step 5: Configure the Compose File in Dokploy

1. In your `finio-monitoring` application in Dokploy
2. Go to the **Compose** tab
3. Paste the content from `docker-compose.monitoring.yml`
4. Update the volume paths to point to `/opt/dokploy/monitoring/`:

```yaml
volumes:
  - /opt/dokploy/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
  - /opt/dokploy/monitoring/prometheus/alerts:/etc/prometheus/alerts:ro
  - /opt/dokploy/monitoring/loki/loki-config.yml:/etc/loki/loki-config.yml:ro
  - /opt/dokploy/monitoring/promtail/promtail-config.yml:/etc/promtail/promtail-config.yml:ro
  - /opt/dokploy/monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
  - /opt/dokploy/monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
```

### Step 6: Set Environment Variables

In Dokploy, go to **Environment** tab and add:

```env
# Grafana Admin Credentials (CHANGE THESE!)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-secure-password-here

# Prometheus Basic Auth (generate with: htpasswd -nb admin password | sed 's/\$/\$\$/g')
PROMETHEUS_BASIC_AUTH=admin:$$apr1$$your-hash-here
```

**To generate Prometheus Basic Auth:**
```bash
# On your local machine or server
htpasswd -nb admin your-secure-password

# Copy the output and replace $ with $$ for docker-compose
# Example: admin:$apr1$H6uskkkW$IgXLP6ewTrSuBkTrqE8wj/
# Becomes: admin:$$apr1$$H6uskkkW$$IgXLP6ewTrSuBkTrqE8wj/
```

### Step 7: Deploy the Stack

1. Click **"Deploy"** in Dokploy
2. Wait for all containers to start
3. Check the logs for any errors

### Step 8: Verify Deployment

1. **Grafana:** Visit `https://grafana.finio.cloud`
   - Login with your admin credentials
   - Check that Prometheus and Loki datasources are connected (green)
   - Navigate to Dashboards → finio → "finio - Service Overview"

2. **Prometheus:** Visit `https://prometheus.finio.cloud`
   - Login with basic auth credentials
   - Go to Status → Targets
   - All services should show as "UP"

## Configuration Files Reference

### File Structure

```
infrastructure/monitoring/
├── docker-compose.monitoring.yml  # Main compose file
├── prometheus/
│   ├── prometheus.yml             # Prometheus configuration
│   └── alerts/
│       └── finio-alerts.yml       # Alert rules
├── loki/
│   └── loki-config.yml            # Loki configuration
├── promtail/
│   └── promtail-config.yml        # Promtail configuration
└── grafana/
    ├── provisioning/
    │   ├── datasources/
    │   │   └── datasources.yml    # Auto-configure datasources
    │   └── dashboards/
    │       └── dashboards.yml     # Dashboard provisioning config
    └── dashboards/
        └── finio-overview.json    # Pre-built dashboard
```

## Available Metrics

### Auth Service (`/metrics` on port 8010)
- `auth_http_requests_total` - Total HTTP requests
- `auth_http_request_duration_seconds` - Request duration histogram
- `auth_login_total` - Login attempts (success/failure)
- `auth_token_refresh_total` - Token refresh operations
- `auth_rate_limit_hits_total` - Rate limit violations

### User Service (`/metrics` on port 8011)
- `user_http_requests_total` - Total HTTP requests
- `user_http_request_duration_seconds` - Request duration histogram
- `user_profile_operations_total` - Profile operations
- `user_db_operations_total` - Database operations

### Watchlist Service (`/metrics` on port 8012)
- `watchlist_http_requests_total` - Total HTTP requests
- `watchlist_http_request_duration_seconds` - Request duration histogram
- `watchlist_add_total` - Watchlist add operations by tier
- `watchlist_remove_total` - Watchlist remove operations
- `watchlist_tier_limit_exceeded_total` - Tier limit violations

### Search Service (`/metrics` on port 8000)
- `search_http_requests_total` - Total HTTP requests
- `search_http_request_duration_seconds` - Request duration histogram
- `search_cache_hits_total` - Cache hit count
- `search_cache_misses_total` - Cache miss count
- `search_external_api_requests_total` - External API calls

## Accessing Logs

### In Grafana (Loki)

1. Go to Explore
2. Select "Loki" as datasource
3. Use LogQL queries:

```logql
# All logs from auth-service
{service="auth-service"}

# Error logs only
{service=~".+"} |= "error"

# Logs from specific container
{container="finio-search-service"}

# Filter by log level
{service="auth-service"} | json | level="error"

# Search for specific request ID
{service=~".+"} |= "request_id=abc123"
```

## Alert Rules

The following alerts are pre-configured:

| Alert | Severity | Description |
|-------|----------|-------------|
| ServiceDown | Critical | Service is down for >1 minute |
| HighErrorRate | Warning | >5% error rate for 5 minutes |
| SlowResponseTime | Warning | p95 response time >2 seconds |
| HighAuthFailureRate | Warning | >30% auth failure rate |
| HighRateLimitHits | Warning | Frequent rate limiting |
| WatchlistDBFailures | Warning | Database operation failures |
| HighCacheMissRate | Warning | >80% cache miss rate |

## Troubleshooting

### Services not appearing in Prometheus

1. Check that services are on the same Docker network (`dokploy-network`)
2. Verify container names match those in `prometheus.yml`
3. Test metrics endpoint manually:
   ```bash
   docker exec -it finio-prometheus wget -qO- http://finio-auth-service:8010/metrics
   ```

### Logs not appearing in Loki

1. Check Promtail logs:
   ```bash
   docker logs finio-promtail
   ```
2. Verify Docker socket is mounted:
   ```bash
   docker exec -it finio-promtail ls -la /var/run/docker.sock
   ```

### Grafana datasource connection failed

1. Verify Prometheus/Loki containers are running
2. Check network connectivity:
   ```bash
   docker exec -it finio-grafana wget -qO- http://finio-prometheus:9090/-/healthy
   docker exec -it finio-grafana wget -qO- http://finio-loki:3100/ready
   ```

### Container names not resolving

Ensure all containers use the same network. In Dokploy, both the main application and monitoring stack should use `dokploy-network`.

## Security Recommendations

1. **Change default passwords** - Update `GRAFANA_ADMIN_PASSWORD` and `PROMETHEUS_BASIC_AUTH`
2. **Use strong passwords** - Minimum 16 characters with mixed case, numbers, and symbols
3. **Restrict Prometheus access** - Only expose via Traefik with basic auth
4. **Enable Grafana authentication** - Consider OAuth/LDAP for production
5. **Regular updates** - Keep Grafana/Prometheus/Loki images updated

## Optional: Adding Node Exporter

To monitor server-level metrics (CPU, memory, disk), add node_exporter:

```yaml
# Add to docker-compose.monitoring.yml
node-exporter:
  image: prom/node-exporter:v1.7.0
  container_name: finio-node-exporter
  command:
    - '--path.rootfs=/host'
  volumes:
    - '/:/host:ro,rslave'
  network_mode: host
  pid: host
  restart: unless-stopped
```

Then uncomment the node-exporter job in `prometheus.yml`.

## Optional: Adding cAdvisor

To monitor container metrics (CPU, memory per container), add cAdvisor:

```yaml
# Add to docker-compose.monitoring.yml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:v0.47.2
  container_name: finio-cadvisor
  privileged: true
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
    - /dev/disk/:/dev/disk:ro
  networks:
    - dokploy-network
  restart: unless-stopped
```

Then uncomment the cadvisor job in `prometheus.yml`.

## Support

For issues specific to the monitoring stack, check:
1. Container logs in Dokploy
2. Grafana explore for log analysis
3. Prometheus targets page for scrape failures
