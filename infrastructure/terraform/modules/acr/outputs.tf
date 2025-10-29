output "acr_id" {
  description = "ID of the Azure Container Registry"
  value       = azurerm_container_registry.acr.id
}

output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  description = "Login server URL for the ACR"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  description = "Admin username for ACR"
  value       = azurerm_container_registry.acr.admin_username
  sensitive   = true
}

output "acr_admin_password" {
  description = "Admin password for ACR"
  value       = azurerm_container_registry.acr.admin_password
  sensitive   = true
}

output "acr_identity_principal_id" {
  description = "Principal ID of the ACR managed identity"
  value       = azurerm_container_registry.acr.identity[0].principal_id
}

output "manual_role_assignment_command" {
  description = "Command to manually assign AcrPull role to AKS (use if automatic assignment is disabled)"
  value       = var.enable_aks_role_assignment ? "Role assignment managed by Terraform" : "az role assignment create --assignee ${var.aks_principal_id} --role AcrPull --scope ${azurerm_container_registry.acr.id}"
}
