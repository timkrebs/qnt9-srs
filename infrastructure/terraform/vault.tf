# Vault Secrets Integration
# This file reads secrets from HCP Vault KV v2 engine

# Read Datadog secrets from Vault
data "vault_kv_secret_v2" "datadog" {
  mount = "kv"
  name  = "datadog"
}

# Local values to use Vault secrets
locals {
  datadog_api_key = data.vault_kv_secret_v2.datadog.data["datadog_api_key"]
  datadog_site    = data.vault_kv_secret_v2.datadog.data["datadog_site"]
}
