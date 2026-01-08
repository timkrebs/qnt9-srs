# Notification Service

Finio Notification Service handles email notifications for price alerts and marketing campaigns.

## Features

- Price alert notifications via Resend
- Marketing email campaigns
- User notification preferences management
- Background worker for daily price monitoring
- Notification history tracking
- Multi-channel notification abstraction

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Resend API key and database credentials
```

3. Run the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8040 --reload
```

## API Endpoints

### User Endpoints

- `GET /api/v1/preferences` - Get notification preferences
- `PATCH /api/v1/preferences` - Update notification preferences

### Admin Endpoints

- `POST /api/v1/admin/marketing-email` - Send marketing campaign
- `GET /api/v1/admin/notification-history` - Query notification logs

### Health & Metrics

- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

## Configuration

Key environment variables:

- `RESEND_API_KEY` - Resend API key for email delivery
- `DATABASE_URL` - PostgreSQL connection string
- `SUPABASE_JWT_SECRET` - JWT secret for authentication
- `SEARCH_SERVICE_URL` - URL for search service (price data)
- `PRICE_ALERT_SEND_HOUR` - Hour to send daily price alerts (default: 8)
- `ALERT_COOLDOWN_HOURS` - Cooldown period between alerts (default: 24)

## Background Workers

The service includes a background worker that runs daily at the configured hour (default: 8 AM) to:

1. Query watchlist items with alerts enabled
2. Fetch current prices from search service
3. Check price thresholds
4. Send notifications via Resend
5. Log delivery status

## Email Templates

Email templates are located in `app/templates/`:

- `price_alert.html` - Price alert notification
- `marketing_welcome.html` - Welcome email
- `product_update.html` - Product update announcement

## Notification Channels

The service uses a channel abstraction to support multiple notification types:

- Email (via Resend) - implemented
- SMS - future
- Push notifications - future
- In-app notifications - future

## Database Schema

### notification_preferences

Stored as JSONB in `user_profiles.notification_preferences`:

```json
{
  "email_notifications": true,
  "product_updates": true,
  "usage_alerts": true,
  "security_alerts": true,
  "marketing_emails": false
}
```

### notification_history

Tracks all sent notifications:

- id (UUID)
- user_id (UUID)
- notification_type (price_alert, marketing, product_update)
- sent_at (timestamp)
- delivery_status (sent, failed, bounced)
- resend_id (external ID)
- metadata (JSONB)

## Development

Run tests:
```bash
pytest
```

Run with Docker:
```bash
docker build -t finio-notification-service .
docker run -p 8040:8040 --env-file .env finio-notification-service
```
