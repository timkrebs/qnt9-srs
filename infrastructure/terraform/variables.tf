# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

# Tagging Variables

variable "environment" {
  description = "Environment name (dev, stg, prd)"
  type        = string
  default     = "prd"
  
  validation {
    condition     = contains(["dev", "stg", "prd"], var.environment)
    error_message = "Environment must be dev, stg, or prd."
  }
}

variable "cost_center" {
  description = "Cost Center code for billing"
  type        = string
  default     = "CC-FIN-001"
}

variable "owner_email" {
  description = "Technical owner email address"
  type        = string
  default     = "devops@qnt9.com"
}

variable "business_owner_email" {
  description = "Business owner email address"
  type        = string
  default     = "product@qnt9.com"
}

variable "data_classification" {
  description = "Data classification level (Public, Internal, Confidential, Restricted)"
  type        = string
  default     = "Confidential"
  
  validation {
    condition     = contains(["Public", "Internal", "Confidential", "Restricted"], var.data_classification)
    error_message = "Data classification must be Public, Internal, Confidential, or Restricted."
  }
}

variable "criticality" {
  description = "System criticality level (Critical, High, Medium, Low)"
  type        = string
  default     = "High"
  
  validation {
    condition     = contains(["Critical", "High", "Medium", "Low"], var.criticality)
    error_message = "Criticality must be Critical, High, Medium, or Low."
  }
}

variable "budget_code" {
  description = "Budget allocation code"
  type        = string
  default     = "BDG-2024-Q1-SRS"
}

variable "compliance_requirements" {
  description = "Compliance frameworks (comma-separated)"
  type        = string
  default     = "GDPR,SOC2"
}

variable "data_residency" {
  description = "Data residency requirement"
  type        = string
  default     = "US"
}
