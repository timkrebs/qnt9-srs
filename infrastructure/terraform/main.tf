# Main Terraform configuration for QNT9 SRS Azure Infrastructure
# This file orchestrates all infrastructure components

terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    vault = {
      source  = "hashicorp/vault"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Cloud block is configured via CLI or environment variables
  # The organization and workspace are set in the HCP Terraform workspace settings
  # and passed via the GitHub Actions workflow
}

# Local variables for resource naming and tagging
locals {
  project_name = "qnt9-srs"

  # Generate unique suffix for globally unique resources
  unique_suffix = substr(md5("${var.environment}-${var.location}"), 0, 6)

  # Resource naming convention: projectname-resourcetype-environment-region
  resource_prefix = "${local.project_name}-${var.environment}"

  # Common tags applied to all resources
  common_tags = {
    Project            = "QNT9-SRS"
    Environment        = var.environment
    ManagedBy          = "Terraform"
    CostCenter         = var.cost_center
    Owner              = var.owner_email
    BusinessOwner      = var.business_owner_email
    DataClassification = var.data_classification
    Criticality        = var.criticality
    BudgetCode         = var.budget_code
    Compliance         = var.compliance_requirements
    DataResidency      = var.data_residency
    LastModified       = timestamp()
  }
}

# Resource Group - Central container for all Azure resources
resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

# Storage Account for Terraform state and blob storage
resource "azurerm_storage_account" "main" {
  name                     = "qnt9srs${var.environment}${local.unique_suffix}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  # Security settings
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = merge(local.common_tags, {
    Purpose = "Blob Storage and Terraform State"
  })
}

# Storage Container for reports
resource "azurerm_storage_container" "reports" {
  name                  = "reports"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Storage Container for Terraform state
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# AKS Cluster module
module "aks" {
  source = "./modules/aks"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  resource_prefix     = local.resource_prefix

  node_count         = var.aks_node_count
  vm_size            = var.aks_vm_size
  kubernetes_version = var.aks_kubernetes_version

  tags = local.common_tags
}

# Azure Container Registry module
module "acr" {
  source = "./modules/acr"

  acr_name            = "acr${replace(local.project_name, "-", "")}${var.environment}${local.unique_suffix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  # Use Basic SKU for dev, Standard for staging/prod
  sku = var.environment == "dev" ? "Basic" : "Standard"

  # Enable admin for GitHub Actions authentication
  admin_enabled = true

  # Allow AKS to pull images
  aks_principal_id = module.aks.kubelet_identity_object_id

  tags = merge(local.common_tags, {
    Purpose = "Container Registry for Microservices"
  })
}

# Icinga monitoring VM
resource "azurerm_linux_virtual_machine" "icinga" {
  name                = "${local.resource_prefix}-icinga-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.icinga_vm_size
  admin_username      = var.icinga_admin_username

  network_interface_ids = [
    azurerm_network_interface.icinga.id,
  ]

  admin_ssh_key {
    username   = var.icinga_admin_username
    public_key = var.icinga_ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = var.environment == "dev" ? "Standard_LRS" : "Premium_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  tags = merge(local.common_tags, {
    Purpose = "Icinga Monitoring Server"
  })
}

# Network Interface for Icinga VM
resource "azurerm_network_interface" "icinga" {
  name                = "${local.resource_prefix}-icinga-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.icinga.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.icinga.id
  }

  tags = local.common_tags
}

# Public IP for Icinga VM
resource "azurerm_public_ip" "icinga" {
  name                = "${local.resource_prefix}-icinga-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = merge(local.common_tags, {
    Purpose = "Icinga Web Access"
  })
}

# Virtual Network for Icinga
resource "azurerm_virtual_network" "icinga" {
  name                = "${local.resource_prefix}-icinga-vnet"
  address_space       = ["10.1.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Subnet for Icinga
resource "azurerm_subnet" "icinga" {
  name                 = "${local.resource_prefix}-icinga-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.icinga.name
  address_prefixes     = ["10.1.1.0/24"]
}

# Network Security Group for Icinga
resource "azurerm_network_security_group" "icinga" {
  name                = "${local.resource_prefix}-icinga-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # SSH access
  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.icinga_allowed_ip_range
    destination_address_prefix = "*"
  }

  # HTTPS for Icinga Web
  security_rule {
    name                       = "HTTPS"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = var.icinga_allowed_ip_range
    destination_address_prefix = "*"
  }

  # HTTP for Icinga Web (redirect to HTTPS)
  security_rule {
    name                       = "HTTP"
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = var.icinga_allowed_ip_range
    destination_address_prefix = "*"
  }

  # Icinga API
  security_rule {
    name                       = "IcingaAPI"
    priority                   = 1004
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5665"
    source_address_prefix      = var.icinga_allowed_ip_range
    destination_address_prefix = "*"
  }

  tags = local.common_tags
}

# Associate NSG with NIC
resource "azurerm_network_interface_security_group_association" "icinga" {
  network_interface_id      = azurerm_network_interface.icinga.id
  network_security_group_id = azurerm_network_security_group.icinga.id
}

# Function App module
module "function_app" {
  source = "./modules/function-app"

  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  resource_prefix      = local.resource_prefix
  storage_account_name = azurerm_storage_account.main.name
  storage_account_key  = azurerm_storage_account.main.primary_access_key

  tags = local.common_tags
}
