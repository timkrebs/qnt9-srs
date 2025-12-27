# Staging Environment Configuration
# QNT9-SRS Terraform Variables

# Core Azure Configuration
location    = "germanywestcentral"
environment = "staging"

# Business Information
cost_center          = "QNT9-STAGING"
owner_email          = "dev-team@qnt9.io"
business_owner_email = "product@qnt9.io"
budget_code          = "STG-2024"

# Technical Configuration
data_classification = "Confidential"
criticality         = "Medium"

# Compliance
compliance_requirements = "GDPR,SOC2"
data_residency          = "Germany"

# AKS Configuration - Staging (production-like)
aks_node_count         = 3
aks_vm_size            = "Standard_D2s_v3"
aks_kubernetes_version = "1.31.11"

# HCP Vault Configuration
enable_vault_integration = true
vault_namespace          = "admin"

# Icinga Monitoring Configuration
icinga_vm_size          = "Standard_B2ms"
icinga_admin_username   = "icingaadmin"
icinga_allowed_ip_range = "10.0.0.0/8"

# Function App Configuration (if applicable)
# function_app_sku = "EP1"
