# HCP Vault Integration for Azure
# This configuration reads secrets from HCP Vault and configures database secret engine

# Read Datadog credentials from Vault (optional)
data "vault_kv_secret_v2" "datadog" {
  count = var.enable_vault_integration && var.datadog_api_key == "" ? 1 : 0
  mount = "kv"
  name  = "datadog"
}

locals {
  datadog_api_key = var.datadog_api_key != "" ? var.datadog_api_key : try(data.vault_kv_secret_v2.datadog[0].data["api_key"], "")
  datadog_site    = var.datadog_site != "" ? var.datadog_site : try(data.vault_kv_secret_v2.datadog[0].data["site"], "datadoghq.com")
}

# Store PostgreSQL root credentials in Vault KV (optional)
resource "vault_kv_secret_v2" "postgresql" {
  count = var.enable_vault_integration ? 1 : 0
  mount = "kv"
  name  = "azure/postgresql"

  data_json = jsonencode({
    host              = module.postgresql.server_fqdn
    port              = 5432
    database          = var.db_name
    username          = var.db_username
    password          = random_password.db_password.result
    connection_string = module.postgresql.connection_string
  })

  depends_on = [module.postgresql]
}

# Output Vault information
output "vault_postgresql_path" {
  description = "Vault KV path for PostgreSQL credentials"
  value       = var.enable_vault_integration ? "kv/azure/postgresql" : "Vault integration disabled"
}
