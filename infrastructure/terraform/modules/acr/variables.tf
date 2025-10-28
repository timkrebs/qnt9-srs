variable "project_name" {
  description = "Project name for naming resources"
  type        = string
  default     = "qnt9srs"
}

variable "environment" {
  description = "Environment name (dev, staging, prd)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "sku" {
  description = "SKU for ACR (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"
}

variable "admin_enabled" {
  description = "Enable admin user for ACR"
  type        = bool
  default     = true
}

variable "allowed_ip_ranges" {
  description = "Allowed IP ranges for ACR access (production only)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "georeplications" {
  description = "List of geo-replication locations for Premium SKU"
  type = list(object({
    location                = string
    zone_redundancy_enabled = bool
  }))
  default = []
}

variable "enable_encryption" {
  description = "Enable customer-managed key encryption"
  type        = bool
  default     = false
}

variable "encryption_key_vault_key_id" {
  description = "Key Vault key ID for encryption"
  type        = string
  default     = null
}

variable "encryption_identity_client_id" {
  description = "Client ID of the managed identity for encryption"
  type        = string
  default     = null
}

variable "enable_retention_policy" {
  description = "Enable retention policy for untagged manifests"
  type        = bool
  default     = false
}

variable "retention_days" {
  description = "Number of days to retain untagged manifests"
  type        = number
  default     = 7
}

variable "enable_trust_policy" {
  description = "Enable content trust policy"
  type        = bool
  default     = false
}

variable "aks_principal_id" {
  description = "Principal ID of AKS cluster for ACR pull access"
  type        = string
  default     = null
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostics"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
