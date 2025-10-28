# Azure Container Registry Module
# Manages Docker container images for microservices

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  # Enable admin user for basic authentication (needed for GitHub Actions)
  admin_enabled = var.admin_enabled

  # Public network access
  public_network_access_enabled = var.public_network_access_enabled

  # Network rule set for additional security
  dynamic "network_rule_set" {
    for_each = var.network_rule_set_enabled ? [1] : []
    content {
      default_action = "Deny"

      ip_rule {
        action   = "Allow"
        ip_range = var.allowed_ip_ranges
      }
    }
  }

  # Enable georeplications for production
  dynamic "georeplications" {
    for_each = var.georeplications
    content {
      location                = georeplications.value.location
      zone_redundancy_enabled = georeplications.value.zone_redundancy_enabled
      tags                    = var.tags
    }
  }

  # Identity for managed identity scenarios
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Role assignment for AKS to pull images from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  count                = var.aks_principal_id != null ? 1 : 0
  principal_id         = var.aks_principal_id
  role_definition_name = "AcrPull"
  scope                = azurerm_container_registry.acr.id
}
