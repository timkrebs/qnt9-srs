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

# Database outputs
output "db_instance_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.postgresql.endpoint
}

output "db_instance_address" {
  description = "The address of the RDS instance"
  value       = aws_db_instance.postgresql.address
}

output "db_instance_port" {
  description = "The port of the RDS instance"
  value       = aws_db_instance.postgresql.port
}

output "db_instance_name" {
  description = "The database name"
  value       = aws_db_instance.postgresql.db_name
}


output "db_connection_string" {
  description = "PostgreSQL connection string for FastAPI (without password)"
  value       = "postgresql://${var.db_username}@${aws_db_instance.postgresql.address}:${aws_db_instance.postgresql.port}/${var.db_name}"
  sensitive   = false
}

# Datadog Monitoring outputs
output "datadog_operator_install_script" {
  description = "Path to the Datadog Operator installation script"
  value       = local_file.datadog_operator_install_script.filename
}

output "datadog_agent_manifest" {
  description = "Path to the Datadog Agent manifest"
  value       = local_file.datadog_agent_manifest.filename
}

output "datadog_site" {
  description = "Datadog site URL for monitoring"
  value       = data.vault_kv_secret_v2.datadog.data["datadog_site"]
  sensitive   = true
}

output "datadog_cluster_name" {
  description = "Cluster name configured in Datadog"
  value       = module.eks.cluster_name
}

