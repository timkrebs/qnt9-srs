# Azure Container Registry Configuration
# This file manages ACR for all microservices

# Azure Container Registry
resource "azurerm_container_registry" "main" {
  name                = "acrsrs${var.environment}${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic" # Basic is most cost-effective, Standard/Premium for production
  admin_enabled       = false   # Use managed identity instead

  tags = merge(
    local.common_tags,
    {
      Name        = "acr-srs-${var.environment}"
      Description = "Container registry for SRS microservices"
    }
  )
}

# Attach ACR to AKS using managed identity
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# Optional: Create retention policy (requires Premium SKU)
# Uncomment if using Premium SKU
# resource "azurerm_container_registry_task" "retention" {
#   name                  = "retention-task"
#   container_registry_id = azurerm_container_registry.main.id
#   
#   platform {
#     os = "Linux"
#   }
#   
#   docker_step {
#     dockerfile_path      = "Dockerfile"
#     context_path         = "https://github.com/Azure-Samples/acr-tasks.git"
#     context_access_token = ""
#     image_names          = ["sample/hello-world:{{.Run.ID}}"]
#   }
# }

# Output ACR login server
output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.main.login_server
}

output "acr_name" {
  description = "ACR name"
  value       = azurerm_container_registry.main.name
}
