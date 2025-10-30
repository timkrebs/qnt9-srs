# QNT9-SRS Root Makefile
# Convenience targets for the entire project

.PHONY: help test-docker-local test-source test-build test-runtime test-all lint-all clean install-dev

# Default target
help:
	@echo "QNT9-SRS Project Commands"
	@echo "=========================="
	@echo ""
	@echo "CI/CD Pipeline (Local Docker Testing):"
	@echo "  make test-docker-local  - Run full 3-stage pipeline (SOURCE → BUILD → TEST)"
	@echo "  make test-source        - Stage 1: Run Pylint static analysis only"
	@echo "  make test-build         - Stage 2: Build Docker images only"
	@echo "  make test-runtime       - Stage 3: Run tests in Docker containers"
	@echo ""
	@echo "Native Testing:"
	@echo "  make test-all           - Run all service tests natively (no Docker)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint-all           - Run linters on all services"
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

# Run Docker-based tests locally (mirrors GitHub Actions - Full 3-stage pipeline)
test-docker-local:
	@echo "Running full CI/CD pipeline: SOURCE → BUILD → TEST"
	@./scripts/test-docker-local.sh

# Stage 1: Source analysis with Pylint
test-source:
	@echo "Running STAGE 1: SOURCE - Static Code Analysis"
	@echo "Analyzing source code with Pylint..."
	@for service in services/*/; do \
		if [ -f "$$service/requirements.txt" ] && [ -d "$$service/app" ]; then \
			echo ""; \
			echo "Analyzing $$service..."; \
			cd "$$service" && \
			python3 -m pylint app/ tests/ --exit-zero && \
			cd ../..; \
		fi \
	done
	@echo ""
	@echo "[PASS] Source analysis completed"

# Stage 2: Build Docker images
test-build:
	@echo "Running STAGE 2: BUILD - Docker Image Compilation"
	@echo "Building production-ready Docker images..."
	@for service in search-service frontend-service; do \
		if [ -d "services/$$service" ]; then \
			echo ""; \
			echo "Building $$service..."; \
			docker build \
				--build-arg BUILDKIT_INLINE_CACHE=1 \
				-t "qnt9srs/$$service:local-test" \
				-f "services/$$service/Dockerfile" \
				"services/$$service" || exit 1; \
		fi \
	done
	@echo ""
	@echo "[PASS] Docker images built successfully"

# Stage 3: Run tests in Docker containers
test-runtime:
	@echo "Running STAGE 3: TEST - Runtime Tests in Docker Containers"
	@echo "Testing microservices in production-like environment..."
	@for service in search-service frontend-service; do \
		if [ -d "services/$$service" ]; then \
			echo ""; \
			echo "Testing $$service in Docker..."; \
			docker run --rm \
				-v "$$(pwd)/services/$$service:/app" \
				-e USE_LOCAL_DB=true \
				-e DATABASE_URL=sqlite:///./test.db \
				-w /app \
				"qnt9srs/$$service:local-test" \
				sh -c "pip install --user pytest pytest-cov pytest-asyncio httpx && export PATH=\"\$$PATH:\$$HOME/.local/bin\" && pytest -v --cov=app" || exit 1; \
		fi \
	done
	@echo ""
	@echo "[PASS] All runtime tests passed"

# Run all service tests natively
test-all:
	@echo "Running tests for all services..."
	@cd services/search-service && make test || true
	@cd services/frontend-service && make test || true

# Lint all services
lint-all:
	@echo "Linting all services..."
	@for service in services/*/; do \
		if [ -f "$$service/Makefile" ]; then \
			echo "Linting $$service..."; \
			cd "$$service" && make lint || true; \
			cd ../..; \
		fi \
	done

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
