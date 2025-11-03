.PHONY: help fastapi-dev docker-build docker-run

help:
	@echo "Auth Service - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make fastapi-dev     - Run development server with hot reload"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    - Build Docker image"
	@echo "  make docker-run      - Run container"

fastapi-dev:
	fastapi dev app/app.py --reload --port 8002
	
docker-build:
	docker build -t auth-service .

docker-run:
	docker run -d -p 8000:8000 --name auth-service-container auth-service