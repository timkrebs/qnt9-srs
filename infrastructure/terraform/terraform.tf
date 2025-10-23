# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

terraform {

  #cloud {
  #  organization = "tim-krebs-org"  # Your HCP Terraform organization
  #  workspaces {
  #    name = "qnt9-srs-prod"  # Your workspace name
  #  }
  #}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.47.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.6.1"
    }

    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0.5"
    }

    cloudinit = {
      source  = "hashicorp/cloudinit"
      version = "~> 2.3.4"
    }

    datadog = {
      source = "DataDog/datadog"
    }

    local = {
      source  = "hashicorp/local"
      version = "~> 2.4.0"
    }

    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.0.0"
    }
  }

  required_version = "~> 1.3"
}

# AWS Provider Configuration
provider "aws" {
  region = var.region
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
