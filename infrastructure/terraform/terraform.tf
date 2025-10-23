# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

terraform {

  # cloud {
  #   workspaces {
  #     name = "learn-terraform-eks"
  #   }
  # }

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

    vault = {
      source  = "hashicorp/vault"
      version = "~> 4.0"
    }
  }

  required_version = "~> 1.3"
}

# AWS Provider Configuration
provider "aws" {
  region = var.region
}

# HCP Vault Provider Configuration
provider "vault" {
  address   = var.vault_url
  namespace = var.vault_namespace
  token     = var.vault_token
}