# Watchlist Service

Kubernetes deployment for the watchlist service.

## Deployment

The watchlist service is deployed as a Deployment with 2 replicas for high availability.

### Configuration

- **Image**: `qnt9acr.azurecr.io/watchlist-service:latest`
- **Port**: 8012
- **Replicas**: 2
- **Service Type**: ClusterIP (internal)

### Environment Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `JWT_SECRET_KEY` | Secret | JWT signing key |
| `DATABASE_URL` | Secret | Supabase PostgreSQL connection |
| `FREE_TIER_WATCHLIST_LIMIT` | ConfigMap | Max stocks for free users (3) |
| `PAID_TIER_WATCHLIST_LIMIT` | ConfigMap | Max stocks for paid users (999) |

### Health Checks

- **Liveness Probe**: `/health` endpoint (30s interval)
- **Readiness Probe**: `/health` endpoint (10s interval)

### Resources

- **Requests**: 128Mi RAM, 100m CPU
- **Limits**: 256Mi RAM, 500m CPU

## Apply Configuration

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

## Verify Deployment

```bash
# Check pods
kubectl get pods -n qnt9-srs -l app=watchlist-service

# Check service
kubectl get svc -n qnt9-srs watchlist-service

# View logs
kubectl logs -n qnt9-srs -l app=watchlist-service --tail=100
```

## Access Service

The service is accessible within the cluster at:
- `http://watchlist-service.qnt9-srs.svc.cluster.local:8012`

Frontend service proxies requests to this internal endpoint.
