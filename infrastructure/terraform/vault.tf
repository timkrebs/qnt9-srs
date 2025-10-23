# ===================================================
# Vault Data Sources
# ===================================================

# Read Datadog secrets from HCP Vault KV store
data "vault_kv_secret_v2" "datadog" {
  mount = "kv"
  name  = "datadog"
}
