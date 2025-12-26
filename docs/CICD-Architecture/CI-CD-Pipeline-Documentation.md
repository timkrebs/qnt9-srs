# QNT9-SRS CI/CD Pipeline Documentation

## Overview

This document describes the CI/CD pipeline architecture for the QNT9-SRS project. The pipeline implements a four-stage deployment process: Source, Build, Test, and Release.

## Pipeline Architecture

```
+----------------+     +----------------+     +----------------+     +----------------+
|    SOURCE      | --> |     BUILD      | --> |     TEST       | --> |    RELEASE     |
+----------------+     +----------------+     +----------------+     +----------------+
| - Detect       |     | - Unit Tests   |     | - Integration  |     | - Deploy Dev   |
|   Changes      |     | - Coverage     |     |   Tests        |     | - Deploy Stage |
| - Lint/Format  |     | - Docker Build |     | - Security     |     | - Deploy Prod  |
| - Security     |     | - Push to ACR  |     |   Scan         |     | - Verify       |
+----------------+     +----------------+     +----------------+     +----------------+
```

## Environments

| Environment | Branch          | Trigger         | AKS Cluster        |
|-------------|-----------------|-----------------|-------------------|
| dev         | feature/*, dev  | Push, PR        | aks-dev-gwc       |
| staging     | staging         | Push            | aks-staging-gwc   |
| prod        | main            | Push, Manual    | aks-prd-gwc       |

## Workflow Files

### cicd-pipeline.yml

Main CI/CD workflow implementing all stages:

**Triggers:**
- Push to `main`, `development`, `staging`, `feature/**`, `release/**`
- Pull requests to `main`, `development`, `staging`
- Manual workflow dispatch with environment selection

**Jobs:**

1. **detect-changes**: Identifies which services changed using dorny/paths-filter
2. **lint**: Runs Black, isort, Ruff, Bandit security scanning
3. **build-[service]**: Unit tests, coverage, Docker build and push
4. **integration-tests**: Full stack integration testing
5. **security-scan**: Docker Scout CVE scanning
6. **deploy-[environment]**: Kubernetes deployment via AKS

## Service-Specific Build Jobs

Each service has a dedicated build job that:

1. Runs only if the service files changed
2. Executes unit tests with coverage requirements
3. Builds Docker image with multi-stage optimization
4. Pushes to Azure Container Registry

### Coverage Requirements

| Service          | Minimum Coverage |
|------------------|------------------|
| auth-service     | 80%              |
| search-service   | 70%              |
| frontend-service | 70%              |
| user-service     | 70%              |

## Infrastructure Requirements

### Azure Resources

- **Azure Container Registry (ACR)**: Stores Docker images
- **Azure Kubernetes Service (AKS)**: Deployment target
- **Azure Key Vault**: Secrets management (via HCP Vault integration)

### Required GitHub Secrets

| Secret              | Description                           |
|---------------------|---------------------------------------|
| ACR_LOGIN_SERVER    | ACR login server URL                  |
| ACR_USERNAME        | ACR username for authentication       |
| ACR_PASSWORD        | ACR password for authentication       |
| AZURE_CREDENTIALS   | Azure Service Principal credentials   |
| DATABASE_URL        | PostgreSQL connection string          |
| JWT_SECRET_KEY      | JWT signing key                       |
| REDIS_URL           | Redis connection string               |
| CODECOV_TOKEN       | CodeCov upload token                  |

## Kubernetes Deployment

### Directory Structure

```
infrastructure/kubernetes/
├── base/
│   ├── namespace.yaml
│   ├── secrets.yaml
│   ├── ingress.yaml
│   └── network-policy.yaml
├── auth-service/
│   ├── deployment.yaml
│   └── service.yaml
├── search-service/
│   ├── deployment.yaml
│   └── service.yaml
├── frontend-service/
│   ├── deployment.yaml
│   └── service.yaml
└── user-service/
    ├── deployment.yaml
    └── service.yaml
```

### Deployment Process

1. Connect to AKS cluster using Azure credentials
2. Apply base resources (namespace, secrets, configmaps)
3. Substitute environment variables using `envsubst`
4. Apply deployment and service manifests
5. Wait for rollout completion
6. Verify deployment health

### Rollback Strategy

If a deployment fails:

1. Pipeline automatically fails the job
2. Previous deployment remains active (rolling update strategy)
3. Manual rollback available via:
   ```bash
   kubectl rollout undo deployment/<service> -n qnt9
   ```

## Terraform Infrastructure

### Workspace Configuration

| Workspace        | Environment | tfvars file              |
|------------------|-------------|--------------------------|
| qnt9-dev         | dev         | environments/dev.tfvars  |
| qnt9-staging     | staging     | environments/staging.tfvars |
| qnt9-prd         | prd         | environments/prd.tfvars  |

### Resource Scaling

| Environment | AKS Nodes | VM Size        | Replicas |
|-------------|-----------|----------------|----------|
| dev         | 2         | Standard_B2s   | 2        |
| staging     | 3         | Standard_D2s_v3| 2        |
| prod        | 5         | Standard_D4s_v3| 3+       |

## Security

### Pipeline Security

- OIDC authentication with Azure
- Docker Scout CVE scanning
- Bandit Python security scanning
- Secret injection from GitHub Secrets

### Kubernetes Security

- Non-root container execution
- Read-only root filesystem
- Network policies for pod isolation
- Pod security context enforcement

## Monitoring

### Pipeline Metrics

- Build duration tracking
- Test coverage reporting (CodeCov)
- Deployment status tracking

### Application Metrics

- Prometheus scraping enabled
- Health check endpoints
- Resource utilization monitoring

## Troubleshooting

### Common Issues

1. **Build fails on coverage**: Increase test coverage or adjust threshold
2. **Docker push fails**: Check ACR credentials and permissions
3. **Deployment times out**: Check pod logs and resource limits
4. **Integration tests fail**: Verify service connectivity and database state

### Debugging Commands

```bash
# Check deployment status
kubectl get deployments -n qnt9

# View pod logs
kubectl logs -f deployment/<service> -n qnt9

# Describe failing pods
kubectl describe pods -n qnt9 -l app=<service>

# Check events
kubectl get events -n qnt9 --sort-by='.lastTimestamp'
```

## Maintenance

### Updating Kubernetes Version

1. Update `aks_kubernetes_version` in tfvars files
2. Apply Terraform changes to staging first
3. Monitor for issues
4. Apply to production

### Updating Docker Images

1. Bump version in Dockerfile or build args
2. Push changes to trigger pipeline
3. Monitor deployment rollout

### Secret Rotation

1. Update secrets in GitHub repository settings
2. Re-run pipeline or manually update Kubernetes secrets
3. Restart affected deployments
