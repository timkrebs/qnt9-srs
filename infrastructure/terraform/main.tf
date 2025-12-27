# Main Terraform configuration for QNT9 SRS Azure Infrastructure
# This file orchestrates all infrastructure components
#
# HCP Terraform Cloud Integration:
# ================================
# When running locally with Terraform Cloud, the workspace is selected via
# TF_WORKSPACE environment variable. The cloud block omits workspace configuration
# to allow dynamic workspace selection.
#
# For local development:
#   export TF_WORKSPACE=qnt9-srs-dev
#   terraform login
#   terraform init
#   terraform plan -var-file=environments/dev.tfvars
#
# For CI/CD (ephemeral):
#   export TF_WORKSPACE=qnt9-srs-dev-pr123
#   terraform init
#   terraform apply -var-file=environments/dev.tfvars -var="ephemeral=true" -var="run_id=pr123"

terraform {
  # Cloud block for HCP Terraform Cloud integration
  # Workspace is selected dynamically via TF_WORKSPACE environment variable
  # The CI/CD pipeline creates workspaces via API before running terraform
  cloud {
    organization = "tim-krebs-org"
    # No workspace block - workspace is selected via TF_WORKSPACE env var
  }

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
}

# Local variables for resource naming and tagging
locals {
  project_name = "qnt9-srs"

  # Generate unique suffix for globally unique resources
  unique_suffix = substr(md5("${var.environment}-${var.location}"), 0, 6)

  # Ephemeral suffix for CI/CD runs (e.g., pr-123 or run-456789)
  ephemeral_suffix = var.ephemeral && var.run_id != "" ? "-${var.run_id}" : ""

  # Resource naming convention: projectname-resourcetype-environment-region[-runid]
  resource_prefix = var.ephemeral ? "${local.project_name}-${var.environment}${local.ephemeral_suffix}" : "${local.project_name}-${var.environment}"

  # Compute actual AKS configuration based on ephemeral mode
  actual_aks_node_count = var.ephemeral ? var.aks_ephemeral_node_count : var.aks_node_count
  actual_aks_vm_size    = var.ephemeral ? var.aks_ephemeral_vm_size : var.aks_vm_size

  # ACR name must be alphanumeric only, 5-50 characters
  acr_name = var.ephemeral ? "acr${replace(local.project_name, "-", "")}${var.environment}${replace(var.run_id, "-", "")}" : "acr${replace(local.project_name, "-", "")}${var.environment}${local.unique_suffix}"

  # Common tags applied to all resources
  common_tags = {
    Project            = "QNT9-SRS"
    Environment        = var.environment
    ManagedBy          = "Terraform"
    Ephemeral          = tostring(var.ephemeral)
    RunID              = var.run_id
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

  node_count         = local.actual_aks_node_count
  vm_size            = local.actual_aks_vm_size
  kubernetes_version = var.aks_kubernetes_version

  tags = local.common_tags
}

# Azure Container Registry module
module "acr" {
  source = "./modules/acr"

  acr_name            = local.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  # Use Basic SKU for dev and ephemeral, Standard for staging/prod
  sku = var.ephemeral || var.environment == "dev" ? "Basic" : "Standard"

  # Enable admin for GitHub Actions authentication
  admin_enabled = true

  # Allow AKS to pull images
  aks_principal_id = module.aks.kubelet_identity_object_id

  tags = merge(local.common_tags, {
    Purpose = "Container Registry for Microservices"
  })
}

# Icinga monitoring VM (disabled for ephemeral deployments)
resource "azurerm_linux_virtual_machine" "icinga" {
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

  name                = "${local.resource_prefix}-icinga-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.icinga_vm_size
  admin_username      = var.icinga_admin_username

  network_interface_ids = [
    azurerm_network_interface.icinga[0].id,
  ]

  admin_ssh_key {
    username   = var.icinga_admin_username
    public_key = var.icinga_ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = var.environment == "dev" ? "Standard_LRS" : "Premium_LRS"
    disk_size_gb         = 64 # Increased from default 30GB for logs and monitoring data
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  # Cloud-init configuration for automated Icinga installation
  custom_data = base64encode(file("${path.module}/scripts/cloud-init-icinga.yaml"))

  tags = merge(local.common_tags, {
    Purpose = "Icinga Monitoring Server"
  })
}

# Network Interface for Icinga VM
resource "azurerm_network_interface" "icinga" {
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

  name                = "${local.resource_prefix}-icinga-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.icinga[0].id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.icinga[0].id
  }

  tags = local.common_tags
}

# Public IP for Icinga VM
resource "azurerm_public_ip" "icinga" {
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

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
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

  name                = "${local.resource_prefix}-icinga-vnet"
  address_space       = ["10.1.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = local.common_tags
}

# Subnet for Icinga
resource "azurerm_subnet" "icinga" {
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

  name                 = "${local.resource_prefix}-icinga-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.icinga[0].name
  address_prefixes     = ["10.1.1.0/24"]
}

# Network Security Group for Icinga
resource "azurerm_network_security_group" "icinga" {
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

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
  count = var.enable_icinga && !var.ephemeral ? 1 : 0

  network_interface_id      = azurerm_network_interface.icinga[0].id
  network_security_group_id = azurerm_network_security_group.icinga[0].id
}

# Function App module (disabled for ephemeral deployments)
module "function_app" {
  count  = var.enable_function_app && !var.ephemeral ? 1 : 0
  source = "./modules/function-app"

  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  resource_prefix      = local.resource_prefix
  storage_account_name = azurerm_storage_account.main.name
  storage_account_key  = azurerm_storage_account.main.primary_access_key

  tags = local.common_tags
}
