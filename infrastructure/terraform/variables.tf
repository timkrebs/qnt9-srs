# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
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
  description = "PostgreSQL database master username"
  type        = string
  default     = "srs_admin"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.3"
}

# HCP Vault Configuration
#variable "vault_url" {
#  description = "HCP Vault cluster URL"
#  type        = string
#  default     = ""
#}
#
#variable "vault_namespace" {
#  description = "HCP Vault namespace"
#  type        = string
#  default     = "admin"
#}
#
#variable "vault_token" {
#  description = "HCP Vault token for authentication"
#  type        = string
#  sensitive   = true
#  default     = ""
#}

# Monitoring Configuration
variable "datadog_api_key" {
  description = "Datadog API key for monitoring (optional)"
  type        = string
  sensitive   = true
  default     = ""
}
