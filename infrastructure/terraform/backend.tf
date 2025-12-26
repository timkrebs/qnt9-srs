# Backend configuration for Terraform state storage
# State is stored in Azure Blob Storage for secure remote backend

terraform {
  backend "azurerm" {
    # These values are provided via -backend-config flags in terraform init
    # resource_group_name  = "qnt9-terraform-state-rg"
    # storage_account_name = "qnt9tfstate..."
    # container_name       = "tfstate"
    # key                  = "dev.tfstate" or "dev-runX.tfstate" for ephemeral
  }
}

# For local development, you can create a backend_override.tf file:
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "qnt9-terraform-state-rg"
#     storage_account_name = "qnt9tfstateXXXXXXXX"
#     container_name       = "tfstate"
#     key                  = "dev-local.tfstate"
#   }
# }
