# Copyright (c) HashiCorp, Inc.
# SPDX-License-Identifier: MPL-2.0

# Random suffix for unique naming
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  cluster_name = "qnt9-srs-aks-${random_string.suffix.result}"
  resource_group_name = "rg-srs-${var.environment}-${random_string.suffix.result}"

  common_tags = {
    CostCenter         = var.cost_center
    BusinessUnit       = "Investment-Tech"
    Project            = "Stock-Recommendation"
    Owner              = var.owner_email
    BusinessOwner      = var.business_owner_email
    Environment        = var.environment
    Application        = "SRS-Platform"
    ManagedBy          = "Terraform"
    TerraformWorkspace = terraform.workspace
    DataClassification = var.data_classification
    Criticality        = var.criticality
    ChargebackCode     = "${upper(var.environment)}-SRS-2024"
    BudgetCode         = var.budget_code
    ComplianceGDPR     = contains(split(",", var.compliance_requirements), "GDPR") ? "true" : "false"
    ComplianceSOC2     = contains(split(",", var.compliance_requirements), "SOC2") ? "true" : "false"
    DataResidency      = var.data_residency
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "vnet-srs-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  address_space       = ["10.0.0.0/16"]
  
  tags = local.common_tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "snet-aks"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Subnet for PostgreSQL
resource "azurerm_subnet" "postgresql" {
  name                 = "snet-postgresql"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]
  
  service_endpoints = ["Microsoft.Storage"]
  
  delegation {
    name = "postgresql-delegation"
    
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "postgresql" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name
  tags                = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgresql" {
  name                  = "postgresql-vnet-link"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.postgresql.name
  virtual_network_id    = azurerm_virtual_network.main.id
  tags                  = local.common_tags
}

# Azure Kubernetes Service (AKS)
resource "azurerm_kubernetes_cluster" "main" {
  name                = local.cluster_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "srs-${var.environment}"
  kubernetes_version  = var.aks_kubernetes_version

  default_node_pool {
    name            = "default"
    vm_size         = var.aks_vm_size
    vnet_subnet_id  = azurerm_subnet.aks.id
    min_count       = 1
    max_count       = 5
    os_disk_size_gb = 30
    
    tags = local.common_tags
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.1.0.0/16"
    dns_service_ip    = "10.1.0.10"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  azure_policy_enabled = true

  tags = local.common_tags
}

# Log Analytics Workspace for AKS monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-srs-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  
  tags = local.common_tags
}

# Random password for PostgreSQL
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Azure Database for PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "psql-srs-${var.environment}-${random_string.suffix.result}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = var.db_version
  delegated_subnet_id    = azurerm_subnet.postgresql.id
  private_dns_zone_id    = azurerm_private_dns_zone.postgresql.id
  administrator_login    = var.db_username
  administrator_password = random_password.db_password.result
  zone                   = "1"

  storage_mb = var.db_storage_mb
  sku_name   = var.db_sku_name

  backup_retention_days        = var.environment == "prd" ? 7 : 7
  geo_redundant_backup_enabled = var.environment == "prd" ? true : false

  high_availability {
    mode = var.environment == "prd" ? "ZoneRedundant" : "Disabled"
  }

  maintenance_window {
    day_of_week  = 0
    start_hour   = 3
    start_minute = 0
  }

  tags = local.common_tags

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgresql]
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# PostgreSQL Firewall Rules - Allow Azure Services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# PostgreSQL Firewall Rules - Allow HCP Vault (adjust IP ranges as needed)
resource "azurerm_postgresql_flexible_server_firewall_rule" "vault" {
  name             = "AllowHCPVault"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0" # TODO: Restrict to HCP Vault IPs
  end_ip_address   = "255.255.255.255"
}

# PostgreSQL Configuration
resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "uuid-ossp,pgcrypto"
}
