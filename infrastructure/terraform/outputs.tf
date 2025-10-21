# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = module.eks.cluster_endpoint
}

output "cluster_security_group_id" {
  description = "Security group ids attached to the cluster control plane"
  value       = module.eks.cluster_security_group_id
}

output "region" {
  description = "AWS region"
  value       = var.region
}

output "cluster_name" {
  description = "Kubernetes Cluster Name"
  value       = module.eks.cluster_name
}

# Datadog Monitoring Outputs
output "datadog_agent_status" {
  description = "Command to check Datadog agent status"
  value       = "kubectl get datadogagent datadog -n default"
}

output "datadog_pods_status" {
  description = "Command to check Datadog pods"
  value       = "kubectl get pods -n default -l app.kubernetes.io/component=agent"
}

output "datadog_site" {
  description = "Datadog site URL"
  value       = "https://us3.datadoghq.com"
}
