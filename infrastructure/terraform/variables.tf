# Core Azure Configuration
variable "location" {
  description = "Azure region where resources will be deployed"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prd)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prd"], var.environment)
    error_message = "Environment must be dev, staging, or prd."
  }
}

# Business Information
variable "cost_center" {
  description = "Cost center for billing and chargeback"
  type        = string
}

variable "owner_email" {
  description = "Email of the technical owner"
  type        = string
}

variable "business_owner_email" {
  description = "Email of the business owner"
  type        = string
}

variable "budget_code" {
  description = "Budget code for financial tracking"
  type        = string
}

# Technical Configuration
variable "data_classification" {
  description = "Data classification level (Public, Internal, Confidential, Restricted)"
  type        = string

  validation {
    condition     = contains(["Public", "Internal", "Confidential", "Restricted"], var.data_classification)
    error_message = "Data classification must be Public, Internal, Confidential, or Restricted."
  }
}

variable "criticality" {
  description = "System criticality level (Low, Medium, High, Critical)"
  type        = string

  validation {
    condition     = contains(["Low", "Medium", "High", "Critical"], var.criticality)
    error_message = "Criticality must be Low, Medium, High, or Critical."
  }
}

# Compliance
variable "compliance_requirements" {
  description = "Comma-separated list of compliance requirements (e.g., GDPR,SOC2)"
  type        = string
}

variable "data_residency" {
  description = "Data residency requirement"
  type        = string
}

# Database Configuration
variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
}

variable "db_username" {
  description = "PostgreSQL administrator username"
  type        = string
}

variable "db_sku_name" {
  description = "PostgreSQL SKU name (e.g., B_Standard_B1ms)"
  type        = string
  default     = "B_Standard_B1ms"
}

variable "db_storage_mb" {
  description = "PostgreSQL storage size in MB"
  type        = number
  default     = 32768
}

variable "db_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "16"
}

# AKS Configuration
variable "aks_node_count" {
  description = "Number of nodes in the AKS cluster"
  type        = number
  default     = 2

  validation {
    condition     = var.aks_node_count >= 1 && var.aks_node_count <= 10
    error_message = "AKS node count must be between 1 and 10."
  }
}

variable "aks_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_B2s"
}

variable "aks_kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = "1.31.11"
}

# HCP Vault Configuration
variable "vault_address" {
  description = "HCP Vault address"
  type        = string
  default     = ""
  sensitive   = true
}

variable "vault_namespace" {
  description = "HCP Vault namespace"
  type        = string
  default     = "admin"
}

variable "vault_token" {
  description = "HCP Vault token"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_vault_integration" {
  description = "Enable HCP Vault integration for storing secrets"
  type        = bool
  default     = false
}

# Monitoring Configuration (Optional)
variable "datadog_api_key" {
  description = "Datadog API key for monitoring"
  type        = string
  default     = ""
  sensitive   = true
}

variable "datadog_site" {
  description = "Datadog site (e.g., datadoghq.com, datadoghq.eu)"
  type        = string
  default     = "datadoghq.com"
}

# Networking (Optional for future)
variable "enable_vnet" {
  description = "Enable Virtual Network for AKS"
  type        = bool
  default     = false
}

variable "vnet_address_space" {
  description = "Address space for Virtual Network"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

# SendGrid Configuration
variable "sendgrid_api_key" {
  description = "SendGrid API key for email services"
  type        = string
  default     = ""
  sensitive   = true
}
