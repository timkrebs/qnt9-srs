# QNT9-SRS Kubernetes Infrastructure

This directory contains Kubernetes manifests for deploying QNT9-SRS services to Azure Kubernetes Service (AKS).

## Directory Structure

```
kubernetes/
├── base/                    # Shared resources across all services
│   ├── namespace.yaml       # QNT9 namespace definition
│   ├── secrets.yaml         # Secrets template (use external secrets in prod)
│   ├── ingress.yaml         # NGINX Ingress configuration
│   └── network-policy.yaml  # Network isolation policies
├── auth-service/            # Authentication service manifests
│   ├── deployment.yaml
│   └── service.yaml
├── search-service/          # Search service manifests
│   ├── deployment.yaml
│   └── service.yaml
├── webapp-service/          # Webapp service manifests (Next.js)
│   ├── deployment.yaml
│   └── service.yaml
├── user-service/            # User service manifests
│   ├── deployment.yaml
│   └── service.yaml
└── watchlist-service/       # Watchlist service manifests
    ├── deployment.yaml
    └── service.yaml
```

## Prerequisites

1. **Azure CLI** installed and configured
2. **kubectl** installed and configured
3. **AKS cluster** deployed via Terraform
4. **ACR** with pushed Docker images
5. **envsubst** available (usually pre-installed on Linux/macOS)

## Environment Variables

The manifests use environment variable substitution. Set these before deploying:

```bash
export ENVIRONMENT=dev          # dev, staging, or prd
export IMAGE_TAG=latest         # Docker image tag
export ACR_LOGIN_SERVER=qnt9acr.azurecr.io
export DATABASE_URL="postgresql://user:pass@host:5432/db"
export JWT_SECRET_KEY="your-jwt-secret"
export REDIS_URL="redis://:password@host:6379/0"
export INGRESS_HOST="qnt9.example.com"
```

## Deployment

### Manual Deployment

```bash
# Connect to AKS cluster
az aks get-credentials --resource-group qnt9-rg-dev-gwc --name aks-dev-gwc

# Apply base resources
for manifest in base/*.yaml; do
    envsubst < "$manifest" | kubectl apply -f -
done

# Deploy a specific service
export IMAGE_TAG=v1.0.0
envsubst < auth-service/deployment.yaml | kubectl apply -f -
envsubst < auth-service/service.yaml | kubectl apply -f -
```

### Using the Deploy Script

```bash
# Deploy auth-service to dev environment
./scripts/deploy.sh dev auth-service v1.0.0

# Deploy all services
for service in auth-service search-service webapp-service user-service watchlist-service; do
    ./scripts/deploy.sh dev $service v1.0.0
done
```

## Service Endpoints

| Service           | Port | Internal URL                      |
|-------------------|------|-----------------------------------|
| auth-service      | 8010 | http://auth-service:8010          |
| search-service    | 8000 | http://search-service:8000        |
| webapp-service    | 3000 | http://webapp-service:3000        |
| user-service      | 8020 | http://user-service:8020          |
| watchlist-service | 8012 | http://watchlist-service:8012     |

## Resource Specifications

### CPU and Memory

| Service           | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-------------------|-------------|-----------|----------------|--------------|
| auth-service      | 100m        | 500m      | 256Mi          | 512Mi        |
| search-service    | 200m        | 1000m     | 512Mi          | 1Gi          |
| webapp-service    | 100m        | 500m      | 256Mi          | 512Mi        |
| user-service      | 100m        | 500m      | 256Mi          | 512Mi        |
| watchlist-service | 100m        | 500m      | 256Mi          | 512Mi        |

### Auto-scaling

All services have HPA (Horizontal Pod Autoscaler) configured:

- **Min replicas**: 2
- **Max replicas**: 10-15 (varies by service)
- **Scale up trigger**: CPU > 70% or Memory > 80%
- **Scale down stabilization**: 5 minutes

## Health Checks

Each service exposes health endpoints:

- **Liveness probe**: `/health` - Restarts unhealthy pods
- **Readiness probe**: `/health` - Controls traffic routing

## Security

### Pod Security

- Runs as non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- Drops all capabilities

### Network Policies

- Inter-service communication allowed within namespace
- Ingress from NGINX controller allowed
- External egress restricted to necessary ports (443, 5432, 6379)

## Troubleshooting

### Check pod status

```bash
kubectl get pods -n qnt9
kubectl describe pod <pod-name> -n qnt9
```

### View logs

```bash
kubectl logs -f deployment/auth-service -n qnt9
kubectl logs -f deployment/search-service -n qnt9 --tail=100
```

### Check events

```bash
kubectl get events -n qnt9 --sort-by='.lastTimestamp'
```

### Restart deployment

```bash
kubectl rollout restart deployment/auth-service -n qnt9
```

### Rollback deployment

```bash
kubectl rollout undo deployment/auth-service -n qnt9
kubectl rollout history deployment/auth-service -n qnt9
```

## Cleanup

To remove all QNT9 resources:

```bash
kubectl delete namespace qnt9
```

Warning: This will delete all services, deployments, secrets, and data in the namespace.
