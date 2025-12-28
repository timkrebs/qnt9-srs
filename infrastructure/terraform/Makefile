# Makefile for QNT9-SRS Terraform Infrastructure Management
# Supports local development and CI/CD integration with HCP Terraform Cloud

.PHONY: help init plan apply destroy validate fmt clean aks-creds acr-login test-local

# Environment configuration (default: dev)
ENV ?= dev
TF_WORKSPACE ?= qnt9-srs-$(ENV)

# Colors for output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m

help: ## Show this help message
	@echo "$(GREEN)QNT9-SRS Terraform Infrastructure Management$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make init ENV=dev            # Initialize for dev environment"
	@echo "  make plan ENV=staging        # Plan for staging environment"
	@echo "  make apply ENV=prd           # Apply to production"
	@echo "  make test-local              # Run local validation"

# =============================================================================
# Terraform Operations
# =============================================================================

init: ## Initialize Terraform with HCP Terraform Cloud backend
	@echo "$(GREEN)Initializing Terraform for $(ENV) environment...$(NC)"
	@export TF_WORKSPACE=$(TF_WORKSPACE) && \
	terraform init

validate: ## Validate Terraform configuration
	@echo "$(GREEN)Validating Terraform configuration...$(NC)"
	terraform validate

fmt: ## Format Terraform files
	@echo "$(GREEN)Formatting Terraform files...$(NC)"
	terraform fmt -recursive

fmt-check: ## Check Terraform formatting
	@echo "$(GREEN)Checking Terraform formatting...$(NC)"
	terraform fmt -check -recursive -diff

plan: ## Plan Terraform changes
	@echo "$(GREEN)Planning Terraform changes for $(ENV)...$(NC)"
	@export TF_WORKSPACE=$(TF_WORKSPACE) && \
	terraform plan \
		-var-file=environments/$(ENV).tfvars \
		-out=tfplan.$(ENV)

apply: ## Apply Terraform changes
	@echo "$(GREEN)Applying Terraform changes for $(ENV)...$(NC)"
	@if [ ! -f tfplan.$(ENV) ]; then \
		echo "$(RED)Error: No plan file found. Run 'make plan ENV=$(ENV)' first.$(NC)"; \
		exit 1; \
	fi
	@export TF_WORKSPACE=$(TF_WORKSPACE) && \
	terraform apply tfplan.$(ENV)

destroy: ## Destroy infrastructure
	@echo "$(RED)Destroying infrastructure for $(ENV)...$(NC)"
	@export TF_WORKSPACE=$(TF_WORKSPACE) && \
	terraform destroy -var-file=environments/$(ENV).tfvars

output: ## Show Terraform outputs
	@echo "$(GREEN)Terraform outputs for $(ENV):$(NC)"
	@export TF_WORKSPACE=$(TF_WORKSPACE) && \
	terraform output

# =============================================================================
# Local Testing & Validation
# =============================================================================

test-local: fmt-check validate ## Run local validation suite
	@echo "$(GREEN)Running local validation suite...$(NC)"
	@echo ""
	@echo "1. Checking format..."
	@terraform fmt -check -recursive || (echo "$(RED)Format check failed$(NC)" && exit 1)
	@echo "$(GREEN)Format OK$(NC)"
	@echo ""
	@echo "2. Validating configuration..."
	@terraform validate || (echo "$(RED)Validation failed$(NC)" && exit 1)
	@echo "$(GREEN)Validation OK$(NC)"
	@echo ""
	@echo "$(GREEN)All local tests passed!$(NC)"

security-scan: ## Run security scan with tfsec
	@echo "$(GREEN)Running security scan...$(NC)"
	tfsec .

# =============================================================================
# Kubernetes Operations
# =============================================================================

aks-creds: ## Get AKS credentials for kubectl
	@echo "$(GREEN)Getting AKS credentials...$(NC)"
	@CLUSTER_NAME=$$(terraform output -raw aks_cluster_name 2>/dev/null) && \
	RG_NAME=$$(terraform output -raw resource_group_name 2>/dev/null) && \
	az aks get-credentials --resource-group "$$RG_NAME" --name "$$CLUSTER_NAME" --overwrite-existing

acr-login: ## Login to Azure Container Registry
	@echo "$(GREEN)Logging into ACR...$(NC)"
	@ACR_NAME=$$(terraform output -raw acr_name 2>/dev/null) && \
	az acr login --name "$$ACR_NAME"

# =============================================================================
# Utility Operations
# =============================================================================

clean: ## Clean Terraform cache and temporary files
	@echo "$(GREEN)Cleaning Terraform cache...$(NC)"
	rm -rf .terraform
	rm -rf .terraform.lock.hcl
	rm -f tfplan.*
	rm -f backend_override.tf
	rm -f cicd.auto.tfvars
	rm -f *.backup
	@echo "$(GREEN)Clean complete$(NC)"

show-config: ## Show current configuration
	@echo "$(GREEN)Current Configuration:$(NC)"
	@echo "  Environment: $(ENV)"
	@echo "  Workspace:   $(TF_WORKSPACE)"
