# Finio Auth Service

Modern authentication service using **Supabase Auth** for the Finio Stock Research System.

## Features

**Supabase Integration**
- Secure user authentication via Supabase Auth
- Email/password authentication
- JWT-based session management
- Password reset functionality

**Security**
- Industry-standard security practices
- Secure password hashing (handled by Supabase)
- JWT token-based authentication
- CORS protection

**API Endpoints**
- User registration (`/auth/signup`)
- User login (`/auth/signin`)
- User logout (`/auth/signout`)
- Profile management (`/auth/me`)
- Password updates
- Session refresh

## Architecture

```
auth-service/
├── app/
│   ├── __init__.py
│   ├── app.py                 # FastAPI application
│   ├── auth_service.py        # Supabase auth business logic
│   ├── config.py              # Configuration management
│   ├── logging_config.py      # Logging setup
│   ├── models.py              # Pydantic models
│   └── supabase_client.py     # Supabase client setup
├── tests/
│   └── test_auth.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── Makefile
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (provided by Supabase)
- Supabase account ([supabase.com](https://supabase.com))
- Redis (optional, for rate limiting)

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Database Configuration
DATABASE_URL=postgresql://user:password@host:5432/database

# Service Configuration
SERVICE_NAME=auth-service
ENVIRONMENT=development
LOG_LEVEL=INFO
```

3. **Run database migrations:**
```bash
# Apply Supabase migrations
psql $DATABASE_URL < ../../supabase/migrations/001_initial_schema.sql
```

4. **Start the service:**
```bash
# Development mode
uvicorn app.app:app --reload --port 8001

# Production mode
uvicorn app.app:app --host 0.0.0.0 --port 8001 --workers 4

# Using Docker
docker-compose up auth-service

# Using Make
make run
```

## Supabase Configuration

### Required Settings

Get your Supabase credentials from your project dashboard:

1. **Project URL** (`SUPABASE_URL`)
   - Settings → API → Project URL
   - Format: `https://your-project.supabase.co`

2. **Anon/Public Key** (`SUPABASE_KEY`)
   - Settings → API → Project API keys → `anon` `public`
   - Used for client-side operations

3. **Service Role Key** (`SUPABASE_SERVICE_ROLE_KEY`)
   - Settings → API → Project API keys → `service_role` `secret`
   - Used for admin operations (keep secure!)

4. **JWT Secret** (`SUPABASE_JWT_SECRET`)
   - Settings → API → JWT Settings → JWT Secret
   - Used for token validation

### Authentication Settings

1. Go to **Authentication** → **Providers**
2. Enable **Email** provider
3. Configure email templates:
   - Confirmation email
   - Password reset email
   - Magic link email (optional)
4. Set **Site URL** and **Redirect URLs** for your frontend

## API Documentation

Complete API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the service is running.

### Authentication Endpoints

#### Sign Up
```bash
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "tier": "free"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "email_confirmed_at": null,
    "tier": "free",
    "user_metadata": {},
    "app_metadata": {
      "provider": "email",
      "providers": ["email"]
    },
    "created_at": "2024-01-01T00:00:00Z"
  },
  "session": {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "expires_in": 3600,
    "expires_at": 1704067200,
    "token_type": "bearer"
  }
}
```

#### Sign In
```bash
POST /api/v1/auth/signin
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "email_confirmed_at": "2024-01-01T00:00:00Z",
    "tier": "free"
  },
  "session": {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "expires_in": 3600,
    "expires_at": 1704067200,
    "token_type": "bearer"
  }
}
```

#### Refresh Session
```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 3600,
  "expires_at": 1704067200,
  "token_type": "bearer"
}
```

#### Sign Out
```bash
POST /api/v1/auth/signout
Authorization: Bearer eyJhbGc...
```

**Response (200 OK):**
```json
{
  "message": "Successfully signed out"
}
```

### User Management Endpoints

#### Get Current User
```bash
GET /api/v1/users/me
Authorization: Bearer eyJhbGc...
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "email_confirmed_at": "2024-01-01T00:00:00Z",
  "tier": "free",
  "user_metadata": {},
  "app_metadata": {
    "provider": "email"
  },
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Update Current User
```bash
PATCH /api/v1/users/me
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "email": "newemail@example.com",
  "password": "NewSecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "newemail@example.com",
  "email_confirmed_at": null,
  "tier": "free"
}
```

#### Get User Tier
```bash
GET /api/v1/users/me/tier
Authorization: Bearer eyJhbGc...
```

**Response (200 OK):**
```json
{
  "tier": "premium"
}
```

#### Update User Tier
```bash
PUT /api/v1/users/me/tier
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "tier": "premium"
}
```

**Response (200 OK):**
```json
{
  "tier": "premium"
}
```

#### Request Password Reset
```bash
POST /api/v1/users/password-reset
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "Password reset email sent successfully"
}
```

### Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

Common HTTP status codes:
- `400 Bad Request` - Invalid input or validation error
- `401 Unauthorized` - Missing or invalid authentication token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - User already exists
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_supabase_auth.py

# Using Make
make test
make test-cov
```

### Code Quality

```bash
# Format code with black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Lint with flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/

# Using Make
make format
make lint
```

## Integration with Other Services

### Token Validation

Other services can validate Supabase JWTs using the shared JWT secret:

```python
from app.security import validate_supabase_jwt, extract_user_from_supabase_token

# Validate token
claims = validate_supabase_jwt(token)
if claims:
    user_info = extract_user_from_supabase_token(token)
    user_id = user_info["id"]
    user_email = user_info["email"]
```

### Example: Using Auth in Another Service

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.security import validate_supabase_jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    claims = validate_supabase_jwt(token)
    
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return {
        "id": claims.get("sub"),
        "email": claims.get("email"),
        "role": claims.get("role")
    }

# Use in endpoint
@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user_id": user["id"], "email": user["email"]}
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SUPABASE_URL` | Supabase project URL | Yes | - |
| `SUPABASE_KEY` | Supabase anon/public key | Yes | - |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes | - |
| `SUPABASE_JWT_SECRET` | JWT secret for token validation | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `REDIS_URL` | Redis connection string (optional) | No | `redis://localhost:6379` |
| `SERVICE_NAME` | Service identifier | No | `auth-service` |
| `ENVIRONMENT` | Environment (dev/staging/prod) | No | `development` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `PORT` | Service port | No | `8001` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | No | `*` |

## Security Best Practices

1. **Environment Variables**
   - Never commit `.env` files to version control
   - Use `.env.example` as a template
   - Rotate credentials regularly
   - Use different credentials per environment

2. **Token Security**
   - Store JWT secrets securely (use secret managers in production)
   - Tokens expire after 1 hour (configurable in Supabase)
   - Implement refresh token rotation
   - Clear tokens on logout

3. **Network Security**
   - Always use HTTPS in production
   - Configure proper CORS origins (never use `*` in production)
   - Implement rate limiting
   - Use a reverse proxy (nginx/Traefik) for TLS termination

4. **Database Security**
   - Use Row Level Security (RLS) policies in Supabase
   - Never expose service role key to clients
   - Use connection pooling (PgBouncer)
   - Enable SSL for database connections

5. **Monitoring & Logging**
   - Log all authentication events
   - Monitor failed login attempts
   - Set up alerts for suspicious activity
   - Implement audit logging

## Deployment

### Docker

```bash
# Build image
docker build -t finio-auth-service:latest .

# Run container
docker run -d \
  --name auth-service \
  -p 8001:8001 \
  --env-file .env \
  finio-auth-service:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  auth-service:
    build: ./services/auth-service
    ports:
      - "8001:8001"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
```

### Kubernetes

See [infrastructure/kubernetes/auth-service/](../../infrastructure/kubernetes/auth-service/) for complete Kubernetes manifests.

### Production Checklist

Before deploying to production, ensure:

- [ ] All environment variables are set correctly
- [ ] Database migrations are applied
- [ ] Supabase email templates are configured
- [ ] CORS origins are properly restricted
- [ ] Rate limiting is enabled
- [ ] HTTPS/TLS is configured
- [ ] Monitoring and logging are set up
- [ ] Health checks are configured
- [ ] Backup strategy is in place
- [ ] Secrets are stored securely (not in code)

See [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) for the complete 90+ point deployment checklist.

## Migration from Legacy Auth

If you have existing users with custom authentication, see:
- [SUPABASE_MIGRATION.md](./SUPABASE_MIGRATION.md) - Complete migration guide
- [migrate_to_supabase.py](./migrate_to_supabase.py) - User migration script

The migration script supports:
- Dry-run mode for testing
- Batch processing for large user bases
- Email notifications for password reset
- Rollback capabilities
- Progress tracking and error reporting

## Troubleshooting

### Common Issues

**Supabase Connection Issues**
```
Error: Supabase client not initialized
```
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set
- Check that Supabase project is active
- Ensure service role key has not been rotated

**JWT Validation Failures**
```
Error: Invalid or expired token
```
- Verify `SUPABASE_JWT_SECRET` matches your project
- Check token expiration time
- Use refresh token to get new access token
- Ensure token format is correct (Bearer scheme)

**Database Connection Issues**
```
Error: Could not connect to database
```
- Verify `DATABASE_URL` is correct
- Check Supabase database is running
- Ensure connection pooling settings are correct
- Use direct connection for migrations, pooler for app

**Rate Limiting Issues**
```
Error: Too many requests
```
- Default limit: 60 requests per 60 seconds
- Clear rate limit: restart Redis or wait for window expiration
- Adjust limits in `app/middleware.py` if needed

**Email Delivery Issues**
```
Warning: Password reset email not sent
```
- Check Supabase email settings (Authentication → Email Templates)
- Verify SMTP configuration in Supabase
- Check spam folders
- Enable email provider in Supabase (Settings → Auth)

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
export ENVIRONMENT=development
uvicorn app.app:app --reload --log-level debug
```

### Health Checks

```bash
# Service health
curl http://localhost:8001/health

# Supabase connection
curl http://localhost:8001/health/supabase

# Database connection
curl http://localhost:8001/health/database
```

## Documentation

- [SUPABASE_README.md](./SUPABASE_README.md) - Quick start guide
- [SUPABASE_MIGRATION.md](./SUPABASE_MIGRATION.md) - Migration guide
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) - Technical implementation details
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md) - Production deployment checklist

## License

This project is part of the Finio Stock Research System.

## Support

For issues and questions:
- Review the documentation files above
- Check Supabase documentation: [supabase.com/docs](https://supabase.com/docs)
- Check FastAPI documentation: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- Open an issue in the repository
