# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

# Azure Configuration Variables
# Note: Azure authentication uses ARM_* environment variables
variable "appId" {
    description = "Azure Application (Client) ID"
    type        = string
}

variable "password" {
    description = "Azure Client Secret"
    type        = string
    sensitive   = true
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "West US 2"  # Changed for better availability
}

variable "environment" {
  description = "Environment name (dev, stg, prd)"
  type        = string
  default     = "prd"
}

# Business Tags
variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "CC-FIN-001"
}

variable "owner_email" {
  description = "Email of the technical owner"
  type        = string
  default     = "devops@qnt9.com"
}

variable "business_owner_email" {
  description = "Email of the business owner"
  type        = string
  default     = "product@qnt9.com"
}

# Technical Tags
variable "data_classification" {
  description = "Data classification level (Public, Internal, Confidential, Restricted)"
  type        = string
  default     = "Confidential"
}

variable "criticality" {
  description = "System criticality (Critical, High, Medium, Low)"
  type        = string
  default     = "High"
}

# Financial Tags
variable "budget_code" {
  description = "Budget code for cost tracking"
  type        = string
  default     = "BDG-2024-Q1-SRS"
}

# Compliance Tags
variable "compliance_requirements" {
  description = "Compliance requirements (comma-separated)"
  type        = string
  default     = "GDPR,SOC2"
}

variable "data_residency" {
  description = "Data residency requirements"
  type        = string
  default     = "US"
}

# Database Configuration
variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "srs_db"
}

variable "db_username" {
  description = "PostgreSQL database administrator username"
  type        = string
  default     = "srsadmin"
}

variable "db_sku_name" {
  description = "Azure Database for PostgreSQL SKU"
  type        = string
  default     = "B_Standard_B1ms" # Burstable, cost-effective
}

variable "db_storage_mb" {
  description = "Storage size in MB"
  type        = number
  default     = 32768 # 32 GB
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "15"
}

# AKS Configuration
variable "aks_node_count" {
  description = "Default node count for AKS"
  type        = number
  default     = 2
}

variable "aks_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_B2s" # Cost-effective for development
}

variable "aks_kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = "1.30"
}

# Vault Configuration
variable "vault_address" {
  description = "HCP Vault address"
  type        = string
}

variable "vault_namespace" {
  description = "HCP Vault namespace"
  type        = string
  default     = "admin"
}

variable "vault_token" {
  description = "HCP Vault token"
  type        = string
  sensitive   = true
}

# Datadog Configuration (from Vault)
variable "datadog_api_key" {
  description = "Datadog API key (optional, will be fetched from Vault if not provided)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "datadog_site" {
  description = "Datadog site (optional, will be fetched from Vault if not provided)"
  type        = string
  default     = ""
}
