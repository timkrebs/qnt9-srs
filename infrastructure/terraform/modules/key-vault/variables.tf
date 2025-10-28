variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_prefix" {
  description = "Prefix for resource naming"
  type        = string
}

variable "unique_suffix" {
  description = "Unique suffix for globally unique resources"
  type        = string
}

variable "secrets" {
  description = "Map of secrets to store in Key Vault (keys are secret names, values are secret values)"
  type        = map(string)
  default     = {}
  # Note: Cannot mark as sensitive because it's used in for_each
  # Individual secret values are still protected in Key Vault
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
