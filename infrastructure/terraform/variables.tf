# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "datadog_api_key" {
  description = "Datadog API Key for monitoring"
  type        = string
  sensitive   = true
}
