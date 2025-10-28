# QNT9 SRS - Azure Infrastructure (Terraform)

This directory contains Terraform configurations for deploying the Stock Recommendation System (SRS) infrastructure on **Microsoft Azure**.

## 🚀 Migration from AWS to Azure

This infrastructure replaces the AWS-based setup with cost-effective Azure services:

| AWS Service | Azure Service | Notes |
|------------|---------------|-------|
| EKS | AKS (Azure Kubernetes Service) | Managed Kubernetes |
| ECR | ACR (Azure Container Registry) | Container registry |
| RDS PostgreSQL | Azure Database for PostgreSQL Flexible Server | Managed database |
| VPC | Virtual Network (VNet) | Network isolation |
| CloudWatch | Azure Monitor + Log Analytics | Monitoring & logging |

## 📋 Prerequisites

1. **Azure CLI**
   ```bash
   brew install azure-cli
   az login
   ```

2. **Terraform** (>= 1.3)
   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   ```

3. **kubectl**
   ```bash
   brew install kubectl
   ```

4. **Helm**
   ```bash
   brew install helm
   ```

5. **HCP Vault** credentials
   - Vault Address
   - Vault Token
   - Vault Namespace (default: `admin`)

## 🏗️ Infrastructure Components

### Azure Resources

1. **Resource Group** - Logical container for all resources
2. **Virtual Network** - Network isolation with subnets
3. **AKS Cluster** - Kubernetes cluster with auto-scaling
4. **Azure Container Registry** - Docker image storage
5. **PostgreSQL Flexible Server** - Managed database
6. **Log Analytics Workspace** - Centralized logging
7. **Private DNS Zone** - Internal DNS for PostgreSQL

### Cost Optimization Features

- **Burstable VMs**: `Standard_B2s` for AKS nodes (2 vCPU, 4 GB RAM)
- **Basic ACR Tier**: Cost-effective registry for development
- **Flexible PostgreSQL**: Burstable tier `B_Standard_B1ms`
- **Auto-scaling**: Nodes scale down when not in use (min: 1, max: 5)
- **Single NAT Gateway**: Reduced networking costs

### Estimated Monthly Costs

| Service | Configuration | Estimated Cost (USD/month) |
|---------|--------------|---------------------------|
| AKS | 2x Standard_B2s nodes | ~$60 |
| ACR | Basic tier | ~$5 |
| PostgreSQL | B_Standard_B1ms | ~$12 |
| Virtual Network | Standard | ~$10 |
| Log Analytics | 5GB/month | ~$10 |
| **Total** | | **~$97/month** |

> Note: Prices are approximate and may vary by region. Use `make cost-estimate` for detailed breakdown.

## 🔧 Configuration

### 1. Create Vault Secrets

Store Datadog credentials in HCP Vault:

```bash
vault kv put kv/datadog \
  api_key="your-datadog-api-key" \
  site="datadoghq.com"
```

### 2. Set Vault Environment Variables

```bash
export VAULT_ADDR="https://your-vault-cluster.vault.hashicorp.cloud:8200"
export VAULT_NAMESPACE="admin"
export VAULT_TOKEN="your-vault-token"
```

Or create `terraform.tfvars.secret`:

# QNT9 SRS - Azure Infrastructure (Terraform)

This directory contains Terraform configurations for deploying the Stock Recommendation System (SRS) infrastructure on **Microsoft Azure**.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Infrastructure Components](#infrastructure-components)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Outputs](#outputs)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

This infrastructure replaces the AWS-based setup with cost-effective Azure services:

| Component | Azure Service | Purpose |
|-----------|--------------|---------|
| Container Orchestration | Azure Kubernetes Service (AKS) | Managed Kubernetes cluster for microservices |
| Database | PostgreSQL Flexible Server | Managed database with automatic backups |
| Storage | Azure Blob Storage | Object storage for reports and Terraform state |
| Serverless Compute | Azure Functions | Scheduled jobs and background processing |
| Secrets Management | Azure Key Vault + HCP Vault | Secure secrets storage |
| Monitoring | Application Insights | Application performance monitoring |
| Logging | Log Analytics Workspace | Centralized logging and analytics |

## Prerequisites

### Required Tools

1. **Azure CLI** (>= 2.50)
   ```bash
   brew install azure-cli
   az login
   ```

2. **Terraform** (>= 1.3.0)
   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/terraform
   ```

3. **kubectl**
   ```bash
   brew install kubectl
   ```

4. **Helm** (>= 3.0)
   ```bash
   brew install helm
   ```

5. **HCP Vault CLI** (optional, for Vault operations)
   ```bash
   brew tap hashicorp/tap
   brew install hashicorp/tap/vault
   ```

### Azure Subscription

Ensure you have an active Azure subscription with sufficient permissions:
- Resource Group creation
- AKS cluster management
- PostgreSQL server creation
- Storage account management
- Key Vault access

### HCP Vault Setup

1. Create an HCP Vault cluster at https://portal.cloud.hashicorp.com
2. Note down:
   - Vault Address
   - Vault Token
   - Vault Namespace (usually "admin")

3. Enable KV v2 secrets engine:
   ```bash
   vault secrets enable -version=2 kv
   ```

## Quick Start

### 1. Clone and Navigate

```bash
cd infrastructure/terraform
```

### 2. Configure Environment Variables

Create a `.env` file or export variables:

```bash
export VAULT_ADDR="https://your-vault-cluster.vault.hashicorp.cloud:8200"
export VAULT_NAMESPACE="admin"
export VAULT_TOKEN="your-vault-token"
export TF_VAR_vault_address=$VAULT_ADDR
export TF_VAR_vault_namespace=$VAULT_NAMESPACE
export TF_VAR_vault_token=$VAULT_TOKEN
```

### 3. Initialize Terraform

```bash
make init ENV=dev
# or
terraform init
```

### 4. Review the Plan

```bash
make plan ENV=dev
# or
terraform plan -var-file="environments/dev.tfvars"
```

### 5. Apply Infrastructure

```bash
make apply ENV=dev
# or
terraform apply -var-file="environments/dev.tfvars"
```

### 6. Configure kubectl

```bash
make configure-kubectl
# or
az aks get-credentials --resource-group <resource-group> --name <aks-cluster>
```

## Infrastructure Components

### Core Resources

#### 1. Resource Group
- **Purpose**: Logical container for all Azure resources
- **Naming**: `qnt9-srs-{env}-rg`
- **Location**: Configurable per environment

#### 2. Azure Kubernetes Service (AKS)
- **Purpose**: Managed Kubernetes cluster for microservices
- **Node Pool**: Auto-scaling (min: 1, max: node_count + 3)
- **VM Size**: `Standard_B2s` (dev), `Standard_D4s_v3` (prod)
- **Features**:
  - Azure AD integration
  - Azure RBAC
  - Container Insights monitoring
  - Auto-scaling enabled

#### 3. PostgreSQL Flexible Server
- **Purpose**: Managed relational database
- **Version**: PostgreSQL 16
- **SKU**: `B_Standard_B1ms` (dev), `GP_Standard_D2s_v3` (prod)
- **Backup**: 7-day retention
- **Security**: SSL required, Azure firewall rules

#### 4. Azure Blob Storage
- **Purpose**: Object storage for reports and Terraform state
- **Tier**: Standard with LRS replication
- **Features**:
  - Versioning enabled
  - Soft delete (7 days)
  - Private access only
  - TLS 1.2 minimum

#### 5. Azure Functions
- **Purpose**: Serverless compute for scheduled jobs
- **Runtime**: Python 3.11
- **Plan**: Consumption (Y1)
- **Integration**: Application Insights for monitoring

#### 6. Azure Key Vault
- **Purpose**: Secrets management
- **Features**:
  - Soft delete enabled
  - Access policies for Terraform
  - Integration with HCP Vault

#### 7. Application Insights
- **Purpose**: Application monitoring and telemetry
- **Features**:
  - Log Analytics workspace integration
  - 30-day retention
  - Custom metrics and traces

### Modules Structure

```
modules/
├── aks/                    # Azure Kubernetes Service
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── postgresql/             # PostgreSQL Flexible Server
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── app-insights/           # Application Insights
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── function-app/           # Azure Functions
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
└── key-vault/              # Azure Key Vault
    ├── main.tf
    ├── variables.tf
    └── outputs.tf
```

## Configuration

### Environment-Specific Variables

Three environment configurations are provided:

#### Development (`environments/dev.tfvars`)
- Minimal resources for cost savings
- 1 AKS node
- Burstable PostgreSQL tier
- Internal data classification

#### Staging (`environments/staging.tfvars`)
- Production-like configuration
- 2 AKS nodes
- General Purpose PostgreSQL tier
- Confidential data classification

#### Production (`environments/prd.tfvars`)
- High availability configuration
- 3 AKS nodes
- General Purpose PostgreSQL tier with higher storage
- Confidential data classification

### Required Variables

All environments require these variables (see `variables.tf`):

```hcl
# Azure Configuration
location                   # Azure region
environment               # dev, staging, or prd

# Business Information
cost_center               # Cost center code
owner_email              # Technical owner email
business_owner_email     # Business owner email
budget_code              # Budget tracking code

# Technical
data_classification      # Data classification level
criticality              # System criticality

# Compliance
compliance_requirements  # Comma-separated compliance standards
data_residency          # Data residency requirement

# Database
db_name                 # PostgreSQL database name
db_username             # PostgreSQL admin username
db_sku_name            # PostgreSQL SKU
db_storage_mb          # Storage size in MB
db_version             # PostgreSQL version

# AKS
aks_node_count         # Number of AKS nodes
aks_vm_size            # VM size for nodes
aks_kubernetes_version # Kubernetes version
```

### Sensitive Variables

Store sensitive values in HCP Vault or environment variables:

```bash
export TF_VAR_vault_address="https://your-vault.hashicorp.cloud:8200"
export TF_VAR_vault_token="your-vault-token"
export TF_VAR_sendgrid_api_key="your-sendgrid-key"
```

## Deployment

### Using Make (Recommended)

```bash
# Initialize Terraform
make init ENV=dev

# Validate configuration
make validate

# Format Terraform files
make format

# Create execution plan
make plan ENV=dev

# Apply changes
make apply ENV=dev

# View outputs
make output ENV=dev

# Configure kubectl
make configure-kubectl

# Destroy infrastructure
make destroy ENV=dev
```

### Using Terraform CLI

```bash
# Initialize
terraform init

# Plan
terraform plan -var-file="environments/dev.tfvars" -out=tfplan

# Apply
terraform apply tfplan

# Destroy
terraform destroy -var-file="environments/dev.tfvars"
```

### Deployment Workflow

1. **Development**: Test changes in dev environment first
2. **Staging**: Promote tested changes to staging
3. **Production**: Deploy to production after staging validation

```bash
# Development workflow
make dev-plan
make dev-apply

# Staging workflow
make plan ENV=staging
make apply ENV=staging

# Production workflow (requires extra confirmation)
make prd-plan
make prd-apply
```

## Outputs

After successful deployment, Terraform provides these outputs:

```bash
# View all outputs
terraform output

# View specific output
terraform output postgresql_connection_string

# Export to JSON
terraform output -json > outputs.json
```

### Key Outputs

- `resource_group_name`: Resource group name
- `aks_cluster_name`: AKS cluster name
- `aks_get_credentials_command`: Command to configure kubectl
- `postgresql_server_fqdn`: PostgreSQL server FQDN
- `postgresql_connection_string`: Database connection string (sensitive)
- `storage_account_name`: Storage account name
- `function_app_url`: Function App URL
- `key_vault_name`: Key Vault name
- `app_insights_instrumentation_key`: Application Insights key (sensitive)

## Cost Optimization

### Estimated Monthly Costs

| Environment | Configuration | Estimated Cost (USD) |
|------------|---------------|---------------------|
| Development | 1 node, Burstable tier | ~$97/month |
| Staging | 2 nodes, GP tier | ~$350/month |
| Production | 3 nodes, GP tier, HA | ~$650/month |

### Cost-Saving Features

1. **Auto-scaling**: AKS nodes scale down when not in use
2. **Burstable VMs**: Development uses cost-effective B-series VMs
3. **Consumption Plan**: Functions use pay-per-execution model
4. **Storage Optimization**: Local redundancy for non-critical data
5. **Resource Tagging**: All resources tagged for cost tracking

### Cost Estimation

```bash
# Estimate costs before deployment
make cost-estimate ENV=dev

# Requires infracost CLI
brew install infracost
infracost auth login
infracost breakdown --path . --terraform-var-file environments/dev.tfvars
```

## Troubleshooting

### Common Issues

#### 1. Terraform Init Fails

```bash
# Clean cache and reinitialize
make clean
make init ENV=dev
```

#### 2. Azure Authentication Issues

```bash
# Re-authenticate with Azure
az login
az account set --subscription <subscription-id>
```

#### 3. Vault Connection Errors

```bash
# Verify Vault connectivity
export VAULT_ADDR="your-vault-address"
export VAULT_TOKEN="your-token"
vault status
```

#### 4. Resource Name Conflicts

If resources with the same name exist:
- Modify `unique_suffix` generation in `main.tf`
- Or manually destroy conflicting resources

#### 5. AKS Credential Issues

```bash
# Reset kubectl credentials
az aks get-credentials --resource-group <rg-name> --name <aks-name> --overwrite-existing
```

### Validation Commands

```bash
# Validate Terraform syntax
terraform validate

# Check formatting
terraform fmt -check -recursive

# Show current state
terraform show

# List resources
terraform state list
```

### Logging and Debugging

```bash
# Enable Terraform debug logging
export TF_LOG=DEBUG
export TF_LOG_PATH=terraform-debug.log

# Run Terraform command
terraform apply -var-file="environments/dev.tfvars"

# Disable logging
unset TF_LOG
unset TF_LOG_PATH
```

## Security Best Practices

1. **Never commit secrets**: Use `.gitignore` for sensitive files
2. **Use HCP Vault**: Store all secrets in Vault
3. **Enable RBAC**: Azure AD integration enabled on AKS
4. **Network isolation**: Use private endpoints in production
5. **Audit logging**: Enable Azure Monitor for all resources
6. **Least privilege**: Use managed identities where possible
7. **Encryption**: TLS 1.2 minimum, data encrypted at rest

## Maintenance

### Regular Tasks

1. **Update Kubernetes version**: Review AKS release notes monthly
2. **Patch PostgreSQL**: Apply security patches during maintenance windows
3. **Review costs**: Monitor Azure Cost Management weekly
4. **Backup verification**: Test PostgreSQL backup restoration quarterly
5. **Security scanning**: Run Terraform security scans before deployment

### Terraform State Management

State is stored in HCP Terraform Cloud for:
- Remote collaboration
- State locking
- Version history
- Secure storage

Alternative: Azure Blob Storage backend (see `backend.tf`)

## Contributing

When making changes to infrastructure:

1. Create a feature branch
2. Test in dev environment
3. Run `make validate` and `make format`
4. Create PR with plan output
5. Get approval before merging
6. Apply to staging, then production

## Support

For issues or questions:
- Technical Owner: devops@qnt9.com
- Business Owner: product@qnt9.com

## License

Copyright 2024 QNT9 - All Rights Reserved
```

### 3. Customize Variables (Optional)

Edit `terraform.tfvars` to adjust:
- Azure region
- VM sizes
- Database configuration
- Node counts

## 🚦 Deployment

### Quick Start

```bash
# Initialize and deploy everything
make all

# Or step by step:
make init      # Initialize Terraform
make validate  # Validate configuration
make plan      # Preview changes
make apply     # Apply changes
```

### Manual Steps

```bash
# 1. Initialize
terraform init

# 2. Plan
terraform plan -out=tfplan

# 3. Apply
terraform apply tfplan

# 4. Configure kubectl
make aks-creds

# 5. Verify
kubectl get nodes
```

## 🔐 Access Configuration

### Configure kubectl for AKS

```bash
make aks-creds
# Or manually:
az aks get-credentials --name <cluster-name> --resource-group <rg-name>
```

### Login to ACR

```bash
make acr-login
# Or manually:
az acr login --name <acr-name>
```

### Build and Push Images

```bash
# Build image
docker build -t <acr-name>.azurecr.io/qnt9-srs/auth-service:v1.0 ./services/auth-service

# Push to ACR
docker push <acr-name>.azurecr.io/qnt9-srs/auth-service:v1.0
```

## 🗄️ Database Access

### Connection Details

Database credentials are stored in Vault at `kv/azure/postgresql`:

```bash
vault kv get kv/azure/postgresql
```

### Connect to PostgreSQL

```bash
# Get FQDN
PGHOST=$(terraform output -raw db_server_fqdn)

# Get password from Vault
PGPASSWORD=$(vault kv get -field=password kv/azure/postgresql)

# Connect
psql "postgresql://srsadmin:${PGPASSWORD}@${PGHOST}:5432/srs_db?sslmode=require"
```

## 📊 Monitoring

### Datadog Integration

Datadog is automatically configured:
- Cluster monitoring
- Container metrics
- Log collection
- APM enabled

Access your cluster in Datadog: https://app.datadoghq.com/infrastructure/map

### Azure Monitor

```bash
# View logs
az monitor log-analytics query \
  --workspace $(terraform output -raw log_analytics_workspace_id) \
  --analytics-query "ContainerLog | limit 100"
```

## 🔄 Vault Database Engine (Optional)

To enable dynamic database credentials:

```bash
cd ../scripts
./setup-vault-db-engine.sh
```

This creates:
- Database connection in Vault
- Roles for auth-service
- Dynamic credential generation

## 📦 Outputs

Key outputs after deployment:

```bash
terraform output cluster_name              # AKS cluster name
terraform output acr_login_server          # ACR URL
terraform output db_server_fqdn            # PostgreSQL FQDN
terraform output aks_get_credentials_command # kubectl setup command
```

## 🧹 Cleanup

```bash
# Destroy all resources
make destroy

# Or manually
terraform destroy
```

## 📁 File Structure

```
terraform-azure/
├── main.tf                 # Core infrastructure (VNet, AKS, PostgreSQL)
├── acr.tf                  # Container registry
├── vault.tf                # Vault integration
├── helm_datadog.tf         # Datadog monitoring
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── terraform.tf            # Provider configuration
├── terraform.tfvars        # Variable values
├── datadog-agent.yaml.tpl  # Datadog manifest template
├── Makefile                # Automation commands
└── README.md               # This file
```

## 🆘 Troubleshooting

### AKS Access Issues

```bash
# Re-configure kubectl
make aks-creds

# Verify connection
kubectl cluster-info
```

### Database Connection Issues

```bash
# Check PostgreSQL firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group <rg-name> \
  --name <server-name>

# Test connection
make test-db
```

### ACR Access Issues

```bash
# Verify ACR role assignment
az role assignment list \
  --scope $(terraform output -raw acr_id) \
  --query "[?roleDefinitionName=='AcrPull']"
```

## 📚 Additional Resources

- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [Azure Database for PostgreSQL](https://docs.microsoft.com/en-us/azure/postgresql/)
- [Azure Container Registry](https://docs.microsoft.com/en-us/azure/container-registry/)
- [HCP Vault Documentation](https://developer.hashicorp.com/vault)
- [Datadog Azure Integration](https://docs.datadoghq.com/integrations/azure/)

## 🔗 Related Documentation

- [Architecture Overview](../../docs/MicroserviceArchitecture.md)
- [Vault Configuration](../../docs/VAULT_TERRAFORM_AUTOMATION.md)
- [Database Secrets Engine](../../docs/DATABASE_SECRETS_ENGINE.md)

## 📝 License

Copyright (c) HashiCorp, Inc.
SPDX-License-Identifier: MPL-2.0
