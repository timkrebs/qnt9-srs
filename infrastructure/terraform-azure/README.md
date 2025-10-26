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

```hcl
vault_address   = "https://your-vault-cluster.vault.hashicorp.cloud:8200"
vault_namespace = "admin"
vault_token     = "your-vault-token"
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
