# QNT9-SRS Root Makefile
# Convenience targets for the entire project

.PHONY: help test-docker-local test-source test-build test-runtime test-all lint-all clean install-dev
.PHONY: up down restart logs build-dev rebuild status health migrate test shell-search shell-frontend dev

# Default target
help:
	@echo "QNT9-SRS Project Commands"
	@echo "=========================="
	@echo ""
	@echo "  Docker Compose (Local Development):"
	@echo "  make up                 - Start all services (frontend, search, postgres, redis)"
	@echo "  make down               - Stop all services"
	@echo "  make restart            - Restart all services"
	@echo "  make logs               - Follow logs from all services"
	@echo "  make status             - Show status of all services"
	@echo "  make health             - Check health of all services"
	@echo "  make dev                - Start services and follow logs"
	@echo ""
	@echo "  Development Tools:"
	@echo "  make shell-search       - Open shell in search service container"
	@echo "  make shell-frontend     - Open shell in frontend service container"
	@echo "  make migrate            - Run database migrations"
	@echo "  make test               - Run all tests in containers"
	@echo "  make rebuild            - Rebuild and restart all services"
	@echo ""
	@echo "  Native Testing:"
	@echo "  make test-all           - Run all service tests natively (no Docker)"
	@echo ""
	@echo "  Code Quality:"
	@echo "  make format-all         - Auto-format all services with Black and isort"
	@echo ""
	@echo "  Maintenance:"
	@echo "  make install-dev        - Install development dependencies"
	@echo "  make clean              - Clean up test artifacts and caches"
	@echo ""
	@echo "  Infrastructure:"
	@echo "  make terraform-init     - Initialize Terraform"
	@echo "  make terraform-plan     - Plan Terraform changes (dev environment)"
	@echo ""

# Run all service tests natively
test-all:
	@echo "Running tests for all services..."
	@cd services/search-service && make test || true

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

# ============================================================================
# Docker Compose Commands (Local Development)
# ============================================================================

up: ## Start all services in detached mode
	@echo "Building and starting all services..."
	@echo ""
	docker-compose build --no-cache
	docker-compose up -d
	@echo ""
	@echo "All services started successfully!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Frontend:     http://localhost:8080"
	@echo "Search API:   http://localhost:8000"
	@echo "API Docs:     http://localhost:8000/api/docs"
	@echo "Metrics:      http://localhost:9090/metrics"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Tips:"
	@echo "  - Run 'make logs' to view logs"
	@echo "  - Run 'make health' to check service health"
	@echo "  - Run 'make status' to see service status"
	@echo "  - Code changes will auto-reload"
	@echo ""

down: ## Stop all services
	docker-compose down
	@echo "All services stopped"

restart: ## Restart all services
	docker-compose restart
	@echo "All services restarted"

build-dev: ## Rebuild all service images
	docker-compose build --no-cache
	@echo " All images rebuilt"

rebuild: down build-dev up ## Rebuild and restart all services

clean-docker: ## Stop services and remove volumes (destroys data!)
	@echo "WARNING: This will delete all Docker data. Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	docker-compose down -v
	@echo "All services stopped and volumes removed"

# Logs
logs: ## Follow logs from all services
	docker-compose logs -f

logs-search: ## Follow logs from search service only
	docker-compose logs -f search-service

logs-webapp: ## Follow logs from webapp service only
	docker-compose logs -f webapp-service

logs-db: ## Follow logs from PostgreSQL only
	docker-compose logs -f postgres

# Service Status
status: ## Show status of all services
	@docker-compose ps

health: ## Check health of all services
	@echo "Checking service health..."
	@echo ""
	@echo "Webapp Service:"
	@curl -sf http://localhost:3000/api/health 2>/dev/null && echo "  Healthy" || echo "  Not responding"
	@echo ""
	@echo "Search Service:"
	@curl -sf http://localhost:8000/api/v1/health | jq '.' 2>/dev/null || echo "  Not responding"
	@echo ""
	@echo "PostgreSQL:"
	@docker-compose exec -T postgres pg_isready -U qnt9_user -d qnt9_search 2>/dev/null || echo "  Not responding"
	@echo ""
	@echo "Redis:"
	@docker-compose exec -T redis redis-cli -a qnt9_redis_password ping 2>/dev/null || echo "  Not responding"
	@echo ""

# Shell Access
shell-search: ## Open shell in search service container
	docker-compose exec search-service /bin/bash

shell-webapp: ## Open shell in webapp service container
	docker-compose exec webapp-service /bin/sh

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U qnt9_user -d qnt9_search

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli -a qnt9_redis_password

# Database Operations
migrate: ## Run database migrations
	@echo "Running database migrations..."
	docker-compose exec search-service alembic upgrade head
	@echo "Database migrations completed"

migrate-create: ## Create a new migration (use: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "ERROR: MSG is required. Usage: make migrate-create MSG='your description'"; \
		exit 1; \
	fi
	docker-compose exec search-service alembic revision --autogenerate -m "$(MSG)"
	@echo "Migration created: $(MSG)"

db-reset: ## Reset database (destroys data!)
	@echo "WARNING: This will delete all database data. Press Ctrl+C to cancel, or Enter to continue..."
	@read dummy
	docker-compose down postgres
	docker volume rm qnt9-srs_postgres_data || true
	docker-compose up -d postgres
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	$(MAKE) migrate
	@echo "Database reset complete"

# Testing in Docker
test: ## Run all tests in containers
	@echo "Testing search service..."
	@docker-compose exec -T search-service sh -c "cd /app && PYTHONPATH=/app pytest tests/ -v --cov=app --cov-report=term-missing"
	@echo ""
	@echo "All tests completed!"

test-search-docker: ## Run search service tests in container
	docker-compose exec search-service sh -c "cd /app && PYTHONPATH=/app pytest tests/ -v --cov=app --cov-report=term-missing"

# Development workflow
dev: up logs ## Start services and follow logs

# Quick access
open-webapp: ## Open webapp in browser
	@python3 -m webbrowser http://localhost:3000 2>/dev/null || \
	open http://localhost:3000 2>/dev/null || \
	xdg-open http://localhost:3000 2>/dev/null || \
	echo "Visit: http://localhost:3000"

open-docs: ## Open API documentation in browser
	@python3 -m webbrowser http://localhost:8000/api/docs 2>/dev/null || \
	open http://localhost:8000/api/docs 2>/dev/null || \
	xdg-open http://localhost:8000/api/docs 2>/dev/null || \
	echo "Visit: http://localhost:8000/api/docs"
