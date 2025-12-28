# Backend configuration for Terraform state storage
# 
# NOTE: This project uses HCP Terraform Cloud for state management.
# The `cloud` block in main.tf configures the TFC backend.
# 
# The azurerm backend below is kept for reference but is NOT USED.
# To use local/Azure backend instead of TFC, remove the `cloud` block 
# from main.tf and uncomment the backend block below.

# terraform {
#   backend "azurerm" {
#     # These values are provided via -backend-config flags in terraform init
#     # resource_group_name  = "qnt9-terraform-state-rg"
#     # storage_account_name = "qnt9tfstate..."
#     # container_name       = "tfstate"
#     # key                  = "dev.tfstate" or "dev-runX.tfstate" for ephemeral
#   }
# }

# For local development with TFC, run:
#   export TF_WORKSPACE=qnt9-srs-dev
#   terraform login
#   terraform init
#   terraform plan
#
# For local development with Azure backend (alternative):
# 1. Remove the `cloud` block from main.tf
# 2. Uncomment the backend "azurerm" block above
# 3. Create a backend_override.tf file:
#    terraform {
#      backend "azurerm" {
#        resource_group_name  = "qnt9-terraform-state-rg"
#        storage_account_name = "qnt9tfstateXXXXXXXX"
#        container_name       = "tfstate"
#        key                  = "dev-local.tfstate"
#      }
#    }

