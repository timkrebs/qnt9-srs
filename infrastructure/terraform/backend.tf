# Backend configuration for Terraform state storage
# State is stored in HCP Terraform (Terraform Cloud) for secure remote backend

# The cloud block is configured in main.tf or via CLI:
# - Organization and workspace are set via TF_CLOUD_ORGANIZATION and TF_WORKSPACE env vars
# - Or configured in HCP Terraform workspace settings
# - The GitHub Actions workflow handles this configuration automatically

# For local development, you can create a backend_override.tf file:
# terraform {
#   cloud {
#     organization = "qnt9"
#     workspaces {
#       name = "qnt9-srs-dev-main"
#     }
#   }
# }

# Alternative: Azure Blob Storage backend (currently not used)
# Uncomment if migrating from HCP Terraform to Azure backend
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "qnt9-srs-tfstate-rg"
#     storage_account_name = "qnt9srstfstate"
#     container_name       = "tfstate"
#     key                  = "terraform.tfstate"
#   }
# }
