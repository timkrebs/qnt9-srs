# Contributing to QNT9-SRS

Thank you for your interest in contributing to the QNT9 Stock Recommendation System! This document provides guidelines and information for contributors.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [CI/CD Pipeline](#cicd-pipeline)
- [Code Quality Standards](#code-quality-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Branch Protection Rules](#branch-protection-rules)

## Getting Started

### Prerequisites

- Python 3.11 or 3.12
- Node.js 20.x (for frontend services)
- Docker and Docker Compose
- Azure CLI
- kubectl
- Git

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/timkrebs/qnt9-srs.git
   cd qnt9-srs
   ```

2. **Set up your service:**
   ```bash
   cd services/auth-service
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Copy environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

4. **Run tests:**
   ```bash
   pytest
   ```

5. **Run the service locally:**
   ```bash
   uvicorn app.app:app --reload
   ```

## Development Workflow

### Branch Strategy

We use **Git Flow** branching model:

- `main` - Production-ready code, deployed to staging
- `develop` - Integration branch for features, deployed to development
- `feature/*` - Feature development branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Critical production fixes

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Committing Changes

We follow **Conventional Commits** specification:

```bash
git commit -m "feat(auth): add OAuth2 Google provider"
git commit -m "fix(auth): resolve token expiration issue"
git commit -m "docs(readme): update installation steps"
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## CI/CD Pipeline

### Pipeline Overview

Our CI/CD pipeline automatically runs on every push and pull request:

```
Lint → Test → Build → Push → Deploy → Notify
```

### Pipeline Stages

#### 1. Lint (Code Quality)
- **Black**: Code formatting check
- **isort**: Import sorting check
- **Flake8**: Python linting
- **MyPy**: Static type checking
- **Duration**: ~2 minutes

```bash
# Run locally before pushing
black --check app/
isort --check-only app/
flake8 app/
mypy app/
```

#### 2. Test (Unit & Integration Tests)
- **Pytest**: Run all tests
- **Coverage**: Generate coverage reports
- **Matrix**: Test against Python 3.11 and 3.12
- **Duration**: ~3 minutes

```bash
# Run locally
pytest --cov=app --cov-report=html
```

**Minimum Coverage**: 80% (enforced in CI)

#### 3. Security Scan
- **Safety**: Check for vulnerable dependencies
- **Bandit**: Security linter for Python
- **Duration**: ~1 minute

```bash
# Run locally
safety check -r requirements.txt
bandit -r app/
```

#### 4. Build (Docker Image)
- Build Docker image for the service
- Tag with branch name and commit SHA
- Cache layers for faster builds
- **Duration**: ~3 minutes

#### 5. Push (to Azure Container Registry)
- Push image to ACR
- Only on push to `develop` or `main`
- **Duration**: ~2 minutes

#### 6. Deploy (to Azure Kubernetes Service)
- **Development**: Auto-deploy on push to `develop`
- **Staging**: Auto-deploy on push to `main`
- **Production**: Manual approval required
- **Duration**: ~3 minutes

### Total Pipeline Duration

**Target**: < 10 minutes
**Typical**: 7-8 minutes

### Workflow Files

Each microservice has its own workflow file:

```
.github/workflows/
├── auth-service-ci-cd.yml
├── data-ingestion-service-ci-cd.yml
├── analysis-service-ci-cd.yml
└── terraform-apply.yml
```

### Environment Secrets

Required GitHub Secrets:

```bash
# Azure Credentials
AZURE_CREDENTIALS          # Service principal for dev/staging
AZURE_CREDENTIALS_PRD      # Service principal for production

# Azure Container Registry
ACR_LOGIN_SERVER          # e.g., acrqnt9srsdev.azurehq.io
ACR_USERNAME              # Admin username
ACR_PASSWORD              # Admin password

# Application Secrets
DATABASE_URL              # PostgreSQL connection string
JWT_SECRET                # JWT signing secret
VAULT_ADDR                # HashiCorp Vault address
VAULT_TOKEN               # Vault access token

# Monitoring
DD_API_KEY                # Datadog API key
DD_APP_KEY                # Datadog application key
CODECOV_TOKEN             # Codecov upload token
```

## Code Quality Standards

### Python Code Style

We follow **PEP 8** with these modifications:

- **Line length**: 100 characters (not 79)
- **Formatter**: Black
- **Import sorting**: isort
- **Type hints**: Encouraged but not required

### Code Formatting

```bash
# Format code with Black
black app/

# Sort imports
isort app/

# Check with Flake8
flake8 app/ --max-line-length=100
```

### Type Hints

```python
# Good
def create_user(email: str, password: str) -> User:
    ...

# Also acceptable (gradual typing)
def create_user(email, password):
    ...
```

## Testing

### Test Structure

```
services/auth-service/
├── app/
│   ├── __init__.py
│   ├── app.py
│   └── ...
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    └── test_integration.py
```

### Writing Tests

```python
import pytest
from fastapi.testclient import TestClient
from app.app import app

client = TestClient(app)

def test_register_user():
    """Test user registration endpoint"""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "pass123"}
    )
    assert response.status_code == 201
    assert "user_id" in response.json()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_register_user

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Test Coverage Requirements

- **Minimum overall coverage**: 80%
- **Critical paths**: 100% (auth, payment, etc.)
- **CI blocks**: PRs with < 80% coverage

## Pull Request Process

### 1. Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create PR on GitHub targeting `develop` branch.

### 2. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No new warnings
```

### 3. Automated Checks

Pull requests must pass:

All linting checks
All unit tests (Python 3.11 & 3.12)
Security scans
Code coverage ≥ 80%
No merge conflicts

### 4. Code Review

- **Required reviewers**: 1 (for `develop`)
- **Required reviewers**: 2 (for `main`)
- Address all review comments
- Re-request review after changes

### 5. Merge

- Use **Squash and Merge** for feature branches
- Use **Merge Commit** for `develop` → `main`
- Delete branch after merge

## Branch Protection Rules

### `develop` Branch

- Require pull request before merging
- Require 1 approval
- Require status checks to pass:
  - Lint Python Code
  - Run Tests (Python 3.11)
  - Run Tests (Python 3.12)
  - Security Scan
- Require branches to be up to date
- Do not allow force pushes
- Do not allow deletions

### `main` Branch

- Require pull request before merging
- Require 2 approvals
- Require status checks to pass (same as develop)
- Require deployments to succeed before merge
- Do not allow bypassing the above settings
- Do not allow force pushes
- Do not allow deletions

## Deployment Process

### Development Deployment

**Automatic** when merged to `develop`:

1. CI/CD pipeline runs
2. Docker image built and pushed
3. Deployed to dev AKS cluster
4. Health checks verify deployment

### Staging Deployment

**Automatic** when merged to `main`:

1. CI/CD pipeline runs
2. Docker image built and pushed
3. Deployed to staging AKS cluster
4. Integration tests run
5. Smoke tests verify deployment

### Production Deployment

**Manual approval** required:

1. Trigger workflow manually
2. Wait for approval (5 min + 2 reviewers)
3. Blue-green deployment to production
4. Health checks and smoke tests
5. Rollback on failure

## Getting Help

- **Documentation**: See `docs/` folder
- **Issues**: Create a GitHub issue
- **Discussions**: Use GitHub Discussions
- **Slack**: #qnt9-dev channel (internal)

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
