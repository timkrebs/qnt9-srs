.PHONY: help install dev test clean docker-build docker-run

help:
	@echo "Watchlist Service - Make targets"
	@echo ""
	@echo "  install       Install dependencies"
	@echo "  dev           Run development server"
	@echo "  test          Run tests"
	@echo "  clean         Clean cache and temp files"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run Docker container"

install:
	pip install -r requirements.txt

dev:
	python -m uvicorn app.main:app --reload --port 8012

test:
	pytest tests/ -v

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

docker-build:
	docker build -t watchlist-service:latest .

docker-run:
	docker run -p 8012:8012 --env-file .env watchlist-service:latest
