# Provider configuration for Azure and HashiCorp Vault

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }

    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "vault" {
  address   = var.vault_address
  namespace = var.vault_namespace
  token     = var.vault_token

  # Skip TLS verification for local development (remove in production)
  skip_tls_verify = false
}

provider "random" {
  # Random provider for generating passwords and unique identifiers
}
