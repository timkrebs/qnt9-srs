# QNT9 Search Service

Stock search microservice for the QNT9 Stock Recommendation System. Provides ISIN, WKN, and symbol-based stock search with intelligent caching and multi-API support.

## Features

- **Multi-format Search**: Support for ISIN (12-char), WKN (6-char), and standard ticker symbols
- **Input Validation**: Regex-based validation with ISIN checksum verification
- **Intelligent Caching**: PostgreSQL-based caching with 5-minute TTL
- **Multi-API Support**: Yahoo Finance (primary) with Alpha Vantage fallback
- **Performance**: Sub-2-second response times with rate limiting
- **Analytics**: Search history tracking and autocomplete suggestions
- **Security**: HashiCorp Vault integration for secrets management
- **Cloud-Ready**: Docker support with Azure deployment configuration

## Architecture

```
search-service/
├── app/
│   ├── app.py           # Main FastAPI application
│   ├── models.py        # SQLAlchemy database models
│   ├── database.py      # Database connection & Vault integration
│   ├── vault_kv.py      # Vault KV credential retrieval
│   ├── validators.py    # Pydantic models & input validation
│   ├── cache.py         # Cache management layer
│   └── api_clients.py   # External API clients (Yahoo/Alpha Vantage)
├── tests/
│   ├── conftest.py      # Test fixtures
│   ├── test_api.py      # API integration tests
│   ├── test_cache.py    # Cache unit tests
│   └── test_validators.py # Validation tests
├── requirements.txt
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## API Endpoints

### Stock Search
```http
GET /api/stocks/search?query={isin|wkn|symbol}
```

**Examples:**
```bash
# Search by ISIN
curl "http://localhost:8000/api/stocks/search?query=US0378331005"

# Search by WKN
curl "http://localhost:8000/api/stocks/search?query=865985"

# Search by Symbol
curl "http://localhost:8000/api/stocks/search?query=AAPL"
```

**Response:**
```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "isin": "US0378331005",
    "wkn": "865985",
    "current_price": 175.50,
    "currency": "USD",
    "exchange": "NASDAQ",
    "market_cap": 2800000000000,
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "source": "yahoo",
    "cached": false,
    "cache_age_seconds": 0
  },
  "message": "Data retrieved from external API",
  "query_type": "isin",
  "response_time_ms": 856
}
```

### Autocomplete Suggestions
```http
GET /api/stocks/suggestions?query={prefix}&limit=5
```

### Cache Management
```http
GET /api/cache/stats        # Get cache statistics
POST /api/cache/cleanup     # Remove expired entries
```

### Health Checks
```http
GET /                       # Service info
GET /health                 # Health check
GET /api/docs              # Interactive API documentation (Swagger)
GET /api/redoc             # Alternative API documentation (ReDoc)
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (production) or SQLite (local dev)
- Optional: HashiCorp Vault for production credentials
- Optional: Alpha Vantage API key (defaults to demo key)

### Local Development (SQLite)

1. **Install dependencies:**
   ```bash
   cd services/search-service
   pip install -r requirements.txt
   ```

2. **Run the service:**
   ```bash
   make fastapi-dev
   ```
   Service will be available at `http://localhost:8000`

3. **View API documentation:**
   Open `http://localhost:8000/api/docs`

### Local Development (PostgreSQL)

1. **Set environment variable:**
   ```bash
   export USE_LOCAL_DB=true
   export DATABASE_URL="postgresql://srs_admin:password@localhost:5432/srs_db"
   ```

2. **Run the service:**
   ```bash
   make fastapi-dev
   ```

### Production (with Vault)

1. **Configure Vault environment:**
   ```bash
   export VAULT_ADDR="https://your-vault-instance.com"
   export VAULT_TOKEN="your-token"
   export VAULT_NAMESPACE="admin"
   ```

2. **Optional: Alpha Vantage API key:**
   ```bash
   export ALPHA_VANTAGE_API_KEY="your-api-key"
   ```

3. **Run the service:**
   ```bash
   make fastapi-dev
   ```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `USE_LOCAL_DB` | Use local PostgreSQL instead of Vault | `false` | No |
| `DATABASE_URL` | Database connection string | `sqlite:///./search_service.db` | No |
| `VAULT_ADDR` | HashiCorp Vault address | - | Production |
| `VAULT_TOKEN` | Vault authentication token | - | Production |
| `VAULT_NAMESPACE` | Vault namespace | `admin` | Production |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | `demo` | No |

## Database Connection Logic

The service implements a three-tier fallback strategy:

1. **Vault KV** (Production): Fetch credentials from `kv/data/database/qnt9-srs`
2. **Environment Variable**: Use `DATABASE_URL` if Vault unavailable
3. **SQLite Fallback**: Local `search_service.db` for development

```python
# Connection priority
if USE_LOCAL_DB:
    → PostgreSQL (local)
elif Vault available:
    → PostgreSQL (production via Vault)
else:
    → SQLite (development)
```

## Testing

### Run all tests:
```bash
make test
```

### Run with coverage:
```bash
make test-cov
```

Coverage report will be generated in `htmlcov/index.html`

### Test structure:
- `test_validators.py`: Input validation logic (ISIN/WKN/symbol)
- `test_cache.py`: Cache management and TTL behavior
- `test_api.py`: API endpoints and acceptance criteria

**Target Coverage:** >80% (enforced in `pyproject.toml`)

## API Rate Limits

The service implements intelligent rate limiting for external APIs:

| API | Rate Limit | Window | Handling |
|-----|------------|--------|----------|
| Yahoo Finance | 5 requests/sec | 1 second | Auto-throttle with exponential backoff |
| Alpha Vantage | 5 requests/min | 60 seconds | Fallback only when Yahoo fails |

**Note:** Alpha Vantage free tier limits to 5 requests/minute. Consider upgrading for production.

## Caching Strategy

- **Storage**: PostgreSQL (production) or SQLite (development)
- **TTL**: 5 minutes
- **Invalidation**: Automatic on expiry
- **Hit Tracking**: Records cache hits for analytics
- **Cleanup**: Manual via `/api/cache/cleanup` or automatic on query

## Validation Rules

### ISIN Format
- Length: 12 characters
- Pattern: `[A-Z]{2}[A-Z0-9]{9}[0-9]`
- Checksum: Luhn algorithm validation
- Example: `US0378331005` (Apple)

### WKN Format
- Length: 6 characters
- Pattern: `[A-Z0-9]{6}`
- Example: `865985` (Apple)

### Symbol Format
- Length: 1-10 characters
- Pattern: `[A-Z0-9\.\-]{1,10}`
- Example: `AAPL`, `BRK.B`

## Docker Deployment

### Build image:
```bash
make docker-build
```

### Run container:
```bash
make docker-run
```

Container runs on port 8001 (mapped to internal 8000).

### Environment variables for Docker:
```bash
docker run -d \
  -p 8001:8000 \
  -e VAULT_ADDR="https://vault.example.com" \
  -e VAULT_TOKEN="your-token" \
  -e ALPHA_VANTAGE_API_KEY="your-key" \
  --name search-service \
  search-service
```

## Monitoring & Observability

### Datadog APM (Optional)

Run with Datadog instrumentation:
```bash
make fastapi-dev-dd
```

Requires Datadog agent running on `localhost:8126`.

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Cache statistics
curl http://localhost:8000/api/cache/stats
```

## Acceptance Criteria

- [x] **AC1**: Valid ISIN search returns stock with name, ISIN, WKN, price, symbol (<2s)
- [x] **AC2**: Valid WKN search returns matching stock
- [x] **AC3**: Invalid format shows validation error without API call
- [x] **AC4**: Stock not found shows friendly message with suggestions
- [x] **AC5**: Cached data served within 5 minutes without external API call

## Development Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/search-service-enhancement
   ```

2. **Make changes and test:**
   ```bash
   make test-cov
   ```

3. **Format code:**
   ```bash
   black app/ tests/
   isort app/ tests/
   ```

4. **Commit following convention:**
   ```bash
   git commit -m "feat(search): add WKN to ISIN mapping"
   ```

5. **Push and create PR:**
   ```bash
   git push origin feature/search-service-enhancement
   ```

## Troubleshooting

### Database connection fails
- **Vault credentials**: Check `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_NAMESPACE`
- **Local dev**: Set `USE_LOCAL_DB=true` and verify `DATABASE_URL`
- **SQLite fallback**: Service will use `search_service.db` automatically

### API rate limits exceeded
- Check cache statistics: `GET /api/cache/stats`
- Manually cleanup expired entries: `POST /api/cache/cleanup`
- Consider increasing TTL (current: 5 minutes)

### Tests failing
- Ensure SQLite is available (no external dependencies)
- Run `pytest -v` for detailed output
- Check test fixtures in `tests/conftest.py`

### Datadog APM not working
- This is normal for local development
- Agent connection errors are gracefully handled
- Use `make fastapi-dev` instead of `make fastapi-dev-dd` for local work

## API Documentation

Full interactive API documentation available at:
- **Swagger UI**: `http://localhost:8000/api/docs`
- **ReDoc**: `http://localhost:8000/api/redoc`
- **OpenAPI Schema**: `http://localhost:8000/api/openapi.json`

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for:
- Code style guidelines (Black, isort, mypy)
- Testing requirements (>80% coverage)
- Commit message conventions
- PR process and review checklist

## License

See [LICENSE](../../LICENSE) file in repository root.

## Support

For issues or questions:
1. Check [MicroserviceArchitecture.md](../../docs/MicroserviceArchitecture.md)
2. Review service logs
3. Create GitHub issue with:
   - Environment details
   - Error messages
   - Steps to reproduce

## Related Services

- **auth-service**: User authentication (port 8000)
- **analysis-service**: Stock analysis (port 8002)
- **data-ingestion-service**: Data pipeline (port 8003)

---

**Version:** 1.0.0  
**Status:** Production Ready
**Last Updated:** October 29, 2025
