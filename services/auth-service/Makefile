.PHONY: help run test test-cov format lint clean install

help:
	@echo "Auth Service - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run development server"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run tests"
	@echo "  make test-cov   - Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format     - Format code with black and isort"
	@echo "  make lint       - Run linters (ruff, mypy)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Remove cache and build files"

install:
	pip install -r requirements.txt

run:
	fastapi dev app/app.py --reload --port 8002

test:
	pytest -v

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term

format:
	black app/ tests/
	isort app/ tests/

lint:
	ruff check app/ tests/
	mypy app/

docker-build:
	docker build -t qnt9-auth-service .

docker-run:
	docker run -d -p 8001:8001 --env-file .env --name auth-service qnt9-auth-service

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
