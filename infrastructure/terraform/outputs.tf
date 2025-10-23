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

