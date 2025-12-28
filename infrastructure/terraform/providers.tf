# Provider configuration for Azure

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "random" {
  # Random provider for generating unique identifiers
}
