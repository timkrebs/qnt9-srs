# QNT9 Auth Service

Modern authentication service using **Supabase Auth** for the QNT9 Stock Recommendation System.

## Features

✨ **Supabase Integration**
- Secure user authentication via Supabase Auth
- Email/password authentication
- JWT-based session management
- Password reset functionality

🔐 **Security**
- Industry-standard security practices
- Secure password hashing (handled by Supabase)
- JWT token-based authentication
- CORS protection

📡 **API Endpoints**
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
- Supabase account ([supabase.com](https://supabase.com))

### Installation

1. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

Get your Supabase credentials from:
- Go to your Supabase project
- Settings → API
- Copy `Project URL` and `service_role` key

4. **Run the service:**
```bash
# Development mode
uvicorn app.app:app --reload --port 8001

# Or use make
make run
```

## Supabase Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Wait for setup to complete

### 2. Configure Authentication

1. Go to **Authentication** → **Providers**
2. Enable **Email** provider
3. Configure email templates (optional)
4. Set redirect URLs for your frontend

### 3. Get API Keys

1. Go to **Settings** → **API**
2. Copy:
   - Project URL → `SUPABASE_URL`
   - `anon` `public` key → `SUPABASE_ANON_KEY`
   - `service_role` `secret` key → `SUPABASE_SERVICE_KEY`

## API Documentation

### Sign Up

```bash
POST /auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  },
  "session": {
    "access_token": "jwt-token",
    "refresh_token": "refresh-token",
    "expires_at": 1234567890
  }
}
```

### Sign In

```bash
POST /auth/signin
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

### Get Current User

```bash
GET /auth/me
Authorization: Bearer <access-token>
```

### Update Profile

```bash
PATCH /auth/me
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "full_name": "John Updated",
  "email": "new@example.com"
}
```

### Sign Out

```bash
POST /auth/signout
Authorization: Bearer <access-token>
```

### Refresh Session

```bash
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token"
}
```

### Password Reset

```bash
POST /auth/reset-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

## Development

### Run Tests

```bash
make test
```

### Run with Coverage

```bash
make test-cov
```

### Format Code

```bash
make format
```

### Lint Code

```bash
make lint
```

## Integration with Frontend

### Example: Login Flow

```javascript
// 1. Sign in user
const response = await fetch('http://localhost:8001/auth/signin', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});

const data = await response.json();
// Store tokens securely
localStorage.setItem('access_token', data.session.access_token);
localStorage.setItem('refresh_token', data.session.refresh_token);

// 2. Use access token for authenticated requests
const userResponse = await fetch('http://localhost:8001/auth/me', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
});

// 3. Refresh token when expired
const refreshResponse = await fetch('http://localhost:8001/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: localStorage.getItem('refresh_token')
  })
});
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | ✅ |
| `SUPABASE_SERVICE_KEY` | Service role key from Supabase | ✅ |
| `SUPABASE_ANON_KEY` | Anonymous key from Supabase | ✅ |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | ❌ |
| `DEBUG` | Enable debug mode | ❌ |
| `CORS_ORIGINS` | Allowed CORS origins | ❌ |

## Security Best Practices

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Use HTTPS in production** - Always use secure connections
3. **Rotate keys regularly** - Change Supabase keys periodically
4. **Implement rate limiting** - Protect against brute force attacks
5. **Validate all inputs** - Use Pydantic models for validation
6. **Log security events** - Monitor authentication attempts

## Deployment

### Docker

```bash
docker build -t qnt9-auth-service .
docker run -p 8001:8001 --env-file .env qnt9-auth-service
```

### Production Considerations

- Use environment variables for all sensitive data
- Enable HTTPS/TLS
- Configure proper CORS origins
- Set up monitoring and alerts
- Implement rate limiting
- Use a reverse proxy (nginx/Traefik)

## Troubleshooting

### Common Issues

**Issue:** `Supabase not configured` error
- **Solution:** Check that `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set in `.env`

**Issue:** `Invalid or expired token`
- **Solution:** Use the refresh token to get a new access token

**Issue:** CORS errors from frontend
- **Solution:** Add your frontend URL to `CORS_ORIGINS` in `.env`

## License

This project is part of the QNT9 Stock Recommendation System.

## Support

For issues and questions:
- Create an issue in the repository
- Check existing documentation
- Review Supabase documentation: [supabase.com/docs](https://supabase.com/docs)
