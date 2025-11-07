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

# Icinga Monitoring
output "icinga_vm_public_ip" {
  description = "Public IP address of Icinga monitoring server"
  value       = azurerm_public_ip.icinga.ip_address
}

output "icinga_vm_fqdn" {
  description = "FQDN of Icinga monitoring server"
  value       = azurerm_public_ip.icinga.fqdn
}

output "icinga_web_url" {
  description = "Icinga Web interface URL"
  value       = "https://${azurerm_public_ip.icinga.ip_address}"
}

output "icinga_ssh_command" {
  description = "SSH command to connect to Icinga server"
  value       = "ssh ${var.icinga_admin_username}@${azurerm_public_ip.icinga.ip_address}"
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
    acr_login         = "az acr login --name ${module.acr.acr_name}"
    ssh_icinga        = "ssh ${var.icinga_admin_username}@${azurerm_public_ip.icinga.ip_address}"
    icinga_web        = "https://${azurerm_public_ip.icinga.ip_address}"
  }
  sensitive = true
}
