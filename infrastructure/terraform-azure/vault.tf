# HCP Vault Integration for Azure
# This configuration reads secrets from HCP Vault and configures database secret engine

# Read Datadog credentials from Vault (optional)
data "vault_kv_secret_v2" "datadog" {
  count = var.datadog_api_key == "" ? 1 : 0
  mount = "kv"
  name  = "datadog"
}

locals {
  datadog_api_key = var.datadog_api_key != "" ? var.datadog_api_key : try(data.vault_kv_secret_v2.datadog[0].data["api_key"], "")
  datadog_site    = var.datadog_site != "" ? var.datadog_site : try(data.vault_kv_secret_v2.datadog[0].data["site"], "datadoghq.com")
}

# Store PostgreSQL root credentials in Vault KV
resource "vault_kv_secret_v2" "postgresql" {
  mount = "kv"
  name  = "azure/postgresql"

  data_json = jsonencode({
    host     = azurerm_postgresql_flexible_server.main.fqdn
    port     = 5432
    database = var.db_name
    username = var.db_username
    password = random_password.db_password.result
    connection_string = "postgresql://${var.db_username}:${random_password.db_password.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.db_name}?sslmode=require"
  })

  depends_on = [azurerm_postgresql_flexible_server.main]
}

# Output Vault information
output "vault_postgresql_path" {
  description = "Vault KV path for PostgreSQL credentials"
  value       = "kv/azure/postgresql"
}
