# HCP Vault Integration for Azure
# This configuration manages secrets in HCP Vault for the QNT9 SRS application

# Note: PostgreSQL is now handled by Supabase (external service)
# Datadog monitoring has been replaced by Icinga (self-hosted)
# Azure Key Vault has been removed in favor of HCP Vault

# Store storage account key in Vault (optional)
resource "vault_kv_secret_v2" "storage_account" {
  count = var.enable_vault_integration ? 1 : 0
  mount = "kv"
  name  = "azure/storage"

  data_json = jsonencode({
    account_name  = azurerm_storage_account.main.name
    account_key   = azurerm_storage_account.main.primary_access_key
    blob_endpoint = azurerm_storage_account.main.primary_blob_endpoint
  })

  depends_on = [azurerm_storage_account.main]
}

# Store ACR credentials in Vault (optional)
resource "vault_kv_secret_v2" "acr" {
  count = var.enable_vault_integration ? 1 : 0
  mount = "kv"
  name  = "azure/acr"

  data_json = jsonencode({
    login_server   = module.acr.acr_login_server
    admin_username = module.acr.acr_admin_username
    admin_password = module.acr.acr_admin_password
  })

  depends_on = [module.acr]
}

# Store Icinga credentials in Vault (optional)
resource "vault_kv_secret_v2" "icinga" {
  count = var.enable_vault_integration ? 1 : 0
  mount = "kv"
  name  = "azure/icinga"

  data_json = jsonencode({
    public_ip = azurerm_public_ip.icinga.ip_address
    ssh_user  = var.icinga_admin_username
    web_url   = "https://${azurerm_public_ip.icinga.ip_address}"
    api_url   = "https://${azurerm_public_ip.icinga.ip_address}:5665"
  })

  depends_on = [azurerm_public_ip.icinga]
}

# Output Vault information
output "vault_storage_path" {
  description = "Vault KV path for Storage Account credentials"
  value       = var.enable_vault_integration ? "kv/azure/storage" : "Vault integration disabled"
}

output "vault_acr_path" {
  description = "Vault KV path for ACR credentials"
  value       = var.enable_vault_integration ? "kv/azure/acr" : "Vault integration disabled"
}

output "vault_icinga_path" {
  description = "Vault KV path for Icinga information"
  value       = var.enable_vault_integration ? "kv/azure/icinga" : "Vault integration disabled"
}
