.PHONY: help init validate fmt plan apply destroy clean check test

# Variables
TERRAFORM := terraform
TERRAFORM_DIR := .
TF_PLAN_FILE := terraform.tfplan
TF_VAR_FILE := terraform.tfvars

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

## help: Show this help message
help:
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Terraform Makefile - QNT9 SRS Infrastructure$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Available targets:$(NC)"
	@echo ""
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## /  /' | column -t -s ':'
	@echo ""
	@echo "$(YELLOW)Required Environment Variables:$(NC)"
	@echo "  VAULT_TOKEN     - HCP Vault authentication token"
	@echo "  VAULT_ADDR      - HCP Vault cluster URL"
	@echo "  VAULT_NAMESPACE - HCP Vault namespace (default: admin)"
	@echo ""
	@echo "$(YELLOW)Optional Variables:$(NC)"
	@echo "  TF_LOG          - Terraform log level (TRACE, DEBUG, INFO, WARN, ERROR)"
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"

## check-env: Check required environment variables
check-env:
	@echo "$(YELLOW)Checking environment variables...$(NC)"
	@if [ -z "$$VAULT_TOKEN" ]; then \
		echo "$(RED)✗ VAULT_TOKEN is not set$(NC)"; \
		echo "  Set it with: export VAULT_TOKEN='your-token'"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ VAULT_TOKEN is set$(NC)"; \
	fi
	@if [ -z "$$VAULT_ADDR" ]; then \
		echo "$(RED)✗ VAULT_ADDR is not set$(NC)"; \
		echo "  Set it with: export VAULT_ADDR='https://your-vault-url:8200'"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ VAULT_ADDR is set: $$VAULT_ADDR$(NC)"; \
	fi
	@if [ -z "$$VAULT_NAMESPACE" ]; then \
		echo "$(YELLOW)⚠ VAULT_NAMESPACE not set, using default 'admin'$(NC)"; \
		export VAULT_NAMESPACE=admin; \
	else \
		echo "$(GREEN)✓ VAULT_NAMESPACE is set: $$VAULT_NAMESPACE$(NC)"; \
	fi

## init: Initialize Terraform (download providers and modules)
init: check-env
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Initializing Terraform$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@$(TERRAFORM) init -upgrade
	@echo "$(GREEN)✓ Terraform initialized$(NC)"

## fmt: Format Terraform files
fmt:
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Formatting Terraform files$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@$(TERRAFORM) fmt -recursive
	@echo "$(GREEN)✓ Files formatted$(NC)"

## fmt-check: Check if Terraform files are formatted
fmt-check:
	@echo ""
	@echo "$(YELLOW)Checking Terraform formatting...$(NC)"
	@if $(TERRAFORM) fmt -check -recursive; then \
		echo "$(GREEN)✓ All files are properly formatted$(NC)"; \
	else \
		echo "$(RED)✗ Some files need formatting$(NC)"; \
		echo "  Run: make fmt"; \
		exit 1; \
	fi

## validate: Validate Terraform configuration
validate: init
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Validating Terraform configuration$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@$(TERRAFORM) validate
	@echo "$(GREEN)✓ Configuration is valid$(NC)"

## plan: Create an execution plan
plan: validate
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Creating execution plan$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@$(TERRAFORM) plan -out=$(TF_PLAN_FILE)
	@echo ""
	@echo "$(GREEN)✓ Plan created: $(TF_PLAN_FILE)$(NC)"
	@echo "$(YELLOW)  Review the plan above before applying$(NC)"
	@echo "$(YELLOW)  To apply: make apply$(NC)"

## plan-destroy: Create a destruction plan
plan-destroy: validate
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Creating destruction plan$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@$(TERRAFORM) plan -destroy -out=$(TF_PLAN_FILE)
	@echo ""
	@echo "$(GREEN)✓ Destruction plan created: $(TF_PLAN_FILE)$(NC)"
	@echo "$(RED)  WARNING: This will destroy all resources!$(NC)"
	@echo "$(YELLOW)  To apply: make apply$(NC)"

## show-plan: Show the current plan file
show-plan:
	@if [ -f $(TF_PLAN_FILE) ]; then \
		echo "$(GREEN)Showing plan file: $(TF_PLAN_FILE)$(NC)"; \
		$(TERRAFORM) show $(TF_PLAN_FILE); \
	else \
		echo "$(RED)No plan file found. Run 'make plan' first.$(NC)"; \
		exit 1; \
	fi

## apply: Apply the Terraform plan
apply:
	@if [ ! -f $(TF_PLAN_FILE) ]; then \
		echo "$(RED)No plan file found. Run 'make plan' first.$(NC)"; \
		exit 1; \
	fi
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Applying Terraform plan$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)Are you sure you want to apply this plan?$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or Enter to continue...$(NC)"
	@read -r confirm
	@$(TERRAFORM) apply $(TF_PLAN_FILE)
	@rm -f $(TF_PLAN_FILE)
	@echo ""
	@echo "$(GREEN)✓ Infrastructure deployed successfully$(NC)"

## destroy: Destroy all Terraform-managed infrastructure
destroy: check-env
	@echo ""
	@echo "$(RED)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(RED)  WARNING: This will destroy all infrastructure!$(NC)"
	@echo "$(RED)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Type 'yes' to confirm destruction:$(NC)"
	@read -r confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(TERRAFORM) destroy; \
		echo "$(GREEN)✓ Infrastructure destroyed$(NC)"; \
	else \
		echo "$(YELLOW)Destruction cancelled$(NC)"; \
	fi

## output: Show Terraform outputs
output:
	@echo "$(GREEN)Terraform outputs:$(NC)"
	@$(TERRAFORM) output

## output-json: Show Terraform outputs in JSON format
output-json:
	@$(TERRAFORM) output -json

## refresh: Refresh Terraform state
refresh: check-env
	@echo "$(YELLOW)Refreshing Terraform state...$(NC)"
	@$(TERRAFORM) refresh
	@echo "$(GREEN)✓ State refreshed$(NC)"

## state-list: List resources in Terraform state
state-list:
	@echo "$(GREEN)Resources in Terraform state:$(NC)"
	@$(TERRAFORM) state list

## graph: Generate a visual graph of resources
graph:
	@echo "$(YELLOW)Generating resource graph...$(NC)"
	@$(TERRAFORM) graph | dot -Tpng > terraform-graph.png
	@echo "$(GREEN)✓ Graph saved to terraform-graph.png$(NC)"
	@echo "$(YELLOW)  Note: Requires 'graphviz' to be installed$(NC)"

## clean: Remove Terraform generated files (local only)
clean:
	@echo ""
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)  Cleaning Terraform files$(NC)"
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(YELLOW)This will remove:$(NC)"
	@echo "  - .terraform/ directory"
	@echo "  - .terraform.lock.hcl file"
	@echo "  - $(TF_PLAN_FILE) file"
	@echo "  - crash.log files"
	@echo ""
	@echo "$(RED)WARNING: This will NOT remove state files for safety$(NC)"
	@echo "$(YELLOW)Type 'yes' to confirm:$(NC)"
	@read -r confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -rf .terraform; \
		rm -f .terraform.lock.hcl; \
		rm -f $(TF_PLAN_FILE); \
		rm -f crash.log; \
		rm -f terraform-graph.png; \
		echo "$(GREEN)✓ Terraform files cleaned$(NC)"; \
		echo "$(YELLOW)  Run 'make init' to reinitialize$(NC)"; \
	else \
		echo "$(YELLOW)Cleaning cancelled$(NC)"; \
	fi

## clean-all: Remove ALL Terraform files including state (DANGEROUS!)
clean-all:
	@echo ""
	@echo "$(RED)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(RED)  DANGER: This will remove ALL Terraform files!$(NC)"
	@echo "$(RED)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(RED)This includes:$(NC)"
	@echo "  - .terraform/ directory"
	@echo "  - .terraform.lock.hcl"
	@echo "  - terraform.tfstate"
	@echo "  - terraform.tfstate.backup"
	@echo "  - $(TF_PLAN_FILE)"
	@echo "  - crash.log"
	@echo ""
	@echo "$(RED)YOU WILL LOSE STATE TRACKING OF YOUR INFRASTRUCTURE!$(NC)"
	@echo "$(YELLOW)Type 'DELETE' to confirm:$(NC)"
	@read -r confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		rm -rf .terraform; \
		rm -f .terraform.lock.hcl; \
		rm -f $(TF_PLAN_FILE); \
		rm -f terraform.tfstate*; \
		rm -f crash.log; \
		rm -f terraform-graph.png; \
		echo "$(RED)✓ All Terraform files removed$(NC)"; \
		echo "$(YELLOW)  Run 'make init' to start fresh$(NC)"; \
	else \
		echo "$(YELLOW)Cleaning cancelled$(NC)"; \
	fi

## test: Run full test suite (fmt-check, validate, plan)
test: check-env fmt-check validate plan
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  All tests passed! ✓$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)Summary:$(NC)"
	@echo "  ✓ Environment variables validated"
	@echo "  ✓ Code formatting checked"
	@echo "  ✓ Configuration validated"
	@echo "  ✓ Plan created successfully"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  - Review the plan: make show-plan"
	@echo "  - Apply changes: make apply"
	@echo "  - Clean up: make clean"
	@echo ""

## check: Quick validation check (fmt-check + validate)
check: fmt-check validate
	@echo "$(GREEN)✓ All checks passed$(NC)"

## doctor: Check system dependencies
doctor:
	@echo "$(GREEN)Checking system dependencies...$(NC)"
	@echo ""
	@command -v terraform >/dev/null 2>&1 && \
		echo "$(GREEN)✓ Terraform: $$(terraform version | head -n1)$(NC)" || \
		echo "$(RED)✗ Terraform not found$(NC)"
	@command -v vault >/dev/null 2>&1 && \
		echo "$(GREEN)✓ Vault CLI: $$(vault version | head -n1)$(NC)" || \
		echo "$(YELLOW)⚠ Vault CLI not found (optional)$(NC)"
	@command -v aws >/dev/null 2>&1 && \
		echo "$(GREEN)✓ AWS CLI: $$(aws --version)$(NC)" || \
		echo "$(YELLOW)⚠ AWS CLI not found (optional)$(NC)"
	@command -v jq >/dev/null 2>&1 && \
		echo "$(GREEN)✓ jq: $$(jq --version)$(NC)" || \
		echo "$(YELLOW)⚠ jq not found (optional)$(NC)"
	@command -v dot >/dev/null 2>&1 && \
		echo "$(GREEN)✓ graphviz: installed$(NC)" || \
		echo "$(YELLOW)⚠ graphviz not found (needed for 'make graph')$(NC)"
	@echo ""
	@if [ -n "$$VAULT_TOKEN" ]; then \
		echo "$(GREEN)✓ VAULT_TOKEN is set$(NC)"; \
	else \
		echo "$(YELLOW)⚠ VAULT_TOKEN not set$(NC)"; \
	fi
	@if [ -n "$$VAULT_ADDR" ]; then \
		echo "$(GREEN)✓ VAULT_ADDR is set$(NC)"; \
	else \
		echo "$(YELLOW)⚠ VAULT_ADDR not set$(NC)"; \
	fi

## cost: Estimate infrastructure costs (requires infracost)
cost:
	@if command -v infracost >/dev/null 2>&1; then \
		echo "$(GREEN)Generating cost estimate...$(NC)"; \
		infracost breakdown --path .; \
	else \
		echo "$(YELLOW)infracost not installed$(NC)"; \
		echo "Install from: https://www.infracost.io/docs/"; \
	fi

## security: Run security scan (requires tfsec)
security:
	@if command -v tfsec >/dev/null 2>&1; then \
		echo "$(GREEN)Running security scan...$(NC)"; \
		tfsec .; \
	else \
		echo "$(YELLOW)tfsec not installed$(NC)"; \
		echo "Install from: https://github.com/aquasecurity/tfsec"; \
	fi

## lint: Run linting checks (requires tflint)
lint:
	@if command -v tflint >/dev/null 2>&1; then \
		echo "$(GREEN)Running linter...$(NC)"; \
		tflint --init; \
		tflint; \
	else \
		echo "$(YELLOW)tflint not installed$(NC)"; \
		echo "Install from: https://github.com/terraform-linters/tflint"; \
	fi
