# Search Service - Clean Architecture Dokumentation

## Architektur-Übersicht

### Schichtenmodell

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Presentation Layer                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ Search Router│  │ Health Router│  │ Metrics      │            │
│  │              │  │              │  │ Endpoint     │            │
│  │ - GET /search│  │ - /health    │  │ - /metrics   │            │
│  │ - POST /name │  │ - /ready     │  │              │            │
│  └──────┬───────┘  └──────────────┘  └──────────────┘            │
│         │                                                          │
└─────────┼──────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Layer                            │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │           StockSearchService (Business Logic)            │     │
│  │                                                          │     │
│  │  - Multi-Layer Caching Strategy                         │     │
│  │  - Search Orchestration                                 │     │
│  │  - Analytics & History Tracking                         │     │
│  └───────────┬──────────────────────────┬───────────────────┘     │
│              │                          │                          │
└──────────────┼──────────────────────────┼──────────────────────────┘
               │                          │
        ┌──────▼──────┐          ┌───────▼────────┐
        │             │          │                │
┌───────┴─────────────┴──────────┴────────────────┴─────────────────┐
│                     Repository Layer                              │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ IStockRepository│  │ ISymbolMapping   │  │ ISearchHistory  │ │
│  │   (Interface)   │  │   Repository     │  │   Repository    │ │
│  └────────┬────────┘  └─────────┬────────┘  └────────┬────────┘ │
│           │                     │                     │          │
│  ┌────────▼────────┐  ┌─────────▼────────┐  ┌────────▼────────┐ │
│  │ Redis           │  │ PostgreSQL       │  │ PostgreSQL      │ │
│  │ Repository      │  │ Symbol Mapping   │  │ History Repo    │ │
│  │                 │  │ Repository       │  │                 │ │
│  │ - Layer 1 Cache │  │ - ISIN→Symbol    │  │ - Analytics     │ │
│  │ - 5min TTL      │  │ - Persistent     │  │ - Autocomplete  │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │        PostgresStockRepository (Layer 2 Cache)           │   │
│  │        - Persistent Storage                              │   │
│  │        - 5min TTL                                        │   │
│  │        - Fuzzy Name Search                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
               │
               ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                           │
│                                                                   │
│  ┌──────────────────┐                                            │
│  │ IStockAPIClient  │  (Interface)                               │
│  └────────┬─────────┘                                            │
│           │                                                       │
│  ┌────────▼─────────────────────────────────────────────┐       │
│  │      YahooFinanceClient                              │       │
│  │                                                      │       │
│  │  ┌────────────────┐  ┌─────────────┐  ┌──────────┐ │       │
│  │  │ Circuit Breaker│  │ Rate Limiter│  │  Retry   │ │       │
│  │  │                │  │             │  │  Logic   │ │       │
│  │  │ - 5 failures   │  │ - 5 req/sec │  │ - 3 tries│ │       │
│  │  │ - 60s timeout  │  │ - Sliding   │  │ - Exp    │ │       │
│  │  │ - Half-open    │  │   window    │  │   backoff│ │       │
│  │  └────────────────┘  └─────────────┘  └──────────┘ │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  Future: AlphaVantageClient, OpenFIGIClient                      │
└───────────────────────────────────────────────────────────────────┘
               │
               ▼
┌───────────────────────────────────────────────────────────────────┐
│                        Domain Layer                               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Entities                                 │ │
│  │                                                             │ │
│  │  Stock (Aggregate Root)                                     │ │
│  │    ├── StockIdentifier (Value Object)                       │ │
│  │    │     ├── ISIN                                           │ │
│  │    │     ├── WKN                                            │ │
│  │    │     ├── Symbol                                         │ │
│  │    │     └── Name                                           │ │
│  │    ├── StockPrice (Value Object)                            │ │
│  │    │     ├── Current, Currency                              │ │
│  │    │     ├── Changes (%, absolute)                          │ │
│  │    │     ├── Day Range                                      │ │
│  │    │     └── 52-Week Range                                  │ │
│  │    └── StockMetadata (Value Object)                         │ │
│  │          ├── Exchange, Sector                               │ │
│  │          ├── Market Cap, PE Ratio                           │ │
│  │          └── Company Info                                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                Custom Exceptions                            │ │
│  │                                                             │ │
│  │  - StockNotFoundException                                   │ │
│  │  - InvalidIdentifierException                               │ │
│  │  - ExternalServiceException                                 │ │
│  │  - RateLimitExceededException                               │ │
│  │  - CircuitBreakerOpenException                              │ │
│  │  - CacheException                                           │ │
│  │  - ValidationException                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Request Flow - Multi-Layer Caching

```
┌─────────────┐
│   Client    │
│  Request    │
└──────┬──────┘
       │
       │ GET /api/v1/search?query=AAPL
       │
       ▼
┌──────────────────────────────────────┐
│      API Layer (Router)              │
│  - Input Validation                  │
│  - Pydantic Model                    │
└──────┬───────────────────────────────┘
       │
       │ StockSearchService.search("AAPL")
       │
       ▼
┌──────────────────────────────────────┐
│    Service Layer                     │
│  1. Detect Type → Symbol             │
│  2. Build Identifier                 │
│  3. Start Cache Lookup               │
└──────┬───────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│  Layer 1: Redis Cache                │
│                                      │
│  Key: stock:symbol:AAPL              │
│  TTL: 300s (5min)                    │
└──────┬───────────────────────────────┘
       │
       ├─ HIT? ──→ Return (50ms) ✓
       │
       └─ MISS ──→ Continue
                   │
                   ▼
       ┌──────────────────────────────────────┐
       │  Layer 2: PostgreSQL Cache           │
       │                                      │
       │  SELECT * FROM stock_cache           │
       │  WHERE symbol = 'AAPL'               │
       │  AND expires_at > NOW()              │
       └──────┬───────────────────────────────┘
              │
              ├─ HIT? ──→ Save to Redis ──→ Return (100ms) ✓
              │
              └─ MISS ──→ Continue
                          │
                          ▼
              ┌──────────────────────────────────────┐
              │  Layer 3: Yahoo Finance API          │
              │                                      │
              │  1. Check Circuit Breaker            │
              │  2. Check Rate Limit                 │
              │  3. Fetch with Retry                 │
              └──────┬───────────────────────────────┘
                     │
                     ├─ SUCCESS ──→ Save to PostgreSQL
                     │              Save to Redis
                     │              Return (2000ms) ✓
                     │
                     └─ FAILURE ──→ Circuit Breaker?
                                    Retry?
                                    404 Error ✗
```

## Dependency Injection Flow

```
┌────────────────────────────────────────────────────────────────┐
│                        app_v2.py                               │
│                     (Composition Root)                         │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Lifespan Startup
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  create_stock_service()                 │
        │                                         │
        │  1. Database Session → PostgreSQL       │
        │  2. Redis Client → Redis Connection     │
        │  3. Create Repositories                 │
        │  4. Create API Client                   │
        │  5. Wire into StockSearchService        │
        └─────────────────┬───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Redis Repo   │  │Postgres Repo │  │Yahoo Client  │
│              │  │              │  │              │
│ - Redis      │  │ - DB Session │  │ - Circuit B. │
│   Client     │  │              │  │ - Rate Limit │
└──────────────┘  └──────────────┘  └──────────────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
                          ▼
                ┌───────────────────┐
                │StockSearchService │
                │                   │
                │ All dependencies  │
                │ injected          │
                └─────────┬─────────┘
                          │
                          │ Registered as
                          │ FastAPI Dependency
                          │
                          ▼
                ┌───────────────────┐
                │   Router          │
                │   @router.get()   │
                │   Depends(...)    │
                └───────────────────┘
```

## Error Handling Strategy

```
┌──────────────────────────────────────────────────────────┐
│                    Error Types                           │
└──────────────────────────────────────────────────────────┘

Domain Exceptions (400-level)
├── ValidationException        → 400 Bad Request
├── InvalidIdentifierException → 400 Bad Request
└── StockNotFoundException     → 404 Not Found

Infrastructure Exceptions (500-level)
├── RateLimitExceededException      → 429 Too Many Requests
├── CircuitBreakerOpenException     → 503 Service Unavailable
├── ExternalServiceException        → 503 Service Unavailable
└── CacheException                  → 500 Internal Server Error
                                      (but don't fail request)

┌──────────────────────────────────────────────────────────┐
│              Error Propagation Flow                      │
└──────────────────────────────────────────────────────────┘

Infrastructure Layer
    │ Try Yahoo API Call
    ├─ Connection Timeout → ExternalServiceException
    ├─ Rate Limit Hit     → RateLimitExceededException
    └─ Circuit Open       → CircuitBreakerOpenException
            │
            ▼
Service Layer
    │ Catch Infrastructure Exceptions
    ├─ Retry with exponential backoff
    ├─ Try fallback sources (cache)
    └─ Convert to domain exceptions if needed
            │
            ▼
API Layer (Router)
    │ Catch All Exceptions
    ├─ Map to HTTP Status Codes
    ├─ Build ErrorResponse
    ├─ Add Retry-After headers
    └─ Return JSON Error
```

## Monitoring & Observability

```
┌──────────────────────────────────────────────────────────┐
│                  Logging Strategy                        │
└──────────────────────────────────────────────────────────┘

Structured JSON Logging (structlog)

Example Log Entry:
{
  "event": "stock_search",
  "level": "info",
  "timestamp": "2025-11-10T10:30:45.123Z",
  "request_id": "req-abc123",
  "query": "AAPL",
  "query_type": "symbol",
  "cache_source": "redis",
  "latency_ms": 45,
  "found": true
}

Log Levels:
- DEBUG: Cache hits/misses, detailed flow
- INFO:  Successful operations, cache source
- WARNING: Rate limits, circuit breaker state
- ERROR: API failures, exceptions

┌──────────────────────────────────────────────────────────┐
│              Prometheus Metrics                          │
└──────────────────────────────────────────────────────────┘

Counters:
- search_service_requests_total{method, endpoint, status}
- search_service_cache_hits_total{cache_layer}
- search_service_api_calls_total{service, status}

Histograms:
- search_service_request_latency_seconds{method, endpoint}
- search_service_cache_latency_seconds{cache_layer}

Gauges:
- search_service_circuit_breaker_state{service}
- search_service_cache_size{layer}

┌──────────────────────────────────────────────────────────┐
│                 Health Checks                            │
└──────────────────────────────────────────────────────────┘

/api/v1/health (Liveness Probe)
├── Returns 200 if process alive
└── Used by Load Balancer

/api/v1/ready (Readiness Probe)
├── Check PostgreSQL connection
├── Check Redis connection (optional)
├── Check Circuit Breaker states
└── Returns 200 if ready, 503 if not

/metrics (Prometheus)
├── Scrape endpoint for metrics
└── Called by Prometheus every 15s
```

## Security Considerations

```
┌──────────────────────────────────────────────────────────┐
│                Input Validation                          │
└──────────────────────────────────────────────────────────┘

1. Pydantic Models
   - Type validation
   - Length constraints (1-100 chars)
   - Pattern matching (regex)

2. Sanitization
   - Strip whitespace
   - Uppercase normalization for identifiers
   - Reject empty/malformed input

3. SQL Injection Prevention
   - SQLAlchemy ORM (parameterized queries)
   - No raw SQL with user input

┌──────────────────────────────────────────────────────────┐
│                  CORS & Security                         │
└──────────────────────────────────────────────────────────┘

CORS Configuration:
- Whitelist allowed origins
- No credentials for public API
- Restrict methods if needed

Request Limits:
- Max query length: 100 chars
- Rate limiting (future): 100 req/min per IP

Logging:
- No user data in logs (GDPR)
- No API keys in logs
- Sanitize error messages

Future:
- API Key Authentication
- JWT Token Validation
- Request Signing
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Deployment                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────┐
│   Ingress   │  (HTTPS, TLS Termination)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Load Balancer   │  (Round Robin)
└──────┬───────────┘
       │
       ├─────────────┬─────────────┬──────────────┐
       │             │             │              │
       ▼             ▼             ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Pod 1    │  │ Pod 2    │  │ Pod 3    │  │ Pod N    │
│          │  │          │  │          │  │          │
│ Search   │  │ Search   │  │ Search   │  │ Search   │
│ Service  │  │ Service  │  │ Service  │  │ Service  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │              │
     └─────────────┴─────────────┴──────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌───────────────┐      ┌──────────────┐
│ Redis Cluster │      │ PostgreSQL   │
│               │      │              │
│ - Master      │      │ - Primary    │
│ - Replicas    │      │ - Read Reps  │
└───────────────┘      └──────────────┘

Auto-Scaling:
- HPA based on CPU/Memory
- Min: 2 replicas
- Max: 10 replicas
- Target CPU: 70%

Health Checks:
- Liveness:  /api/v1/health
- Readiness: /api/v1/ready
```

---

**Last Updated**: 2025-11-10  
**Architecture Version**: 2.0
