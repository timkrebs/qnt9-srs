# Backend configuration for Terraform state storage
# State is stored in HCP Terraform (Terraform Cloud) for secure remote backend

#terraform {
#  backend "remote" {
#    organization = "qnt9"
#    
#    workspaces {
#      prefix = "qnt9-srs-"
#    }
#  }
#}

# Alternative: Azure Blob Storage backend (uncomment if not using HCP Terraform)
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "qnt9-srs-tfstate-rg"
#     storage_account_name = "qnt9srstfstate"
#     container_name       = "tfstate"
#     key                  = "terraform.tfstate"
#   }
# }
