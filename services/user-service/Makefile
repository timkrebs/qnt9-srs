.PHONY: help install dev-install test test-cov lint format clean run-v2 docker-build docker-run migrate

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt

dev-install: ## Install development dependencies
	pip install -r requirements.txt
	pip install pytest-mock faker httpx

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage (target: 70%)
	pytest tests/ --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=70

test-domain: ## Run domain layer tests only
	pytest tests/test_domain_entities.py -v

test-infra: ## Run infrastructure tests only
	pytest tests/test_infrastructure.py -v

lint: ## Run linting with mypy
	mypy app/ --ignore-missing-imports

format: ## Format code with black
	black app/ tests/
	isort app/ tests/

clean: ## Clean cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

run: ## Run service (old version)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-v2: ## Run service v2 (new Clean Architecture version)
	uvicorn app.app_v2:app --reload --host 0.0.0.0 --port 8000

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create new migration (use name=your_migration_name)
	alembic revision --autogenerate -m "$(name)"

docker-build: ## Build Docker image
	docker build -t qnt9-user-serivce:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 \
		-e DATABASE_URL=$${DATABASE_URL} \
		-e REDIS_URL=$${REDIS_URL} \
		qnt9-user-serivce:latest

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop services
	docker-compose down

redis-start: ## Start local Redis (requires Docker)
	docker run -d -p 6379:6379 --name qnt9-redis redis:7-alpine

redis-stop: ## Stop local Redis
	docker stop qnt9-redis && docker rm qnt9-redis

logs: ## View logs (requires service running)
	tail -f logs/user-serivce.log

db-shell: ## Open PostgreSQL shell
	psql $${DATABASE_URL}

redis-cli: ## Open Redis CLI
	redis-cli

check-health: ## Check service health
	curl http://localhost:8000/api/v1/health

check-ready: ## Check service readiness
	curl http://localhost:8000/api/v1/ready

metrics: 
	curl http://localhost:8000/metrics

api-docs:
	open http://localhost:8000/api/docs

search-test: 
	curl "http://localhost:8000/api/v1/search?query=$(query)"

cache-stats: 
	curl http://localhost:8000/api/v1/stats/cache
