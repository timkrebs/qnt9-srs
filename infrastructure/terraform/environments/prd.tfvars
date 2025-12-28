# Production Environment Configuration
# QNT9-SRS Terraform Variables

# Core Azure Configuration
location    = "germanywestcentral"
environment = "prd"

# Business Information
cost_center          = "QNT9-PROD"
owner_email          = "sre-team@qnt9.io"
business_owner_email = "product@qnt9.io"
budget_code          = "PRD-2024"

# Technical Configuration
data_classification = "Confidential"
criticality         = "Critical"

# Compliance
compliance_requirements = "GDPR,SOC2,ISO27001"
data_residency          = "Germany"

# AKS Configuration - Production (high availability)
aks_node_count         = 5
aks_vm_size            = "Standard_D4s_v3"
aks_kubernetes_version = "1.31.11"
