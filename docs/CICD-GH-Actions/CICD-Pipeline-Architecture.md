# QNT9-SRS CI/CD Pipeline Architecture

## Overview

This document describes the CI/CD pipeline architecture for the QNT9-SRS project. The pipeline implements an infrastructure-on-demand pattern where Azure resources (AKS, ACR) are provisioned via Terraform at the start of each pipeline run and destroyed after non-production runs.

## Architecture

```
Pipeline Stages:
================

1. INFRASTRUCTURE STAGE
   - Detect changes and determine environment
   - Provision AKS/ACR via HCP Terraform Cloud
   - Output resource identifiers for downstream jobs

2. SOURCE STAGE
   - Lint Python code (black, isort, ruff)
   - Security scan (bandit)

3. BUILD STAGE
   - Run unit tests with coverage
   - Build Docker images
   - Push to dynamically provisioned ACR

4. TEST STAGE
   - Run integration tests
   - Uses PostgreSQL and Redis services

5. RELEASE STAGE
   - Deploy to dynamically provisioned AKS
   - Apply Kubernetes manifests

6. CLEANUP STAGE
   - Destroy ephemeral infrastructure (non-prod only)
   - Delete HCP Terraform Cloud workspace
```

## Environment Detection

| Branch Pattern | Environment | Ephemeral | Infrastructure Lifecycle |
|---------------|-------------|-----------|--------------------------|
| main | prd | false | Persistent |
| staging | staging | true | Created/Destroyed |
| development | dev | true | Created/Destroyed |
| feature/** | dev | true | Created/Destroyed |
| Pull Requests | dev | true | Created/Destroyed |

## HCP Terraform Cloud Integration

### Workspace Naming Convention

- **Persistent (Production):** `qnt9-srs-prd`
- **Ephemeral:** `qnt9-srs-{env}-{run_id}`
  - Examples: `qnt9-srs-dev-pr123`, `qnt9-srs-staging-run456789`

### Workflow

1. Check if workspace exists
2. Create workspace if missing (ephemeral runs)
3. Set Azure ARM credentials as workspace variables
4. Upload Terraform configuration
5. Create and apply Terraform run
6. Extract outputs for downstream jobs
7. On cleanup: Destroy resources and delete workspace

## Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `TF_API_TOKEN` | HCP Terraform Cloud API token |
| `TF_CLOUD_ORGANIZATION` | HCP Terraform Cloud organization name |
| `ARM_CLIENT_ID` | Azure Service Principal client ID |
| `ARM_CLIENT_SECRET` | Azure Service Principal client secret |
| `ARM_SUBSCRIPTION_ID` | Azure subscription ID |
| `ARM_TENANT_ID` | Azure AD tenant ID |
| `CODECOV_TOKEN` | Codecov upload token (optional) |

## Terraform Variables for CI/CD

The pipeline generates `cicd.auto.tfvars` with the following variables:

```hcl
environment = "dev|staging|prd"
ephemeral   = true|false
run_id      = "pr123|run456789"
enable_icinga       = false  # Disabled for ephemeral
enable_function_app = false  # Disabled for ephemeral
location = "germanywestcentral"
# ... cost tracking and compliance variables
aks_node_count           = 2|3  # Environment dependent
aks_vm_size              = "Standard_B2s|Standard_D2s_v3"
aks_ephemeral_node_count = 1
aks_ephemeral_vm_size    = "Standard_B2s"
```

## Cost Optimization

### Ephemeral Deployments (Dev/Staging)

- Single AKS node (vs 2-3 for production)
- Smaller VM size (Standard_B2s)
- No Icinga monitoring VM
- No Function App
- Resources destroyed after pipeline completion

### Production

- Full infrastructure with monitoring
- Resources persist across pipeline runs
- Uses existing `qnt9-srs-prd` workspace

## Files Structure

```
.github/workflows/
  cicd-pipeline.yml        # Main CI/CD pipeline

infrastructure/terraform/
  main.tf                  # Dynamic resource naming
  variables.tf             # Ephemeral variables
  outputs.tf               # CI/CD integration outputs
  backend.tf               # HCP Terraform Cloud backend
  environments/
    dev.tfvars
    staging.tfvars
    prd.tfvars
```

## Pipeline Triggers

- **Push:** main, development, staging, feature/**, release/**
- **Pull Request:** main, development, staging
- **Manual:** workflow_dispatch with environment selection

## Manual Workflow Options

When triggering manually via workflow_dispatch:

- `environment`: Select target environment (dev, staging, prd)
- `skip_destroy`: Keep infrastructure after run (useful for debugging)

## Outputs

The pipeline generates a summary with:

- Environment and run configuration
- Build status for each service
- Test results
- Deployment status
- Infrastructure cleanup status

## Troubleshooting

### Infrastructure Provisioning Fails

1. Check HCP Terraform Cloud workspace logs
2. Verify Azure credentials are valid
3. Check quota limits in Azure subscription

### Build Fails

1. Check unit test logs
2. Verify dependencies in requirements.txt
3. Check Docker build context

### Deployment Fails

1. Check AKS cluster status
2. Verify Kubernetes manifests
3. Check service health endpoints

### Cleanup Fails

1. Manual cleanup via HCP Terraform Cloud UI
2. Delete workspace: `terraform workspace delete qnt9-srs-{env}-{run_id}`
3. Check for resource locks in Azure

## Related Documentation

- [Terraform Modules](./terraform/README.md)
- [Kubernetes Manifests](./kubernetes/README.md)
- [Microservice Architecture](./docs/MicroserviceArchitecture.md)
