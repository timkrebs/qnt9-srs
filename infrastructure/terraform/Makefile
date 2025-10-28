# Makefile for Terraform Infrastructure Management.PHONY: help init plan apply destroy validate fmt clean aks-creds acr-login

# Simplifies common Terraform operations

help: ## Show this help message

.PHONY: help init plan apply destroy validate format clean cost-estimate	@echo 'Usage: make [target]'

	@echo ''

# Environment variable (default: dev)	@echo 'Available targets:'

ENV ?= dev	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)



# Colors for outputinit: ## Initialize Terraform

GREEN  := \033[0;32m	terraform init

YELLOW := \033[0;33m

RED    := \033[0;31mvalidate: ## Validate Terraform configuration

NC     := \033[0m	terraform validate



help:fmt: ## Format Terraform files

	@echo "$(GREEN)QNT9 SRS - Terraform Infrastructure Management$(NC)"	terraform fmt -recursive

	@echo ""

	@echo "$(YELLOW)Available commands:$(NC)"plan: ## Plan Terraform changes

	@echo "  make init ENV=<env>           - Initialize Terraform (default: dev)"	terraform plan -out=tfplan

	@echo "  make plan ENV=<env>           - Show execution plan"

	@echo "  make apply ENV=<env>          - Apply infrastructure changes"apply: ## Apply Terraform changes

	@echo "  make destroy ENV=<env>        - Destroy infrastructure"	terraform apply tfplan

	@echo "  make validate                 - Validate Terraform configuration"

	@echo "  make format                   - Format Terraform files"destroy: ## Destroy all resources

	@echo "  make clean                    - Clean Terraform cache"	terraform destroy

	@echo "  make cost-estimate ENV=<env>  - Estimate infrastructure costs"

	@echo "  make output ENV=<env>         - Show Terraform outputs"aks-creds: ## Get AKS credentials for kubectl

	@echo "  make configure-kubectl        - Configure kubectl for AKS"	@CLUSTER_NAME=$$(terraform output -raw cluster_name 2>/dev/null || echo ""); \

	@echo ""	RG_NAME=$$(terraform output -raw resource_group_name 2>/dev/null || echo ""); \

	@echo "$(YELLOW)Environment options:$(NC) dev, staging, prd"	if [ -z "$$CLUSTER_NAME" ] || [ -z "$$RG_NAME" ]; then \

	@echo ""		echo "Error: Terraform outputs not available. Run 'make apply' first."; \

	@echo "$(YELLOW)Example:$(NC) make apply ENV=dev"		exit 1; \

	fi; \

init:	az aks get-credentials --name $$CLUSTER_NAME --resource-group $$RG_NAME --overwrite-existing

	@echo "$(GREEN)Initializing Terraform for $(ENV) environment...$(NC)"

	terraform init -upgradeacr-login: ## Login to Azure Container Registry

	@ACR_NAME=$$(terraform output -raw acr_name 2>/dev/null || echo ""); \

validate:	if [ -z "$$ACR_NAME" ]; then \

	@echo "$(GREEN)Validating Terraform configuration...$(NC)"		echo "Error: ACR name not available. Run 'make apply' first."; \

	terraform validate		exit 1; \

	terraform fmt -check -recursive	fi; \

	az acr login --name $$ACR_NAME

format:

	@echo "$(GREEN)Formatting Terraform files...$(NC)"test-db: ## Test database connection

	terraform fmt -recursive	@echo "Testing PostgreSQL connection..."

	@DB_FQDN=$$(terraform output -raw db_server_fqdn 2>/dev/null || echo ""); \

plan:	DB_NAME=$$(terraform output -raw db_database_name 2>/dev/null || echo ""); \

	@echo "$(GREEN)Creating execution plan for $(ENV) environment...$(NC)"	if [ -z "$$DB_FQDN" ] || [ -z "$$DB_NAME" ]; then \

	terraform plan -var-file="environments/$(ENV).tfvars" -out=tfplan-$(ENV)		echo "Error: Database outputs not available."; \

		exit 1; \

apply:	fi; \

	@echo "$(GREEN)Applying infrastructure for $(ENV) environment...$(NC)"	echo "Database FQDN: $$DB_FQDN"; \

	@echo "$(YELLOW)This will create/update resources in Azure$(NC)"	echo "Database Name: $$DB_NAME"; \

	@read -p "Continue? [y/N] " -n 1 -r; \	echo "Note: Password is stored in Vault at kv/azure/postgresql"

	echo; \

	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \clean: ## Clean Terraform files

		terraform apply -var-file="environments/$(ENV).tfvars" -auto-approve; \	rm -rf .terraform

	else \	rm -f .terraform.lock.hcl

		echo "$(RED)Aborted$(NC)"; \	rm -f tfplan

	fi	rm -f terraform.tfstate*

	rm -f datadog-agent-generated.yaml

destroy:

	@echo "$(RED)Destroying infrastructure for $(ENV) environment...$(NC)"cost-estimate: ## Estimate monthly costs (requires infracost)

	@echo "$(RED)WARNING: This will DELETE all resources!$(NC)"	@if command -v infracost >/dev/null 2>&1; then \

	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \		infracost breakdown --path .; \

	if [ "$$confirm" = "yes" ]; then \	else \

		terraform destroy -var-file="environments/$(ENV).tfvars" -auto-approve; \		echo "infracost not installed. Install from https://www.infracost.io/"; \

	else \	fi

		echo "$(YELLOW)Aborted$(NC)"; \

	fisetup-vault: ## Setup Vault configuration (requires vault CLI)

	@echo "Configuring Vault..."

output:	@cd ../scripts && ./setup-vault-env.sh

	@echo "$(GREEN)Terraform outputs for $(ENV) environment:$(NC)"
	terraform outputall: init validate fmt plan apply ## Run init, validate, fmt, plan, and apply



clean:.DEFAULT_GOAL := help

	@echo "$(YELLOW)Cleaning Terraform cache...$(NC)"
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f tfplan-*
	rm -f terraform.tfstate*

cost-estimate:
	@echo "$(GREEN)Estimating infrastructure costs for $(ENV)...$(NC)"
	@echo "$(YELLOW)Note: Requires infracost CLI. Install: brew install infracost$(NC)"
	@if command -v infracost > /dev/null; then \
		infracost breakdown --path . --terraform-var-file environments/$(ENV).tfvars; \
	else \
		echo "$(RED)infracost not installed. Install with: brew install infracost$(NC)"; \
	fi

configure-kubectl:
	@echo "$(GREEN)Configuring kubectl for AKS cluster...$(NC)"
	@RESOURCE_GROUP=$$(terraform output -raw resource_group_name 2>/dev/null); \
	AKS_NAME=$$(terraform output -raw aks_cluster_name 2>/dev/null); \
	if [ -n "$$RESOURCE_GROUP" ] && [ -n "$$AKS_NAME" ]; then \
		az aks get-credentials --resource-group $$RESOURCE_GROUP --name $$AKS_NAME --overwrite-existing; \
		echo "$(GREEN)kubectl configured successfully$(NC)"; \
	else \
		echo "$(RED)Error: Could not retrieve AKS cluster information$(NC)"; \
	fi

# Development workflow shortcuts
dev-init:
	@$(MAKE) init ENV=dev

dev-plan:
	@$(MAKE) plan ENV=dev

dev-apply:
	@$(MAKE) apply ENV=dev

dev-destroy:
	@$(MAKE) destroy ENV=dev

# Production workflow (requires explicit confirmation)
prd-plan:
	@$(MAKE) plan ENV=prd

prd-apply:
	@echo "$(RED)WARNING: This will modify PRODUCTION infrastructure$(NC)"
	@$(MAKE) apply ENV=prd
