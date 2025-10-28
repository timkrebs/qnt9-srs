# PostgreSQL Flexible Server Module
# Provides a managed PostgreSQL database instance

resource "azurerm_postgresql_flexible_server" "main" {
  name                = "${var.resource_prefix}-psql"
  resource_group_name = var.resource_group_name
  location            = var.location

  administrator_login    = var.db_username
  administrator_password = var.db_password

  sku_name   = var.db_sku_name
  version    = var.db_version
  storage_mb = var.db_storage_mb

  # High availability configuration (disabled for cost savings in dev)
  # high_availability {
  #   mode = "ZoneRedundant"
  # }

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  tags = var.tags

  # Ignore zone changes to prevent errors on existing resources
  lifecycle {
    ignore_changes = [
      zone
    ]
  }
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Firewall rule to allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Configuration parameters
resource "azurerm_postgresql_flexible_server_configuration" "max_connections" {
  name      = "max_connections"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "100"
}

resource "azurerm_postgresql_flexible_server_configuration" "shared_buffers" {
  name      = "shared_buffers"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "32768"
}
