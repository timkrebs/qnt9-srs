# Outputs - Important resource IDs and endpoints for external consumption

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

# Storage Account
output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_endpoint" {
  description = "Primary blob endpoint of the storage account"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "reports_container_name" {
  description = "Name of the reports container"
  value       = azurerm_storage_container.reports.name
}

# PostgreSQL Database
output "postgresql_server_fqdn" {
  description = "FQDN of the PostgreSQL server"
  value       = module.postgresql.server_fqdn
  sensitive   = true
}

output "postgresql_database_name" {
  description = "Name of the PostgreSQL database"
  value       = module.postgresql.database_name
}

output "postgresql_connection_string" {
  description = "PostgreSQL connection string (sensitive)"
  value       = module.postgresql.connection_string
  sensitive   = true
}

# AKS Cluster
output "aks_cluster_name" {
  description = "Name of the AKS cluster"
  value       = module.aks.cluster_name
}

output "aks_cluster_id" {
  description = "ID of the AKS cluster"
  value       = module.aks.cluster_id
}

output "aks_kube_config" {
  description = "Kubernetes configuration for kubectl (sensitive)"
  value       = module.aks.kube_config
  sensitive   = true
}

output "aks_get_credentials_command" {
  description = "Command to configure kubectl"
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${module.aks.cluster_name}"
}

# Application Insights
output "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  value       = module.app_insights.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "Application Insights connection string"
  value       = module.app_insights.connection_string
  sensitive   = true
}

# Function App
output "function_app_name" {
  description = "Name of the Function App"
  value       = module.function_app.function_app_name
}

output "function_app_url" {
  description = "Default hostname of the Function App"
  value       = module.function_app.function_app_url
}

# Key Vault
output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = module.key_vault.key_vault_name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = module.key_vault.key_vault_uri
}

# Azure Container Registry
output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = module.acr.acr_name
}

output "acr_login_server" {
  description = "Login server URL for ACR"
  value       = module.acr.acr_login_server
}

output "acr_admin_username" {
  description = "ACR admin username for authentication"
  value       = module.acr.acr_admin_username
  sensitive   = true
}

output "acr_admin_password" {
  description = "ACR admin password for authentication"
  value       = module.acr.acr_admin_password
  sensitive   = true
}

# Environment Information
output "environment" {
  description = "Current environment"
  value       = var.environment
}

output "tags" {
  description = "Common tags applied to all resources"
  value       = local.common_tags
}

# Cost Tracking
output "cost_tracking_info" {
  description = "Cost tracking information"
  value = {
    cost_center = var.cost_center
    budget_code = var.budget_code
    environment = var.environment
    owner       = var.owner_email
  }
}

# Quick Start Commands
output "quick_start_commands" {
  description = "Quick start commands for accessing resources"
  value = {
    configure_kubectl = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${module.aks.cluster_name}"
    view_function_app = "az functionapp show --name ${module.function_app.function_app_name} --resource-group ${azurerm_resource_group.main.name}"
    list_secrets      = "az keyvault secret list --vault-name ${module.key_vault.key_vault_name}"
    acr_login         = "az acr login --name ${module.acr.acr_name}"
    # Note: Use 'az acr login' or retrieve credentials from Key Vault for docker login
  }
  # Mark as sensitive since it contains resource names that might be considered sensitive
  sensitive = true
}
