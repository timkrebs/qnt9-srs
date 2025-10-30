.PHONY: help dev dev-reload test test-cov docker-build docker-run clean

help:
	@echo "Frontend Service - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev             - Run development server"
	@echo "  make dev-reload      - Run with auto-reload (watch templates)"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run tests with pytest"
	@echo "  make test-cov        - Run tests with coverage report"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run container"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean           - Remove cache and temporary files"

dev:
	uvicorn app.app:app --host 0.0.0.0 --port 8001

dev-reload:
	uvicorn app.app:app --reload --reload-dir app --reload-dir tests --host 0.0.0.0 --port 8001

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

docker-build:
	docker build -t frontend-service .

docker-run:
	docker run -d -p 8080:8080 \
		-e SEARCH_SERVICE_URL=http://search-service:8000 \
		--name frontend-service-container frontend-service

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -f .coverage
