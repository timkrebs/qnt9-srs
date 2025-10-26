.PHONY: help init plan apply destroy validate fmt clean aks-creds acr-login

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

init: ## Initialize Terraform
	terraform init

validate: ## Validate Terraform configuration
	terraform validate

fmt: ## Format Terraform files
	terraform fmt -recursive

plan: ## Plan Terraform changes
	terraform plan -out=tfplan

apply: ## Apply Terraform changes
	terraform apply tfplan

destroy: ## Destroy all resources
	terraform destroy

aks-creds: ## Get AKS credentials for kubectl
	@CLUSTER_NAME=$$(terraform output -raw cluster_name 2>/dev/null || echo ""); \
	RG_NAME=$$(terraform output -raw resource_group_name 2>/dev/null || echo ""); \
	if [ -z "$$CLUSTER_NAME" ] || [ -z "$$RG_NAME" ]; then \
		echo "Error: Terraform outputs not available. Run 'make apply' first."; \
		exit 1; \
	fi; \
	az aks get-credentials --name $$CLUSTER_NAME --resource-group $$RG_NAME --overwrite-existing

acr-login: ## Login to Azure Container Registry
	@ACR_NAME=$$(terraform output -raw acr_name 2>/dev/null || echo ""); \
	if [ -z "$$ACR_NAME" ]; then \
		echo "Error: ACR name not available. Run 'make apply' first."; \
		exit 1; \
	fi; \
	az acr login --name $$ACR_NAME

test-db: ## Test database connection
	@echo "Testing PostgreSQL connection..."
	@DB_FQDN=$$(terraform output -raw db_server_fqdn 2>/dev/null || echo ""); \
	DB_NAME=$$(terraform output -raw db_database_name 2>/dev/null || echo ""); \
	if [ -z "$$DB_FQDN" ] || [ -z "$$DB_NAME" ]; then \
		echo "Error: Database outputs not available."; \
		exit 1; \
	fi; \
	echo "Database FQDN: $$DB_FQDN"; \
	echo "Database Name: $$DB_NAME"; \
	echo "Note: Password is stored in Vault at kv/azure/postgresql"

clean: ## Clean Terraform files
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f tfplan
	rm -f terraform.tfstate*
	rm -f datadog-agent-generated.yaml

cost-estimate: ## Estimate monthly costs (requires infracost)
	@if command -v infracost >/dev/null 2>&1; then \
		infracost breakdown --path .; \
	else \
		echo "infracost not installed. Install from https://www.infracost.io/"; \
	fi

setup-vault: ## Setup Vault configuration (requires vault CLI)
	@echo "Configuring Vault..."
	@cd ../scripts && ./setup-vault-env.sh

all: init validate fmt plan apply ## Run init, validate, fmt, plan, and apply

.DEFAULT_GOAL := help
