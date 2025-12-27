# CI/CD Pipeline Setup Guide

This guide explains how to set up and configure the QNT9-SRS CI/CD pipeline with HCP Terraform Cloud and Azure (AKS & ACR).

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

2. **Create API Tokens** (you need TWO different tokens):

   **Organization Token** (for workspace management):
   - Navigate to Organization Settings → API Tokens → Organization Token
   - Generate an organization token
   - Save it securely (you'll need this as `TF_CLOUD_ORGANIZATION`)
   - This token manages teams, team membership, and workspaces
   - ⚠️ Cannot perform plans/applies in workspaces

   **Team Token** (for terraform operations):
   - Navigate to Organization Settings → Teams → Select your team (e.g., "owners")
   - Go to API Token section
   - Generate a team token
   - Save it securely (you'll need this as `TF_API_TOKEN`)
   - This token performs plans and applies on workspaces

3. **Create Initial Workspaces** (optional, CI/CD will create them automatically):
```bash
# Production workspace (persistent)
# Name: qnt9-srs-prd
# Tags: qnt9-srs, prd, persistent

# Development workspace (can be ephemeral)
# Name: qnt9-srs-dev
# Tags: qnt9-srs, dev, ephemeral
```

### 3. GitHub Secrets Configuration

Navigate to your GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `TF_CLOUD_ORGANIZATION` | HCP Terraform Cloud **Organization** token (for workspace management) | `xxx.atlasv1.xxxx` |
| `TF_API_TOKEN` | HCP Terraform Cloud **Team** token (for plan/apply) | `xxx.atlasv1.xxxx` |
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
┌─────────────────────────────────────────────────────────────────────────┐
│                        QNT9-SRS CI/CD Pipeline                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   Detect    │  │    Lint     │  │  Terraform  │  │    Build    │   │
│  │   Changes   │──│   & Test    │──│  Provision  │──│   Images    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│         │                                                   │          │
│         v                                                   v          │
│  ┌─────────────┐                                    ┌─────────────┐   │
│  │ Environment │                                    │    Push     │   │
│  │  Detection  │                                    │   to ACR    │   │
│  └─────────────┘                                    └─────────────┘   │
│                                                             │          │
│                         ┌───────────────────────────────────┘          │
│                         v                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │   Deploy    │  │ Integration │  │   Cleanup   │  │   Summary   │   │
│  │   to AKS    │──│    Tests    │──│  (ephemeral)│──│   Report    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Environment Strategy

| Branch | Environment | Ephemeral | Infrastructure Lifecycle |
|--------|-------------|-----------|--------------------------|
| `main` | prd | false | Persistent |
| `staging` | staging | true | Created/Destroyed per run |
| `development` | dev | true | Created/Destroyed per run |
| `feature/**` | dev | true | Created/Destroyed per run |
| Pull Requests | dev | true | Created/Destroyed per run |

## Workspace Naming Convention

- **Production**: `qnt9-srs-prd`
- **Staging**: `qnt9-srs-staging-run<number>`
- **Development**: `qnt9-srs-dev-run<number>` or `qnt9-srs-dev-pr<number>`

## Local Development

### Initialize and Plan

```bash
cd infrastructure/terraform

# Login to Terraform Cloud
terraform login

# Set workspace
export TF_WORKSPACE=qnt9-srs-dev

# Initialize
terraform init

# Plan
terraform plan -var-file=environments/dev.tfvars
```

### Using Make Commands

```bash
# Show available commands
make help

# Validate configuration
make test-local

# Plan for dev
make plan ENV=dev

# Apply changes
make apply ENV=dev

# Get AKS credentials
make aks-creds
```

## Triggering the Pipeline

### Automatic Triggers

- **Push to development**: Deploys to dev environment
- **Push to staging**: Deploys to staging environment
- **Push to main**: Deploys to production environment
- **Pull Request**: Deploys ephemeral dev environment

### Manual Trigger

1. Go to Actions → QNT9-SRS CI/CD Pipeline
2. Click "Run workflow"
3. Select:
   - **environment**: Target environment (dev, staging, prd)
   - **skip_destroy**: Keep infrastructure after run (for debugging)
   - **force_deploy**: Deploy even without code changes

## Monitoring & Troubleshooting

### View Pipeline Status

- GitHub Actions: Repository → Actions tab
- Terraform Cloud: app.terraform.io → Workspaces

### Common Issues

#### 1. Terraform Workspace Creation Failed
```
Check: TF_API_TOKEN is valid and has permissions
Fix: Regenerate API token in Terraform Cloud
```

#### 2. Azure Authentication Failed
```
Check: ARM_* secrets are correctly set
Fix: Recreate service principal and update secrets
```

#### 3. AKS Deployment Failed
```
Check: kubectl get pods -n qnt9
Check: kubectl describe pod <pod-name> -n qnt9
Fix: Review deployment logs and resource limits
```

#### 4. ACR Push Failed
```
Check: ACR credentials are correct
Fix: Get password from Terraform output:
     terraform output -raw acr_admin_password
```

### Viewing Logs

```bash
# AKS Pod logs
kubectl logs -n qnt9 deployment/auth-service

# All pods status
kubectl get pods -n qnt9 -o wide

# Service endpoints
kubectl get services -n qnt9
```

## Cost Optimization

### Ephemeral Infrastructure

For dev and staging, infrastructure is automatically destroyed after pipeline completion:
- Single AKS node (vs 2-5 for production)
- Smaller VM size (Standard_B2s)
- No Icinga monitoring VM
- No Function App

### Skip Destroy (for debugging)

When debugging, use `skip_destroy: true` to keep infrastructure:
```yaml
# In workflow_dispatch
skip_destroy: true
```

Remember to manually clean up:
```bash
# Via Terraform Cloud UI or CLI
terraform workspace select qnt9-srs-dev-run123
terraform destroy
```

## Security Considerations

1. **Secrets**: All secrets are stored in GitHub Secrets, never in code
2. **Service Principal**: Use least-privilege access where possible
3. **Network**: Consider enabling private AKS clusters for production
4. **Image Scanning**: Trivy scans all images for vulnerabilities
5. **Code Scanning**: Bandit scans Python code for security issues

## Related Documentation

- [CICD-Pipeline-Architecture.md](./CICD-GH-Actions/CICD-Pipeline-Architecture.md)
- [CICD-Architecture.md](./CICD-Architecture/CICD-Architecture.md)
- [Terraform README](../infrastructure/terraform/README.md)
- [Kubernetes README](../infrastructure/kubernetes/README.md)
