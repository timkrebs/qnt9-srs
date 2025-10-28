# QNT9-SRS CI/CD Architecture

## Overview

The QNT9 Stock Recommendation System (QNT9-SRS) implements a comprehensive Continuous Integration and Continuous Deployment (CI/CD) pipeline built on GitHub Actions, Azure Cloud Infrastructure, and HashiCorp Vault. This architecture enables automated testing, security scanning, infrastructure provisioning, and multi-environment deployments while maintaining strict security standards and cost efficiency.

![CI/CD Architecture Diagram](diagram-export-10-28-2025-10_28_09-AM.png)

## Architecture Components

### 1. Source Control and Version Management

**GitHub Repository**: Central code repository hosting all microservices, infrastructure code, and configuration files.

- **Branch Strategy**:
  - `main`: Production-ready code
  - `develop`: Development integration branch
  - Feature branches for isolated development

### 2. Continuous Integration Pipeline

The CI pipeline is triggered automatically on every push and pull request, executing multiple parallel workflows:

#### 2.1 Code Quality and Security Workflows

**Datadog Static Code Analysis**
- Analyzes code quality and identifies security vulnerabilities
- Enforces coding standards and best practices
- Configuration: `.github/workflows/datadog-static-analysis.yml`
- Runs on every push event
- Integrates with Datadog platform for centralized reporting

**Datadog Software Composition Analysis (SCA)**
- Generates Software Bill of Materials (SBOM)
- Scans dependencies for known vulnerabilities
- Validates license compliance
- Configuration: `.github/workflows/datadog-sca.yml`
- Automated dependency tracking and alerting

**Code Coverage Analysis**
- Executes unit tests with coverage measurement
- Tests against Python 3.11 and 3.12 using matrix strategy
- Uploads coverage reports to Codecov
- Configuration: `.github/workflows/codecov.yml`
- Coverage artifacts retained for 30 days
- Minimum coverage thresholds enforced

#### 2.2 Validation Stages

**Terraform Validation**
- Format checking (`terraform fmt -check`)
- Syntax validation (`terraform validate`)
- Security scanning with tfsec
- Ensures infrastructure code quality before deployment

### 3. Infrastructure as Code (IaC)

**Terraform Configuration**
- Location: `infrastructure/terraform/`
- Manages all Azure resources declaratively
- Environment-specific configurations:
  - `environments/dev.tfvars`
  - `environments/staging.tfvars`
  - `environments/prd.tfvars`

**Key Infrastructure Components**:
- Azure Kubernetes Service (AKS) cluster
- Azure Container Registry (ACR)
- Azure Database for PostgreSQL Flexible Server
- Virtual Network with subnets
- Log Analytics Workspace
- Application Insights

**Cost Optimization**:
- Burstable VM instances (Standard_B2s)
- Auto-scaling node pools (1-5 nodes)
- Basic tier ACR for non-production
- Single NAT Gateway configuration

### 4. Secrets Management

**HashiCorp Vault (HCP)**
- Centralized secrets storage
- Dynamic credentials generation
- Secrets rotation capabilities
- Vault integration points:
  - Datadog API keys
  - Azure service principal credentials
  - Database connection strings
  - Application configuration

**Vault Structure**:
```
kv/
  datadog/
    api_key
    site
  azure/
    subscription_id
    tenant_id
  database/
    connection_strings
```

### 5. Multi-Environment Deployment Strategy

#### Development Environment
- **Trigger**: Push to `develop` branch
- **Auto-deployment**: Enabled
- **Purpose**: Integration testing and development validation
- **Resources**: Minimal configuration, burstable instances

#### Staging Environment
- **Trigger**: Push to `main` branch
- **Auto-deployment**: Enabled
- **Purpose**: Pre-production validation
- **Resources**: Production-like configuration
- **Testing**: Integration tests, performance tests, UAT

#### Production Environment
- **Trigger**: Manual workflow dispatch
- **Auto-deployment**: Disabled (requires approval)
- **Purpose**: Live production system
- **Resources**: High-availability configuration
- **Safeguards**: 
  - Manual approval required
  - Production-specific Azure credentials
  - Enhanced monitoring and alerting

### 6. Container Build and Registry

**Docker Container Build Process**:
1. Dockerfile validation during CI
2. Multi-stage builds for optimization
3. Security scanning of container images
4. Push to Azure Container Registry

**Example Service**: Auth Service
- Base image: `python:3.11-slim`
- Exposed port: 8000
- FastAPI/Uvicorn runtime
- Optimized layer caching

### 7. Kubernetes Deployment

**AKS Cluster Configuration**:
- Auto-scaling enabled (1-5 nodes)
- Node VM size: Standard_B2s (2 vCPU, 4 GB RAM)
- Kubernetes version management via Terraform
- Private cluster option for enhanced security

**Deployment Resources**:
- Helm charts: `infrastructure/helm-charts/`
- Service deployments
- Ingress controllers
- ConfigMaps and Secrets

### 8. Monitoring and Observability

**Datadog Integration**:
- Application Performance Monitoring (APM)
- Infrastructure monitoring
- Log aggregation
- Custom dashboards and alerts
- SCA and Static Analysis results

**Azure Application Insights**:
- Service telemetry
- Request tracing
- Exception tracking
- Performance metrics

**Log Analytics**:
- Centralized logging for AKS
- Query and analysis capabilities
- Integration with Azure Monitor

## CI/CD Workflow Execution

### Pull Request Workflow

1. Developer creates pull request
2. Automated validation triggers:
   - Code quality checks (Datadog Static Analysis)
   - Dependency scanning (Datadog SCA)
   - Unit tests with coverage (Codecov)
   - Terraform format and validation
   - Security scanning (tfsec)
3. Terraform plan generated for dev environment
4. Plan posted as PR comment for review
5. Code review and approval
6. Merge to target branch

### Development Deployment Workflow

1. Code merged to `develop` branch
2. CI validations execute
3. Terraform automatically:
   - Initializes with dev backend
   - Applies dev.tfvars configuration
   - Provisions/updates Azure resources
4. Container images built and pushed to ACR
5. Kubernetes manifests updated
6. Services deployed to dev AKS cluster
7. Health checks and smoke tests
8. Datadog monitoring validates deployment

### Staging Deployment Workflow

1. Code merged to `main` branch
2. CI validations execute
3. Terraform automatically:
   - Initializes with staging backend
   - Applies staging.tfvars configuration
   - Provisions/updates Azure resources
4. Container images tagged for staging
5. Services deployed to staging AKS cluster
6. Integration and performance tests
7. Monitoring validation

### Production Deployment Workflow

1. Manual workflow dispatch triggered
2. Environment parameter: `prd`
3. Action parameter: `apply`
4. Production environment approval required
5. Terraform:
   - Uses production-specific Azure credentials
   - Applies prd.tfvars configuration
   - Executes with `-auto-approve` after manual trigger
6. Blue-green or canary deployment to production AKS
7. Enhanced monitoring and alerting
8. Rollback capability maintained

## Security Controls

### Secret Management
- No secrets in source code
- HCP Vault integration for dynamic secrets
- Environment-specific secret isolation
- Automatic secret rotation capabilities

### Access Controls
- GitHub environment protection rules
- Required reviewers for production
- Azure RBAC for resource access
- Kubernetes RBAC for cluster access

### Compliance and Auditing
- Software Composition Analysis (SBOM)
- Vulnerability scanning in CI pipeline
- Infrastructure security scanning (tfsec)
- Audit logs in Azure and Datadog

### Network Security
- Private AKS clusters (optional)
- Virtual Network isolation
- Network Security Groups (NSGs)
- Private endpoints for databases

## Best Practices Implemented

1. **Infrastructure as Code**: All infrastructure defined in Terraform, version-controlled and peer-reviewed

2. **Immutable Infrastructure**: Container-based deployments with versioned images

3. **Automated Testing**: Multiple test layers from unit to integration tests

4. **Security Scanning**: Multi-layered security analysis in CI pipeline

5. **Cost Optimization**: Right-sized resources with auto-scaling capabilities

6. **Observability**: Comprehensive monitoring across all environments

7. **Environment Parity**: Consistent configuration across dev, staging, and production

8. **Fail-Fast Principle**: Early validation in CI pipeline to catch issues quickly

9. **Progressive Deployment**: Manual gates for production deployments

10. **Audit Trail**: Complete deployment history and change tracking

## Troubleshooting

### Common Issues

**Terraform State Lock**:
```bash
terraform force-unlock <lock-id>
```

**Failed Deployment Rollback**:
```bash
kubectl rollout undo deployment/<service-name> -n <namespace>
```

**Vault Authentication Issues**:
```bash
export VAULT_ADDR="https://your-vault.vault.hashicorp.cloud:8200"
export VAULT_TOKEN="your-token"
export VAULT_NAMESPACE="admin"
vault kv get kv/datadog
```

**AKS Connection Issues**:
```bash
az aks get-credentials --resource-group <rg-name> --name <aks-name>
kubectl cluster-info
```

## Required GitHub Secrets

### Development/Staging Environments
- `AZURE_CREDENTIALS`: Azure service principal for dev/staging
- `DD_API_KEY`: Datadog API key
- `DD_APP_KEY`: Datadog application key
- `VAULT_ADDR`: HCP Vault address
- `VAULT_TOKEN`: Vault access token
- `VAULT_NAMESPACE`: Vault namespace (typically "admin")
- `CODECOV_TOKEN`: Codecov upload token

### Production Environment
- `AZURE_CREDENTIALS_PRD`: Dedicated Azure service principal for production
- All other secrets same as dev/staging

## Cost Estimation

**Monthly Infrastructure Costs** (approximate):
- AKS Cluster (2x Standard_B2s): ~$60
- Azure Container Registry (Basic): ~$5
- PostgreSQL Flexible Server (B_Standard_B1ms): ~$12
- Virtual Network: ~$10
- Log Analytics (5GB/month): ~$10
- **Total**: ~$97/month

Note: Production environment may have higher costs due to additional nodes and high-availability configurations.

## Continuous Improvement

The CI/CD pipeline is continuously evolving with:
- Performance optimization
- Enhanced security controls
- Improved test coverage
- Faster deployment times
- Better monitoring and observability
- Cost optimization strategies

## Support and Maintenance

For issues or questions regarding the CI/CD pipeline:
1. Check workflow logs in GitHub Actions
2. Review Terraform plan outputs
3. Consult Datadog dashboards for monitoring data
4. Reference this documentation and linked resources
5. Contact DevOps team for infrastructure issues



