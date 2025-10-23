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

    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }

    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
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

# Kubernetes Provider Configuration
# For HCP Terraform Cloud compatibility, we use data source instead of exec
provider "kubernetes" {
  host                   = try(module.eks.cluster_endpoint, null)
  cluster_ca_certificate = try(base64decode(module.eks.cluster_certificate_authority_data), null)
  token                  = try(data.aws_eks_cluster_auth.cluster[0].token, null)
}

# Get EKS cluster authentication token (only when cluster exists)
data "aws_eks_cluster_auth" "cluster" {
  count = can(module.eks.cluster_name) ? 1 : 0
  name  = module.eks.cluster_name
}

# Helm Provider Configuration
# For HCP Terraform Cloud compatibility
provider "helm" {
  kubernetes {
    host                   = try(module.eks.cluster_endpoint, null)
    cluster_ca_certificate = try(base64decode(module.eks.cluster_certificate_authority_data), null)
    token                  = try(data.aws_eks_cluster_auth.cluster[0].token, null)
  }
}

# Vault Provider Configuration
# For HCP Vault integration
provider "vault" {
  address   = var.vault_url
  namespace = var.vault_namespace
  token     = var.vault_token
}

