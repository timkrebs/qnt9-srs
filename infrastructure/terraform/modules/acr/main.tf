# Azure Container Registry Module

resource "azurerm_container_registry" "main" {
  name                = "acr${var.project_name}${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = var.admin_enabled

  # Enable public network access
  public_network_access_enabled = true

  # Network rule set for production
  dynamic "network_rule_set" {
    for_each = var.environment == "prd" ? [1] : []
    content {
      default_action = "Deny"

      ip_rule {
        action   = "Allow"
        ip_range = var.allowed_ip_ranges
      }
    }
  }

  # Geo-replication for production
  dynamic "georeplications" {
    for_each = var.environment == "prd" && var.sku == "Premium" ? var.georeplications : []
    content {
      location                = georeplications.value.location
      zone_redundancy_enabled = georeplications.value.zone_redundancy_enabled
      tags                    = var.tags
    }
  }

  # Encryption for production
  dynamic "encryption" {
    for_each = var.enable_encryption ? [1] : []
    content {
      enabled            = true
      key_vault_key_id   = var.encryption_key_vault_key_id
      identity_client_id = var.encryption_identity_client_id
    }
  }

  # Retention policy
  dynamic "retention_policy" {
    for_each = var.enable_retention_policy ? [1] : []
    content {
      days    = var.retention_days
      enabled = true
    }
  }

  # Trust policy for content trust
  dynamic "trust_policy" {
    for_each = var.enable_trust_policy ? [1] : []
    content {
      enabled = true
    }
  }

  tags = merge(
    var.tags,
    {
      Name        = "acr-${var.project_name}-${var.environment}"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )
}

# Role assignment for AKS to pull from ACR
resource "azurerm_role_assignment" "aks_acr_pull" {
  count                = var.aks_principal_id != null ? 1 : 0
  principal_id         = var.aks_principal_id
  role_definition_name = "AcrPull"
  scope                = azurerm_container_registry.main.id
}

# Diagnostic settings
resource "azurerm_monitor_diagnostic_setting" "acr" {
  count                      = var.log_analytics_workspace_id != null ? 1 : 0
  name                       = "acr-${var.environment}-diagnostics"
  target_resource_id         = azurerm_container_registry.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "ContainerRegistryRepositoryEvents"
  }

  enabled_log {
    category = "ContainerRegistryLoginEvents"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
