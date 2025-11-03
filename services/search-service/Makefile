.PHONY: help fastapi-dev fastapi-dev-dd docker-build docker-run test test-cov clean

help:
	@echo "Search Service - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make fastapi-dev      - Run development server with hot reload (Port 8000)"
	@echo "  make fastapi-dev-dd   - Run development server with Datadog APM instrumentation"
	@echo "  make dev              - Run with uvicorn on port 8000"
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

fastapi-dev:
	fastapi dev app/app.py --reload --port 8000

dev:
	uvicorn app.app:app --host 0.0.0.0 --port 8000 --reload
	
docker-build:
	docker build -t search-service .

docker-run:
	docker run -d -p 8001:8000 --name search-service-container search-service

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -f .coverage
	rm -f *.db