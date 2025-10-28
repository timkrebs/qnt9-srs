# Main Terraform configuration for QNT9 SRS Azure Infrastructure
# This file orchestrates all infrastructure components

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# Local variables for resource naming and tagging
locals {
  project_name = "qnt9-srs"

  # Generate unique suffix for globally unique resources
  unique_suffix = substr(md5("${var.environment}-${var.location}"), 0, 6)

  # Resource naming convention: projectname-resourcetype-environment-region
  resource_prefix = "${local.project_name}-${var.environment}"

  # Common tags applied to all resources
  common_tags = {
    Project            = "QNT9-SRS"
    Environment        = var.environment
    ManagedBy          = "Terraform"
    CostCenter         = var.cost_center
    Owner              = var.owner_email
    BusinessOwner      = var.business_owner_email
    DataClassification = var.data_classification
    Criticality        = var.criticality
    BudgetCode         = var.budget_code
    Compliance         = var.compliance_requirements
    DataResidency      = var.data_residency
    LastModified       = timestamp()
  }
}

# Resource Group - Central container for all Azure resources
resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

# Generate random password for PostgreSQL
resource "random_password" "db_password" {
  length  = 32
  special = true
  # Azure PostgreSQL password requirements
  override_special = "!#$%&*()-_=+[]{}<>:?"
  min_lower        = 1
  min_upper        = 1
  min_numeric      = 1
  min_special      = 1
}

# Storage Account for Terraform state and blob storage
resource "azurerm_storage_account" "main" {
  name                     = "qnt9srs${var.environment}${local.unique_suffix}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Security settings
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = merge(local.common_tags, {
    Purpose = "Blob Storage and Terraform State"
  })
}

# Storage Container for reports
resource "azurerm_storage_container" "reports" {
  name                  = "reports"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Storage Container for Terraform state
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# PostgreSQL Flexible Server module
module "postgresql" {
  source = "./modules/postgresql"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  resource_prefix     = local.resource_prefix

  db_name       = var.db_name
  db_username   = var.db_username
  db_password   = random_password.db_password.result
  db_sku_name   = var.db_sku_name
  db_storage_mb = var.db_storage_mb
  db_version    = var.db_version

  tags = local.common_tags
}

# AKS Cluster module
module "aks" {
  source = "./modules/aks"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  resource_prefix     = local.resource_prefix

  node_count         = var.aks_node_count
  vm_size            = var.aks_vm_size
  kubernetes_version = var.aks_kubernetes_version

  tags = local.common_tags
}

# Azure Container Registry module
module "acr" {
  source = "./modules/acr"

  project_name        = "qnt9srs"
  environment         = var.environment
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  # SKU based on environment
  sku = var.environment == "prd" ? "Standard" : "Basic"

  # Enable admin user for GitHub Actions push
  admin_enabled = true

  # Grant AKS pull access to ACR
  aks_principal_id = module.aks.kubelet_identity_object_id

  # Enable diagnostics for production
  log_analytics_workspace_id = var.environment == "prd" ? module.app_insights.log_analytics_workspace_id : null

  # Retention policy for staging and production
  enable_retention_policy = var.environment != "dev"
  retention_days          = 7

  tags = local.common_tags
}

# Application Insights module
module "app_insights" {
  source = "./modules/app-insights"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  resource_prefix     = local.resource_prefix

  tags = local.common_tags
}

# Function App module
module "function_app" {
  source = "./modules/function-app"

  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  resource_prefix      = local.resource_prefix
  storage_account_name = azurerm_storage_account.main.name
  storage_account_key  = azurerm_storage_account.main.primary_access_key
  app_insights_key     = module.app_insights.instrumentation_key

  tags = local.common_tags
}

# Key Vault module for secrets management
module "key_vault" {
  source = "./modules/key-vault"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  resource_prefix     = local.resource_prefix
  unique_suffix       = local.unique_suffix

  # Store critical secrets
  secrets = {
    postgresql-connection-string = module.postgresql.connection_string
    sendgrid-api-key             = var.sendgrid_api_key
    storage-account-key          = azurerm_storage_account.main.primary_access_key
  }

  tags = local.common_tags
}
