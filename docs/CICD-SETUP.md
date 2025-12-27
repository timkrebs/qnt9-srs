# CI/CD Pipeline Setup Guide

This guide explains how to set up and configure the QNT9-SRS CI/CD pipeline with HCP Terraform Cloud and Azure (AKS & ACR).

## Workspaces

The pipeline uses **three fixed workspaces** in HCP Terraform Cloud:

| Workspace | Branch | Description |
|-----------|--------|-------------|
| `qnt9-srs-dev` | development | Development environment |
| `qnt9-srs-staging` | staging | Staging environment |
| `qnt9-srs-prd` | main | Production environment |

**Important:** These workspaces must be created manually in HCP Terraform Cloud before running the pipeline.

## Prerequisites

### 1. Azure Setup

1. **Azure Subscription**: An active Azure subscription
2. **Service Principal**: Create a service principal with contributor access:

```bash
# Create Service Principal
az ad sp create-for-rbac \
  --name "qnt9-srs-cicd" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID> \
  --sdk-auth

# Save the output - you'll need these values:
# - clientId (ARM_CLIENT_ID)
# - clientSecret (ARM_CLIENT_SECRET)
# - subscriptionId (ARM_SUBSCRIPTION_ID)
# - tenantId (ARM_TENANT_ID)
```

3. **Additional Permissions** (for ACR role assignment):
```bash
# Grant User Access Administrator role for AKS-ACR integration
az role assignment create \
  --assignee <CLIENT_ID> \
  --role "User Access Administrator" \
  --scope /subscriptions/<SUBSCRIPTION_ID>
```

### 2. HCP Terraform Cloud Setup

1. **Create Organization**: Go to [app.terraform.io](https://app.terraform.io) and create an organization (e.g., `tim-krebs-org`)

2. **Create Workspaces**: Create the three required workspaces manually:

   ```
   qnt9-srs-dev
   qnt9-srs-staging
   qnt9-srs-prd
   ```

   For each workspace:
   - Set Execution Mode to "Local" (state stored in TF Cloud, execution on CI runner)
   - Set Working Directory to `infrastructure/terraform`
   - Set Terraform Version to `1.6.0`

3. **Create Team Token** (for terraform operations):
   - Navigate to Organization Settings -> Teams -> Select your team (e.g., "owners")
   - Go to API Token section
   - Generate a team token
   - Save it securely (you'll need this as `TF_API_TOKEN`)
   - This token performs plans and applies on workspaces

### 3. GitHub Secrets Configuration

Navigate to your GitHub repository -> Settings -> Secrets and variables -> Actions

Add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `TF_API_TOKEN` | HCP Terraform Cloud Team token | `xxx.atlasv1.xxxx` |
| `ARM_CLIENT_ID` | Azure Service Principal Client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ARM_CLIENT_SECRET` | Azure Service Principal Secret | `xxxxxxxxxxxxxxxx` |
| `ARM_SUBSCRIPTION_ID` | Azure Subscription ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ARM_TENANT_ID` | Azure Tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `ACR_ADMIN_PASSWORD` | ACR admin password (from Terraform output) | Auto-generated |
| `CODECOV_TOKEN` | Codecov upload token (optional) | `xxxxxxxx-xxxx-xxxx` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | JWT signing secret | Random secure string |
| `REDIS_URL` | Redis connection string | `redis://host:6379` |

## Pipeline Architecture

```
+-------------------------------------------------------------------------+
|                        QNT9-SRS CI/CD Pipeline                          |
+-------------------------------------------------------------------------+
|                                                                         |
|  +-------------+  +-------------+  +-------------+  +-------------+     |
|  |   Detect    |  |    Lint     |  |  Terraform  |  |    Build    |     |
|  |   Changes   |->|   & Test    |->|  Provision  |->|   Images    |     |
|  +-------------+  +-------------+  +-------------+  +-------------+     |
|         |                                                   |           |
|         v                                                   v           |
|  +-------------+                                    +-------------+     |
|  | Unit Tests  |                                    |   Deploy    |     |
|  +-------------+                                    |   to AKS    |     |
|                                                     +-------------+     |
|                                                            |            |
|                                                            v            |
|                                                     +-------------+     |
|                                                     | Integration |     |
|                                                     |    Tests    |     |
|                                                     +-------------+     |
|                                                                         |
+-------------------------------------------------------------------------+
```

## Pipeline Stages

### Stage 1: Detect Changes
- Determines target environment based on branch
- Detects which files changed (services, infrastructure)

### Stage 2: Lint & Format
- Runs Black (code formatting)
- Runs isort (import sorting)
- Runs Ruff (linting)
- Runs Bandit (security checks)
- Non-blocking - issues are reported as warnings

### Stage 3: Unit Tests
- Runs pytest for auth-service and search-service
- Uses PostgreSQL and Redis containers
- Uploads coverage to Codecov

### Stage 4: Terraform Provision
- Initializes Terraform with HCP Cloud backend
- Plans and applies infrastructure changes
- Extracts outputs (ACR, AKS details)

### Stage 5: Build Images
- Builds Docker images for all services
- Pushes to Azure Container Registry
- Scans for vulnerabilities with Trivy

### Stage 6: Deploy to AKS
- Gets AKS credentials
- Creates namespace and secrets
- Deploys services to Kubernetes

### Stage 7: Integration Tests
- Runs health checks against deployed services

## Branch to Environment Mapping

| Branch | Environment | Workspace |
|--------|-------------|-----------|
| `main` | prd | qnt9-srs-prd |
| `staging` | staging | qnt9-srs-staging |
| `development` | dev | qnt9-srs-dev |
| PRs | dev | qnt9-srs-dev |

## Manual Deployment

You can trigger a manual deployment via workflow_dispatch:

1. Go to Actions -> QNT9-SRS CI/CD Pipeline
2. Click "Run workflow"
3. Select target environment (dev/staging/prd)
4. Optionally enable "Force deployment"

## Local Development

```bash
# Set workspace
export TF_WORKSPACE=qnt9-srs-dev

# Login to Terraform Cloud
terraform login

# Initialize
cd infrastructure/terraform
terraform init

# Plan
terraform plan -var-file=environments/dev.tfvars

# Apply
terraform apply -var-file=environments/dev.tfvars
```

## Troubleshooting

### Terraform Init Fails
- Ensure workspace exists in HCP Terraform Cloud
- Check TF_API_TOKEN has correct permissions
- Verify workspace execution mode is "Local"

### Build Fails
- Check ACR credentials are correct
- Verify Dockerfile exists in service directory

### Deploy Fails
- Check AKS credentials
- Verify namespace permissions
- Check image pull secret is created

### Integration Tests Fail
- Check service endpoints are accessible
- Verify services are healthy (kubectl get pods)
