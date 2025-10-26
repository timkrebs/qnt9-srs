# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.1"
    }

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0.5"
    }

    datadog = {
      source  = "DataDog/datadog"
      version = "~> 3.40.0"
    }

    local = {
      source  = "hashicorp/local"
      version = "~> 2.4.0"
    }

    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.0.0"
    }

    null = {
      source  = "hashicorp/null"
      version = "~> 3.2.0"
    }
  }

  required_version = "~> 1.3"
}

# Azure Provider Configuration
# Uses ARM_* environment variables for authentication
# No need to explicitly set credentials here
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
  
  # Authentication via environment variables (set in HCP Terraform):
  # - ARM_CLIENT_ID
  # - ARM_CLIENT_SECRET
  # - ARM_SUBSCRIPTION_ID
  # - ARM_TENANT_ID
}

provider "datadog" {
  api_key = local.datadog_api_key
}

# HCP Vault Provider Configuration
provider "vault" {
  address   = var.vault_address
  namespace = var.vault_namespace
  token     = var.vault_token
}
