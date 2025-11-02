# QNT9-SRS Root Makefile
# Convenience targets for the entire project

.PHONY: help test-docker-local test-source test-build test-runtime test-all lint-all clean install-dev

# Default target
help:
	@echo "QNT9-SRS Project Commands"
	@echo "=========================="
	@echo ""
	@echo "Native Testing:"
	@echo "  make test-all           - Run all service tests natively (no Docker)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format-all         - Auto-format all services with Black and isort"
	@echo ""
	@echo "Development:"
	@echo "  make install-dev        - Install development dependencies"
	@echo "  make clean              - Clean up test artifacts and caches"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make terraform-init     - Initialize Terraform"
	@echo "  make terraform-plan     - Plan Terraform changes (dev environment)"
	@echo ""

# Run all service tests natively
test-all:
	@echo "Running tests for all services..."
	@cd services/search-service && make test || true
	@cd services/frontend-service && make test || true

# Format all services
format-all:
	@echo "Formatting all services..."
	@for service in services/*/; do \
		if [ -f "$$service/requirements.txt" ] && [ -d "$$service/app" ]; then \
			echo "Formatting $$service..."; \
			cd "$$service" && \
			python3 -m black app/ tests/ && \
			python3 -m isort app/ tests/ && \
			cd ../..; \
		fi \
	done

# Install development dependencies
install-dev:
	@echo "Installing development dependencies..."
	pip install black isort ruff flake8 pylint mypy bandit pytest pytest-cov pytest-asyncio

# Clean up artifacts
clean:
	@echo "Cleaning up test artifacts and caches..."
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'htmlcov' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name 'coverage.xml' -delete
	find . -type f -name 'pytest-report.xml' -delete
	find . -type f -name '.coverage' -delete
	find . -type f -name 'test.db' -delete
	@echo "Cleanup complete!"

# Terraform shortcuts
terraform-init:
	@cd infrastructure/terraform && make init ENV=dev

terraform-plan:
	@cd infrastructure/terraform && make plan ENV=dev
