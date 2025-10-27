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

- **Smart Stock Search** - Search stocks by ISIN, WKN, or company name with instant results
- **Real-time Analysis** - Live stock data integration with Yahoo Finance and Alpha Vantage
- **Custom Watchlists** - Organize and track your favorite stocks in personalized watchlists
- **Weekly Reports** - Automated PDF/HTML reports delivered directly to your inbox
- **Secure Authentication** - OAuth2 support with Google and Microsoft integration
- **Responsive Design** - Seamless experience across desktop and mobile devices

### Technology Stack

**Frontend:**
- React.js / Vue.js
- Azure Static Web Apps
- Tailwind CSS

**Backend:**
- Microservices Architecture
- Node.js (Express) - Auth & Watchlist Services
- Python (FastAPI) - Stock Search & Report Generation
- PostgreSQL - Primary Database
- Azure Blob Storage - Report Storage

**Infrastructure:**
- Azure Cloud Platform
- Azure Container Instances
- Azure Functions (Scheduled Jobs)
- Terraform (Infrastructure as Code)
- Docker & Docker Compose

**Monitoring:**
- Grafana
- Azure Application Insights

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v20.x or later)
- **Python** (3.11 or later)
- **Docker & Docker Compose**
- **Terraform** (v1.5.0 or later)
- **Azure CLI**
- **Git**

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/your-org/qnt9-srs.git
   cd qnt9-srs
```

2. **Set up environment variables**
```bash
   cp .env.example .env
   # Edit .env with your configuration
```

3. **Install dependencies**
   
   For frontend:
```bash
   cd frontend
   npm install
```
   
   For each service:
```bash
   cd services/auth-service
   npm install
   
   cd ../stock-search-service
   pip install -r requirements.txt
```

4. **Start local development with Docker Compose**
```bash
   docker-compose up -d
```

5. **Run database migrations**
```bash
   npm run migrate:dev
```

6. **Access the application**
   - Frontend: http://localhost:3000
   - API Gateway: http://localhost:8080
   - Grafana: http://localhost:3001

### Configuration

#### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qnt9_srs

# Authentication
JWT_SECRET=your-jwt-secret-key
OAUTH_GOOGLE_CLIENT_ID=your-google-client-id
OAUTH_GOOGLE_CLIENT_SECRET=your-google-client-secret
OAUTH_MICROSOFT_CLIENT_ID=your-microsoft-client-id
OAUTH_MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# Stock APIs
YAHOO_FINANCE_API_KEY=your-yahoo-finance-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key

# Email Service
SENDGRID_API_KEY=your-sendgrid-key

# Azure
AZURE_STORAGE_CONNECTION_STRING=your-azure-storage-connection
AZURE_BLOB_CONTAINER_NAME=reports
```

---

## Documentation

### Architecture

The system follows a microservices architecture with the following components:
```
┌─────────────┐
│   Frontend  │ (React/Vue.js)
└──────┬──────┘
       │
┌──────▼───────────────────────────────┐
│         API Gateway (Nginx)          │
└──────┬───────────┬──────────┬────────┘
       │           │          │
   ┌───▼───┐   ┌──▼────┐  ┌──▼─────────┐
   │ Auth  │   │Stock  │  │ Watchlist  │
   │Service│   │Search │  │  Service   │
   └───┬───┘   └───────┘  └──────┬─────┘
       │                          │
   ┌───▼──────────────────────────▼────┐
   │      PostgreSQL Database          │
   └───────────────────────────────────┘
```

### API Documentation

Once the services are running, access the API documentation:
- **Swagger UI**: http://localhost:8080/api/docs
- **OpenAPI Spec**: http://localhost:8080/api/openapi.json

### Project Structure
```
qnt9-srs/
├── .github/
│   └── workflows/          # CI/CD pipelines
├── docs/
│   ├── architecture/       # Architecture diagrams
│   ├── api-specs/          # API specifications
│   └── user-stories/       # User stories and requirements
├── frontend/               # React/Vue.js application
├── services/
│   ├── auth-service/       # Authentication service
│   ├── stock-search-service/
│   ├── watchlist-service/
│   ├── report-generation-service/
│   └── notification-service/
├── infrastructure/
│   ├── terraform/          # Terraform IaC files
│   └── kubernetes/         # Kubernetes manifests
├── docker-compose.yml      # Local development setup
└── README.md
```

### Deployment

#### Deploy to Azure

1. **Provision infrastructure with Terraform**
```bash
   cd infrastructure/terraform
   terraform init
   terraform plan -var-file="environments/prod.tfvars"
   terraform apply -var-file="environments/prod.tfvars"
```

2. **Deploy services via GitHub Actions**
   - Push to `main` branch triggers automatic deployment
   - Monitor deployment in GitHub Actions tab

3. **Verify deployment**
```bash
   az containerinstance show \
     --resource-group rg-stock-recommendation \
     --name ci-auth-service
```

---

## Development

### Development Workflow

1. **Create a feature branch**
```bash
   git checkout -b feature/your-feature-name
```

2. **Make your changes**
   - Follow the coding standards (ESLint/Flake8)
   - Write unit tests
   - Update documentation

3. **Run tests locally**
```bash
   npm test                 # Frontend & Node.js services
   pytest                   # Python services
```

4. **Commit with conventional commits**
```bash
   git commit -m "feat: add stock search autocomplete"
   git commit -m "fix: resolve authentication token expiry issue"
   git commit -m "docs: update API documentation"
```

5. **Push and create Pull Request**
```bash
   git push origin feature/your-feature-name
```

### Coding Standards

- **JavaScript/Node.js**: ESLint with Airbnb config
- **Python**: PEP 8, Flake8, Black formatter
- **Git Commits**: Conventional Commits specification
- **Documentation**: JSDoc for JS, Docstrings for Python

### Running Tests
```bash
# Frontend tests
cd frontend
npm test

# Backend service tests
cd services/auth-service
npm test

cd services/stock-search-service
pytest tests/ --cov

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e
```

### Local Development Tips

- Use `docker-compose` for local services
- Set `NODE_ENV=development` for verbose logging
- Use hot-reload for frontend development
- Mock external APIs during development (see `mocks/` directory)

---

## 🤝 Contributing

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

- Ensure all tests pass
- Follow coding standards
- Update documentation if needed
- Add tests for new features
- Keep PRs focused (one feature/fix per PR)
- Write clear commit messages

### Issue Reporting

Found a bug or have a feature request? Please create an issue with:
- Clear description of the problem/feature
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Screenshots if applicable
- Your environment details

### Code Review Process

1. All PRs require at least one approval
2. CI/CD pipeline must pass
3. Code coverage should not decrease
4. Documentation must be updated

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

**MVP Development**: Sprint 3 of 8

- Sprint 1: Infrastructure Foundation (Completed)
- Sprint 2: Authentication System (Completed)
- Sprint 3: Stock Search Functionality (In Progress)
- Sprint 4-8: Watchlists & Reports (Upcoming)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Links

- **Live Demo**: https://qnt9-srs.azurewebsites.net
- **Documentation**: https://docs.qnt9-srs.com
- **API Docs**: https://api.qnt9-srs.com/docs
- **Status Page**: https://status.qnt9-srs.com

<div align="center">
  
  **Built with ❤️ by the QNT9 Team**
  
  Star us on GitHub if you find this project useful!
  
</div>