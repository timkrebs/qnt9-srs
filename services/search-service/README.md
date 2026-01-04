# Search Service v2.0 - Clean Architecture

## Übersicht

Robuster Microservice für Aktiensuche mit Clean Architecture, Multi-Layer Caching, Circuit Breaker Pattern und umfassendem Monitoring.

## Architektur

### Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (Routers)                  │
│  - FastAPI Router für HTTP Endpoints                   │
│  - Request/Response Validation (Pydantic)               │
│  - Error Handling & HTTP Status Codes                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Service Layer (Business Logic)         │
│  - StockSearchService: Orchestrierung                   │
│  - Multi-Layer Caching Strategie                        │
│  - Search History & Analytics                           │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              Repository Layer (Data Access)             │
│  - IStockRepository (Interface)                         │
│  - PostgresStockRepository (Persistent Cache)           │
│  - RedisStockRepository (In-Memory Cache)               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│          Infrastructure Layer (External Services)       │
│  - IStockAPIClient (Interface)                          │
│  - YahooFinanceClient (Implementation)                  │
│  - Circuit Breaker & Rate Limiter                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 Domain Layer (Core Business)            │
│  - Entities: Stock, StockIdentifier, StockPrice         │
│  - Value Objects: StockMetadata                         │
│  - Custom Exceptions                                    │
└─────────────────────────────────────────────────────────┘
```

### Dateistruktur

```
app/
├── domain/                    # Domain Layer (Geschäftslogik)
│   ├── entities.py           # Stock, StockIdentifier, StockPrice, StockMetadata
│   └── exceptions.py         # Custom Exceptions
│
├── infrastructure/           # Infrastructure Layer (Externe Services)
│   ├── stock_api_client.py  # Interface für API Clients
│   ├── yahoo_finance_client.py  # Yahoo Finance Implementation
│   ├── circuit_breaker.py   # Circuit Breaker Pattern
│   └── rate_limiter.py      # Rate Limiting
│
├── repositories/             # Repository Layer (Datenzugriff)
│   ├── stock_repository.py  # Repository Interfaces
│   ├── postgres_repository.py  # PostgreSQL Implementation
│   └── redis_repository.py  # Redis Implementation
│
├── services/                 # Service Layer (Business Logic)
│   └── stock_service.py     # StockSearchService
│
├── routers/                  # API Layer (HTTP Endpoints)
│   ├── search_router.py     # Search Endpoints
│   └── health_router.py     # Health & Monitoring
│
├── models.py                 # SQLAlchemy Models (alt, für Migration)
├── database.py               # Database Configuration
├── app_v2.py                # Neue Main Application
└── app.py                    # Alte Main Application (deprecated)
```

## Features

### Implementiert

#### 1. **Multi-Layer Caching**
- **Layer 1 (Redis)**: In-Memory Cache, 5 Minuten TTL
- **Layer 2 (PostgreSQL)**: Persistent Cache, 5 Minuten TTL
- **Cache-Key-Strategie**: `stock:{type}:{normalized_value}`
- **Automatische Invalidierung**: TTL-basiert

#### 2. **Intelligente Erkennung**
- Automatische Erkennung von ISIN, WKN, Symbol oder Name
- Regex-basierte Validierung
- Input Sanitization & Normalisierung

#### 3. **Fault Tolerance**
- **Circuit Breaker**: Schützt vor kaskadenförmigen Fehlern
  - 5 Fehler → Circuit öffnet
  - 60 Sekunden Recovery Timeout
  - Half-Open State für Wiederherstellung
- **Retry Logic**: Exponential Backoff (3 Versuche)
- **Rate Limiting**: 5 Requests/Sekunde pro Service
- **Graceful Degradation**: Fallback auf gecachte Daten

#### 4. **Monitoring & Observability**
- **Strukturiertes Logging**: JSON-Format mit structlog
- **Prometheus Metriken**:
  - Request Count & Latency
  - Cache Hit Rates
  - API Success/Failure Rates
- **Health Checks**: `/api/v1/health`, `/api/v1/ready`
- **Request-ID Tracing**: Durchgängige Request-IDs

#### 5. **Security**
- Input Validation mit Pydantic
- SQL Injection Prevention (SQLAlchemy ORM)
- CORS Konfiguration
- Request Size Limits
- Keine sensitiven Daten in Logs

## API Endpoints

### Search Endpoints

#### GET `/api/v1/search`
Suche nach Aktie mit ISIN, WKN, Symbol oder Name.

**Query Parameter:**
- `query` (string, required): ISIN, WKN, Symbol oder Name

**Response:**
```json
{
  "success": true,
  "data": {
    "identifier": {
      "isin": "US0378331005",
      "wkn": "865985",
      "symbol": "AAPL",
      "name": "Apple Inc."
    },
    "price": {
      "current": 175.50,
      "currency": "USD",
      "change_percent": 1.25
    },
    "metadata": {
      "exchange": "NASDAQ",
      "sector": "Technology",
      "market_cap": 2800000000000
    }
  },
  "message": "Stock found successfully",
  "cache_source": "redis"
}
```

#### POST `/api/v1/search/name`
Fuzzy Suche nach Firmennamen.

**Request Body:**
```json
{
  "name": "Apple",
  "limit": 10
}
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "results": [...]
}
```

#### GET `/api/v1/stats/cache`
Cache Statistiken abrufen.

**Response:**
```json
{
  "redis": {
    "total_stock_keys": 150,
    "hit_rate": 85.5
  },
  "postgresql": {
    "valid_entries": 500,
    "total_hits": 12500
  },
  "external_api": {
    "circuit_breaker": {
      "state": "closed",
      "failure_count": 0
    }
  }
}
```

### Health & Monitoring

#### GET `/api/v1/health`
Liveness Probe für Load Balancer.

#### GET `/api/v1/ready`
Readiness Probe für Kubernetes.

#### GET `/metrics`
Prometheus Metriken.

## Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+ (optional, aber empfohlen)

### Environment Variables

Erstelle eine `.env` Datei:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/qnt9_search

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# API Settings
YAHOO_FINANCE_TIMEOUT=5.0
CACHE_TTL_MINUTES=5
```

### Installation

```bash
# 1. Dependencies installieren
pip install -r requirements.txt

# 2. Database migrieren
alembic upgrade head

# 3. Service starten
python -m app.app_v2

# Oder mit uvicorn:
uvicorn app.app_v2:app --reload --host 0.0.0.0 --port 8000
```

### Mit Docker

```bash
# Build
docker build -t qnt9-search-service .

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  qnt9-search-service
```

## Testing

```bash
# Unit Tests
pytest tests/ -v

# Mit Coverage
pytest tests/ --cov=app --cov-report=html

# Integration Tests
pytest tests/integration/ -v

# Nur Domain Layer Tests
pytest tests/domain/ -v
```

## Performance

### Response Time Ziele
- **Cache Hit (Redis)**: < 50ms
- **Cache Hit (PostgreSQL)**: < 100ms
- **API Call**: < 2000ms
- **P95 Latency**: < 500ms

### Caching Strategie

1. **Request kommt rein**
2. **Check Redis** (Layer 1)
   - Hit? → Return (schnell!)
   - Miss? → Weiter
3. **Check PostgreSQL** (Layer 2)
   - Hit? → Save to Redis → Return
   - Miss? → Weiter
4. **Yahoo Finance API** (Layer 3)
   - Success? → Save to PostgreSQL & Redis → Return
   - Failure? → Check Circuit Breaker → Retry

### Rate Limits

- **Yahoo Finance**: 5 req/sec
- **Per Client IP**: 100 req/min (TODO: Implementieren mit Redis)

## Migration von v1 zu v2

Die alte `app.py` ist noch verfügbar, aber deprecated. Um auf v2 zu migrieren:

1. **Testen**: Teste die neue API mit `/api/docs`
2. **Environment**: Prüfe `.env` Variablen
3. **Redis**: Optional, aber stark empfohlen
4. **Switch**: Ändere Startup Command auf `app.app_v2:app`

## Entwicklung

### Neue Funktionen hinzufügen

1. **Domain Entities** in `domain/entities.py` definieren
2. **Repository Interface** in `repositories/stock_repository.py` erweitern
3. **Repository Implementation** in Postgres/Redis Repositories
4. **Service Logic** in `services/stock_service.py` implementieren
5. **Router Endpoint** in `routers/` erstellen
6. **Tests** schreiben

### Logging

Strukturiertes JSON-Logging mit Kontext:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("Stock fetched", symbol="AAPL", source="redis", latency_ms=45)
```

### Metriken

Prometheus Counter/Histogram nutzen:

```python
from prometheus_client import Counter

MY_COUNTER = Counter('my_metric_total', 'Description', ['label'])
MY_COUNTER.labels(label='value').inc()
```

## TODO / Roadmap

- [x] OpenFIGI Integration für ISIN/WKN → Symbol Mapping (Implemented as SymbolMapping)
- [x] Distributed Rate Limiting mit Redis (Phase 1 Complete)
- [x] Enhanced Security Middleware (OWASP Headers, Input Validation)
- [x] SLO Tracking and Observability (Prometheus + Custom Metrics)
- [ ] API Key Authentication Enhancement
- [ ] Batch Request Endpoint
- [ ] Meilisearch for Autocomplete (<100ms target)
- [ ] WebSocket für Realtime Updates
- [ ] GraphQL API

## Recent Changes

### v2.3.0 - Production Readiness (2024)

**Production-Ready Improvements:**

1. **Redis Connection Management**
   - Singleton connection manager with pooling (max 50 connections)
   - Exponential backoff retry logic
   - Health checks and diagnostics
   - Graceful connection handling

2. **Security Middleware**
   - OWASP security headers (X-Content-Type-Options, CSP, HSTS)
   - Request validation (size limits, SQL injection protection, XSS protection)
   - CORS configuration with environment-based origins
   - Input sanitization

3. **Distributed Rate Limiting**
   - Redis-backed rate limiter with sliding window algorithm
   - Tier-based limits (Anonymous: 10/min, Free: 30/min, Paid: 100/min, Enterprise: 1000/min)
   - Automatic fallback to local rate limiting
   - Rate limit headers in API responses

4. **Enhanced Observability**
   - Search-specific Prometheus metrics (latency, cache hits, result counts)
   - SLO tracking (P95/P99 latency, error rate, availability)
   - Error budget monitoring
   - Comprehensive logging and tracing

5. **Infrastructure Updates**
   - Dependency injection for Redis client
   - Application lifespan management
   - Graceful shutdown with cleanup
   - Backward compatible changes

**Configuration:**
```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_MAX_CONNECTIONS=50

# Security
CORS_ALLOWED_ORIGINS=http://localhost:3000
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting (optional overrides)
RATE_LIMIT_ANONYMOUS=10
RATE_LIMIT_FREE=30
RATE_LIMIT_PAID=100
```

**See Also:**
- `PRODUCTION_READINESS_IMPLEMENTATION.md` - Complete implementation details
- `PRODUCTION_PLAN.md` - 4-phase implementation plan

### v2.2.0 - Performance Refactoring (2025-11-11)

**Major Refactoring:**
- Removed 1,890 lines of legacy code (-56%)
- Simplified database configuration (-49%)
- Removed complex Supabase/Vault fallback logic
- Streamlined to pure Clean Architecture

**Removed Files:**
- `cache.py` (938 lines) - Replaced by Clean Architecture repositories
- `validators.py` (654 lines) - Moved to domain layer & Pydantic models
- `supabase_config.py` (148 lines) - Simplified to DATABASE_URL env var
- `vault_kv.py` (150 lines) - Use standard secrets management

**Performance Improvements:**
- 47% faster startup time
- 33% less memory usage
- Simpler, more maintainable code
- Better testability

**See Also:**
- `REFACTORING.md` - Detailed refactoring documentation

### v2.1.0 - Yahoo Finance Only (2025-11-11)

**Breaking Changes:**
- Removed Alpha Vantage dependency completely
- Now uses only Yahoo Finance API for all searches

**Improvements:**
- Enhanced ISIN/WKN resolution using Yahoo Search API
- Improved name search with 3-tier fallback strategy
- Better identifier detection (supports 1-10 char symbols)
- Simplified architecture and reduced dependencies

**See Also:**
- `test_search_improvements.py` - Validation script

## License

MIT

## Contributors

QNT9 Development Team

---

**Version**: 2.3.0  
**Last Updated**: 2024