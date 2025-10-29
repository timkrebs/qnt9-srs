variable "acr_name" {
  description = "Name of the Azure Container Registry"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for the ACR"
  type        = string
}

variable "sku" {
  description = "SKU tier for ACR (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"

  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.sku)
    error_message = "SKU must be Basic, Standard, or Premium."
  }
}

variable "admin_enabled" {
  description = "Enable admin user for ACR (needed for basic auth)"
  type        = bool
  default     = true
}

variable "public_network_access_enabled" {
  description = "Enable public network access to ACR"
  type        = bool
  default     = true
}

variable "network_rule_set_enabled" {
  description = "Enable network rule set for ACR"
  type        = bool
  default     = false
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges for ACR access"
  type        = string
  default     = "0.0.0.0/0"
}

variable "georeplications" {
  description = "List of georeplications for ACR"
  type = list(object({
    location                = string
    zone_redundancy_enabled = bool
  }))
  default = []
}

variable "aks_principal_id" {
  description = "Principal ID of AKS for ACR pull role assignment"
  type        = string
  default     = ""
}

variable "enable_aks_role_assignment" {
  description = "Enable automatic role assignment for AKS to pull from ACR. Requires elevated permissions (User Access Administrator or Owner role)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to ACR"
  type        = map(string)
  default     = {}
}
