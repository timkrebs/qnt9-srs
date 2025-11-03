[![Datadog Software Composition Analysis](https://github.com/timkrebs/qnt9-srs/actions/workflows/datadog-sca.yml/badge.svg)](https://github.com/timkrebs/qnt9-srs/actions/workflows/datadog-sca.yml)
[![Datadog Static Code Analysis](https://github.com/timkrebs/qnt9-srs/actions/workflows/datadog-static-analysis.yml/badge.svg)](https://github.com/timkrebs/qnt9-srs/actions/workflows/datadog-static-analysis.yml)


<div align="center">
  <img src="./docs/images/QNT9_Logo.png" alt="QNT9 Logo" width="400"/>
  
  # QNT9 Stock Recommendation System
  
  ### #QNT9-SRS
  
  **An intelligent stock analysis and recommendation platform**
  
  [![License:](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Azure](https://img.shields.io/badge/Cloud-Azure-0078D4)](https://azure.microsoft.com)
  [![Terraform](https://img.shields.io/badge/IaC-Terraform-7B42BC)](https://www.terraform.io/)
  
</div>

---

## Introduction

QNT9-SRS is a comprehensive microservice-based stock recommendation system that provides users with real-time stock analysis, personalized watchlists, and automated weekly reports. Built with a modern cloud-native architecture, the platform delivers actionable insights to help investors make informed decisions.

### Key Features

- **Smart Stock Search** - Search stocks by ISIN, WKN, or ticker symbol with validation
- **Real-time Data** - Integration with Yahoo Finance and Alpha Vantage APIs
- **Intelligent Caching** - PostgreSQL-based caching with 5-minute TTL for performance
- **Secure Authentication** - JWT-based auth with HashiCorp Vault secrets management
- **Microservices Architecture** - Scalable, cloud-native design on Azure
- **Production Monitoring** - Datadog APM with Application Security Management
- **Infrastructure as Code** - Terraform for automated Azure provisioning

### Technology Stack

**Backend Microservices:**
- Python (FastAPI) - All microservices
- PostgreSQL - Primary Database
- SQLite - Local development & testing
- HashiCorp Vault - Secrets management
- Datadog APM - Application monitoring

**Infrastructure:**
- Azure Cloud Platform
- Azure Kubernetes Service (AKS)
- Azure Container Registry (ACR)
- Azure PostgreSQL
- Azure Key Vault
- Terraform (Infrastructure as Code)
- Docker & Docker Compose

**Development & CI/CD:**
- GitHub Actions (CI/CD)
- Docker Scout (Security scanning)
- Pre-commit hooks (Code quality)
- Pytest (Testing framework)
- Black, isort, Ruff, Flake8 (Code formatting & linting)
- Pylint (Static analysis)

**Monitoring:**
- Datadog APM & Application Security
- Azure Application Insights

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python** (3.11 or later)
- **Docker & Docker Compose**
- **Terraform** (v1.5.0 or later)
- **Azure CLI**
- **Git**
- **HashiCorp Vault** (for local development with secrets)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/timkrebs/qnt9-srs.git
cd qnt9-srs
```

2. **Install development dependencies**
```bash
make install-dev
```

3. **Set up environment variables**

For each service, create a `.env` file or set environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qnt9_srs
# For local testing, SQLite is used automatically
USE_LOCAL_DB=true

# Vault (optional for local dev)
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=your-vault-token

# Stock APIs (stored in Vault for production)
YAHOO_FINANCE_API_KEY=your-yahoo-finance-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key

# Datadog (optional for local dev)
DD_ENV=local
DD_SERVICE=qnt9-srs
DD_VERSION=1.0.0
```

4. **Run tests locally**
```bash
# Run full CI/CD pipeline locally (recommended)
make test-docker-local

# Or test individual services
cd services/search-service
make test
```

5. **Start services with Docker Compose** (coming soon)
```bash
docker-compose up -d
```

### Configuration

#### Required Environment Variables

**Database Configuration:**
```bash
# Production
DATABASE_URL=postgresql://user:password@host:5432/qnt9_srs

# Local Development (automatic SQLite fallback)
USE_LOCAL_DB=true
DATABASE_URL=sqlite:///./qnt9_srs.db
```

**HashiCorp Vault:**
```bash
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=your-vault-dev-token
```

**Stock Market APIs:**
```bash
# These should be stored in Vault for production
YAHOO_FINANCE_API_KEY=your-yahoo-finance-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
```

**Datadog Monitoring:**
```bash
DD_ENV=development
DD_SERVICE=qnt9-srs
DD_VERSION=1.0.0
DD_AGENT_HOST=localhost
DD_TRACE_AGENT_PORT=8126
```

---

## Documentation

### Architecture

The system follows a microservices architecture deployed on Azure Kubernetes Service:

```
┌─────────────────────────────────────────────────────┐
│                 Azure Front Door                    │
│              (Load Balancer / CDN)                  │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│        Azure Kubernetes Service (AKS)               │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │    Auth      │  │    Search    │  │ Analysis  │ │
│  │   Service    │  │   Service    │  │  Service  │ │
│  │  (FastAPI)   │  │  (FastAPI)   │  │ (FastAPI) │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                  │                 │       │
│  ┌──────▼──────────────────▼─────────────────▼────┐ │
│  │         Azure PostgreSQL Database              │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
         │                           │
┌────────▼────────┐        ┌─────────▼──────────┐
│ Azure Key Vault │        │  Datadog APM       │
│   (Secrets)     │        │  (Monitoring)      │
└─────────────────┘        └────────────────────┘
```

**Current Services:**
- **auth-service**: User authentication and JWT token management
- **search-service**: Stock search with ISIN/WKN/symbol validation
- **analysis-service**: Stock analysis and recommendations (in development)
- **data-ingestion-service**: Market data ingestion (in development)
- **frontend-service**: API gateway and frontend (in development)

### API Documentation

Each service provides OpenAPI/Swagger documentation:

**Search Service:**
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI Spec**: http://localhost:8001/openapi.json

**Auth Service:**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Project Structure
```
qnt9-srs/
├── .github/
│   └── workflows/              # CI/CD pipelines
│       ├── ci-python.yml       # Python services CI/CD
│       ├── datadog-sca.yml     # Software Composition Analysis
│       └── datadog-static-analysis.yml
├── docs/
│   ├── MicroserviceArchitecture.md
│   └── CICD-GH-Actions/        # CI/CD documentation
├── infrastructure/
│   ├── terraform/              # Terraform IaC
│   │   ├── modules/            # Reusable modules
│   │   │   ├── aks/            # Azure Kubernetes Service
│   │   │   ├── acr/            # Azure Container Registry
│   │   │   ├── postgresql/     # Azure PostgreSQL
│   │   │   └── key-vault/      # Azure Key Vault
│   │   └── environments/       # Environment configs
│   └── helm-charts/            # Kubernetes Helm charts
├── scripts/
│   ├── test-docker-local.sh    # Local Docker testing
│   └── README.md               # Scripts documentation
├── services/
│   ├── auth-service/           # Authentication service
│   │   ├── app/                # FastAPI application
│   │   ├── tests/              # Pytest tests
│   │   ├── Dockerfile          # Multi-stage build
│   │   └── requirements.txt
│   ├── search-service/         # Stock search service
│   │   ├── app/                # FastAPI application
│   │   ├── tests/              # Pytest tests
│   │   ├── alembic/            # Database migrations
│   │   └── Dockerfile
│   ├── analysis-service/       # Stock analysis (planned)
│   ├── data-ingestion-service/ # Data ingestion (planned)
│   └── frontend-service/       # API gateway (planned)
├── .pre-commit-config.yaml     # Pre-commit hooks
├── codecov.yaml                # Code coverage config
├── Makefile                    # Project commands
└── README.md
```

### Deployment

#### Deploy to Azure with Terraform

1. **Initialize Terraform**
```bash
cd infrastructure/terraform
terraform init
```

2. **Plan infrastructure changes**
```bash
# Development environment
terraform plan -var-file="environments/dev.tfvars"

# Staging environment
terraform plan -var-file="environments/staging.tfvars"

# Production environment
terraform plan -var-file="environments/prd.tfvars"
```

3. **Apply infrastructure**
```bash
terraform apply -var-file="environments/dev.tfvars"
```

4. **Verify deployment**
```bash
# Check AKS cluster
az aks show --resource-group rg-qnt9-srs-dev --name aks-qnt9-srs-dev

# Get AKS credentials
az aks get-credentials --resource-group rg-qnt9-srs-dev --name aks-qnt9-srs-dev

# Check pods
kubectl get pods -n qnt9-srs
```

#### CI/CD with GitHub Actions

The project uses GitHub Actions for automated testing and deployment:

- **Pull Request**: Runs tests and linters
- **Push to development**: Deploys to dev environment
- **Push to main**: Deploys to production

See [`.github/workflows/ci-python.yml`](.github/workflows/ci-python.yml) for details.

---

## Development

### Development Workflow

1. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes**
   - Follow the coding standards (Black, isort, Flake8, Pylint)
   - Write unit tests (pytest)
   - Update documentation

3. **Run tests locally**
```bash
# Recommended: Full 3-stage pipeline (SOURCE → BUILD → TEST)
make test-docker-local

# Quick: Run individual stages
make test-source    # Pylint static analysis
make test-build     # Docker image compilation
make test-runtime   # Tests in Docker containers

# Or test specific service
cd services/search-service
make test
```

4. **Format and lint code**
```bash
# Auto-format all code
make format-all

# Run all linters
make lint-all
```

5. **Commit with conventional commits**
```bash
git commit -m "feat: add stock search autocomplete"
git commit -m "fix: resolve authentication token expiry issue"
git commit -m "docs: update API documentation"
```

6. **Push and create Pull Request**
```bash
git push origin feature/your-feature-name
```

### Coding Standards

- **Python**: PEP 8, Black (line length: 100), isort, Ruff, Flake8, Pylint
- **Type Hints**: Use type annotations where possible
- **Testing**: Minimum 70% coverage (target: 80%+)
- **Git Commits**: Conventional Commits specification
- **Documentation**: Docstrings for all functions/classes

### Running Tests

#### Quick Reference

```bash
# Recommended: Full 3-stage CI/CD pipeline (mirrors GitHub Actions)
make test-docker-local        # SOURCE → BUILD → TEST in Docker

# Individual pipeline stages
make test-source              # Stage 1: Pylint static analysis
make test-build               # Stage 2: Docker image compilation  
make test-runtime             # Stage 3: Tests in containers

# Other commands
make test-all                 # Run all tests natively (no Docker)
make lint-all                 # Run linters on all services
make format-all               # Auto-format code (Black, isort)
make clean                    # Clean up test artifacts
make help                     # Show all available commands
```

#### Docker-Based Testing (Recommended)

The `test-docker-local` command runs a **3-stage CI/CD pipeline** that mirrors GitHub Actions:

**STAGE 1: SOURCE - Static Code Analysis**
- Pylint comprehensive analysis (7.0/10 threshold)
- Quick Black and isort validation
- Identifies code quality issues before compilation

**STAGE 2: BUILD - Docker Image Compilation**
- Builds production-ready Docker images
- Uses BuildKit for efficient caching
- Reports image sizes

**STAGE 3: TEST - Runtime Tests in Containers**
- Executes pytest in isolated Docker containers
- Production-like environment (mirrors deployment)
- Coverage analysis with HTML reports
- Optional Docker Scout security scanning

**Example output:**
```bash
$ make test-docker-local

╔════════════════════════════════════════════════════════════╗
║  STAGE: SOURCE - Static Code Analysis
╚════════════════════════════════════════════════════════════╝

===> Analyzing search-service source code
[INFO] Command: pylint app/ tests/
[INFO] Pylint score: 8.45/10.00
[PASS] Pylint analysis passed (score >= 7.0)

╔════════════════════════════════════════════════════════════╗
║  STAGE: BUILD - Docker Image Compilation
╚════════════════════════════════════════════════════════════╝

===> Building Docker image for search-service
[INFO] Image: qnt9srs/search-service:local-test
[PASS] Docker image built successfully
[INFO] Image size: 234MB

╔════════════════════════════════════════════════════════════╗
║  STAGE: TEST - Runtime Tests in Docker Containers
╚════════════════════════════════════════════════════════════╝

===> Testing search-service in Docker container
===== 47 passed in 2.34s =====
[PASS] Container test execution completed

===> Coverage analysis for search-service
Coverage Report:
  Total coverage: 77.33%
  Minimum threshold: 70%
  Target threshold: 80%
[WARN] Coverage is 77.33% (70-80% range)
[INFO] Aim for 80%+ coverage for better quality

╔════════════════════════════════════════════════════════════╗
║  STAGE: SUMMARY - Pipeline Results
╚════════════════════════════════════════════════════════════╝

  Service: search-service
  Status:  [WARN] ACCEPTABLE
  Coverage: 77.33%

  Service: frontend-service
  Status:  [PASS] GOOD
  Coverage: 89.09%

[PASS] All services passed local testing!
```

**Why use this?**
- Catches issues **before** pushing to GitHub
- Saves CI/CD minutes
- Tests in production-like Docker environment
- Provides instant feedback with detailed logs
- Generates HTML coverage reports locally

**Coverage Reports:**
After running tests, open the HTML reports in your browser:

```bash
# View detailed coverage for each service
open services/search-service/htmlcov/index.html
open services/frontend-service/htmlcov/index.html
```

**Coverage Thresholds:**
| Level | Percentage | Result |
|-------|-----------|--------|
| Fail | < 70% | Pipeline fails |
| Acceptable | 70-80% | Warning (aim higher) |
| Good | 80-90% | Passing |
| Excellent | ≥ 90% | Outstanding! |

See [scripts/README.md](scripts/README.md) for detailed pipeline documentation.

#### Per-Service Testing

```bash
# Test individual services natively
cd services/search-service
make test           # Run pytest
make lint           # Run linters
make format         # Auto-format code

# Or use pytest directly
pytest -v --cov=app --cov-report=html
```

### Local Development Tips

- **SQLite Auto-Fallback**: Set `USE_LOCAL_DB=true` for automatic SQLite usage
- **Vault Integration**: Optional for local dev - services work without it
- **Datadog APM**: Optional for local dev - instrumented but won't send traces without agent
- **Hot Reload**: FastAPI auto-reloads on code changes in development mode
- **Debug Mode**: Set `DEBUG=true` for verbose logging
- **Pre-commit Hooks**: Run `pre-commit install` to enable automatic code quality checks

---

## Contributing

We welcome contributions from the community! Here's how you can help:

### How to Contribute

1. **Fork the repository**
2. **Clone your fork**
```bash
   git clone https://github.com/your-username/qnt9-srs.git
```
3. **Create a feature branch**
4. **Make your changes**
5. **Run tests and linting**
6. **Submit a Pull Request**

### Pull Request Guidelines

- Ensure all tests pass locally (`make test-docker-local`)
- Follow coding standards (Black, isort, Pylint)
- Maintain or improve code coverage (minimum 70%)
- Update documentation if needed
- Add tests for new features
- Keep PRs focused (one feature/fix per PR)
- Write clear commit messages (Conventional Commits)
- Fill out the PR template completely

### Issue Reporting

Found a bug or have a feature request? Please create an issue with:
- Clear description of the problem/feature
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Screenshots if applicable
- Your environment details

### Code Review Process

1. All PRs require at least one approval
2. CI/CD pipeline must pass (all 3 stages)
3. Code coverage must be ≥ 70%
4. Pylint score should be ≥ 7.0/10
5. No security vulnerabilities (Docker Scout)
6. Documentation must be updated for new features

---

## Project Management

We use **GitHub Projects** for task management. Check our project board:
- **Sprint Backlog**: Current sprint tasks
- **In Progress**: Tasks being worked on
- **In Review**: PRs under review
- **Done**: Completed tasks

### Sprint Schedule

- **Sprint Duration**: 2 weeks
- **Sprint Planning**: Every other Monday
- **Daily Standup**: 10:00 AM (async via GitHub Discussions)
- **Sprint Review/Retro**: Last Friday of sprint

---

## Current Status

**Development Phase**: MVP in Progress

**Completed:**
- Infrastructure Foundation (Terraform, Azure AKS, ACR, PostgreSQL)
- CI/CD Pipeline (GitHub Actions with 3-stage testing)
- Authentication Service (JWT, Vault integration, Datadog APM)
- Stock Search Service (ISIN/WKN validation, caching, multi-API)
- Database Migrations (Alembic)
- Local Development Tooling (Docker testing, pre-commit hooks)

**In Progress:**
- Analysis Service (Stock analysis algorithms)
- Data Ingestion Service (Market data pipelines)
- Frontend Service (API gateway)

**Planned:**
- Watchlist Management
- Report Generation Service
- Notification Service
- Production Deployment to Azure AKS

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Links

- **Repository**: https://github.com/timkrebs/qnt9-srs
- **Documentation**: [docs/](docs/)
- **CI/CD Pipeline**: [.github/workflows/](.github/workflows/)
- **Infrastructure**: [infrastructure/terraform/](infrastructure/terraform/)
- **Issue Tracker**: https://github.com/timkrebs/qnt9-srs/issues

---

<div align="center">
  
  **Built with ❤️ by the QNT9 Team**
  
  Star us on GitHub if you find this project useful!
  
</div>