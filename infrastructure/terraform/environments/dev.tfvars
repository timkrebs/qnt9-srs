# Development Environment Configuration
# QNT9-SRS Terraform Variables

# Core Azure Configuration
location    = "germanywestcentral"
environment = "dev"

# Business Information
cost_center          = "QNT9-DEV"
owner_email          = "dev-team@qnt9.io"
business_owner_email = "product@qnt9.io"
budget_code          = "DEV-2024"

# Technical Configuration
data_classification = "Internal"
criticality         = "Low"

# Compliance
compliance_requirements = "GDPR"
data_residency          = "Germany"

# AKS Configuration - Development (smaller footprint)
aks_node_count         = 2
aks_vm_size            = "Standard_B2s"
aks_kubernetes_version = "1.34.1"
