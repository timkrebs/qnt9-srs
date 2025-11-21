# User Service

User profile management service with tier-based access control and Stripe subscription integration.

## Features

- User profile management (CRUD operations)
- Tier management (free/paid/enterprise)
- Stripe subscription integration
- Subscription lifecycle tracking
- JWT authentication
- Prometheus metrics
- Health checks

## Architecture

```
User Service (Port 8011)
    ├── FastAPI Application
    ├── PostgreSQL Database (via Supabase)
    ├── JWT Authentication
    └── Stripe Webhook Integration
```

## API Endpoints

### User Management

#### GET /users/{user_id}
Get user profile with tier and subscription information.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "tier": "paid",
  "subscription_start": "2025-01-01T00:00:00Z",
  "subscription_end": "2026-01-01T00:00:00Z",
  "stripe_customer_id": "cus_xxx",
  "stripe_subscription_id": "sub_xxx",
  "last_login": "2025-11-20T10:00:00Z",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /users/{user_id}/upgrade
Upgrade user to paid tier.

**Request:**
```json
{
  "plan": "monthly",
  "payment_method_id": "pm_xxx"
}
```

**Response:**
```json
{
  "success": true,
  "tier": "paid",
  "subscription_end": "2026-01-01T00:00:00Z",
  "stripe_subscription_id": "sub_xxx"
}
```

#### POST /users/{user_id}/downgrade
Downgrade user to free tier.

**Response:**
```json
{
  "success": true,
  "tier": "free",
  "subscription_end": null
}
```

#### PATCH /users/{user_id}/last-login
Update user's last login timestamp.

**Response:**
```json
{
  "success": true,
  "last_login": "2025-11-20T10:00:00Z"
}
```

#### GET /users/{user_id}/tier
Get user's current tier and subscription status.

**Response:**
```json
{
  "tier": "paid",
  "subscription_active": true,
  "subscription_end": "2026-01-01T00:00:00Z",
  "days_remaining": 365
}
```

#### GET /users/{user_id}/stats
Get user usage statistics.

**Response:**
```json
{
  "watchlist_count": 10,
  "predictions_requested": 150,
  "last_prediction_at": "2025-11-20T09:00:00Z",
  "account_age_days": 90
}
```

### Health & Monitoring

#### GET /health
Service health check.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-11-20T10:00:00Z"
}
```

#### GET /metrics
Prometheus metrics endpoint.

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres-users:5432/qnt9_users

# Stripe
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Service Configuration
SERVICE_PORT=8011
LOG_LEVEL=INFO

# JWT Authentication
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=RS256
```

## Database Schema

### users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'free',
    subscription_start TIMESTAMP,
    subscription_end TIMESTAMP,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tier ON users(tier);
CREATE INDEX idx_users_stripe_customer ON users(stripe_customer_id);
```

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start service
uvicorn app.main:app --reload --port 8011
```

### Testing

```bash
# Run tests
pytest tests/ --cov=app --cov-report=html

# Run specific test
pytest tests/test_user_service.py::test_upgrade_user -v
```

### Docker

```bash
# Build image
docker build -t user-service:latest .

# Run container
docker run -p 8011:8011 \
    -e DATABASE_URL=postgresql://... \
    -e STRIPE_SECRET_KEY=sk_test_... \
    user-service:latest
```

## Stripe Integration

### Webhook Events

The service handles the following Stripe webhook events:

- `customer.subscription.created` - New subscription created
- `customer.subscription.updated` - Subscription updated
- `customer.subscription.deleted` - Subscription cancelled
- `invoice.payment_succeeded` - Payment successful
- `invoice.payment_failed` - Payment failed

### Subscription Plans

| Plan | Price | Interval | Features |
|------|-------|----------|----------|
| Free | $0 | - | 3 stocks in watchlist |
| Monthly | $10 | month | Unlimited watchlist + ML predictions |
| Annual | $100 | year | Unlimited watchlist + ML predictions (2 months free) |

## Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid JWT token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - User not found
- `409 Conflict` - Duplicate email or subscription conflict
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "detail": "Error message",
  "error_code": "USER_NOT_FOUND",
  "timestamp": "2025-11-20T10:00:00Z"
}
```

## Monitoring

### Prometheus Metrics

- `user_service_requests_total` - Total API requests
- `user_service_request_duration_seconds` - Request latency
- `user_service_upgrades_total` - Total tier upgrades
- `user_service_downgrades_total` - Total tier downgrades
- `user_service_active_subscriptions` - Current active paid subscriptions

### Logging

Structured logging with `structlog`:

```python
logger.info(
    "user_upgraded",
    user_id=str(user_id),
    tier="paid",
    plan="monthly",
    subscription_id="sub_xxx"
)
```

## Security

- JWT authentication required for all endpoints
- Stripe webhook signature verification
- SQL injection prevention via parameterized queries
- Input validation with Pydantic models
- Rate limiting (100 requests/minute)

## Performance

- Database connection pooling (10-20 connections)
- Response caching for tier lookups
- Async I/O operations
- Target latency: <100ms P99

## Deployment

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
      - name: user-service
        image: user-service:latest
        ports:
        - containerPort: 8011
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        - name: STRIPE_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: stripe-secret
              key: secret_key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8011
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8011
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Troubleshooting

### Common Issues

**Issue: Database connection failed**
```bash
# Check database connectivity
psql -U postgres -h postgres-users -d qnt9_users -c "SELECT 1"

# Check environment variables
echo $DATABASE_URL
```

**Issue: Stripe webhook verification failed**
```bash
# Verify webhook secret
curl -X POST http://localhost:8011/stripe/webhook \
    -H "Stripe-Signature: xxx" \
    -d @webhook_payload.json

# Check Stripe webhook logs in dashboard
```

**Issue: User upgrade failed**
```bash
# Check Stripe API logs
# Verify payment method is valid
# Check subscription creation in Stripe dashboard
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/qnt9-srs/issues
- Documentation: https://docs.qnt9-srs.com/user-service
- Email: support@qnt9-srs.com

## License

MIT License - see LICENSE file for details
