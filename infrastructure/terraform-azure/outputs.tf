# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

# Resource Group
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_location" {
  description = "Location of the resource group"
  value       = azurerm_resource_group.main.location
}

# AKS Cluster
output "cluster_name" {
  description = "AKS Cluster Name"
  value       = azurerm_kubernetes_cluster.main.name
}

output "cluster_endpoint" {
  description = "Endpoint for AKS control plane"
  value       = azurerm_kubernetes_cluster.main.kube_config[0].host
}

output "cluster_id" {
  description = "AKS Cluster ID"
  value       = azurerm_kubernetes_cluster.main.id
}

output "kube_config" {
  description = "Kubernetes config for AKS cluster"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

# Database outputs
output "db_server_fqdn" {
  description = "The fully qualified domain name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "db_server_name" {
  description = "The name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.name
}

output "db_database_name" {
  description = "The database name"
  value       = azurerm_postgresql_flexible_server_database.main.name
}

output "db_connection_string" {
  description = "PostgreSQL connection string for FastAPI (without password)"
  value       = "postgresql://${var.db_username}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${var.db_name}?sslmode=require"
  sensitive   = false
}

# Networking
output "vnet_id" {
  description = "Virtual Network ID"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Virtual Network Name"
  value       = azurerm_virtual_network.main.name
}

output "aks_subnet_id" {
  description = "AKS Subnet ID"
  value       = azurerm_subnet.aks.id
}

output "postgresql_subnet_id" {
  description = "PostgreSQL Subnet ID"
  value       = azurerm_subnet.postgresql.id
}

# Log Analytics
output "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID"
  value       = azurerm_log_analytics_workspace.main.id
}

# Commands to connect
output "aks_get_credentials_command" {
  description = "Command to configure kubectl"
  value       = "az aks get-credentials --name ${azurerm_kubernetes_cluster.main.name} --resource-group ${azurerm_resource_group.main.name}"
}

output "acr_login_command" {
  description = "Command to login to ACR"
  value       = "az acr login --name ${azurerm_container_registry.main.name}"
}
