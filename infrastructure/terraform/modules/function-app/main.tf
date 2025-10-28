# Azure Function App Module
# Provides serverless compute for scheduled jobs and background processing

# App Service Plan for Function App
resource "azurerm_service_plan" "main" {
  name                = "${var.resource_prefix}-asp"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "Y1"

  tags = var.tags
}

# Linux Function App
resource "azurerm_linux_function_app" "main" {
  name                = "${var.resource_prefix}-func"
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.main.id

  storage_account_name       = var.storage_account_name
  storage_account_access_key = var.storage_account_key

  site_config {
    application_stack {
      python_version = "3.11"
    }

    application_insights_key               = var.app_insights_key
    application_insights_connection_string = var.app_insights_key
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"        = "python"
    "PYTHON_ENABLE_WORKER_EXTENSIONS" = "1"
    "ENABLE_ORYX_BUILD"               = "true"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"  = "true"
  }

  tags = var.tags
}
