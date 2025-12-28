# Watchlist Service

Manages user stock watchlists with tier-based limits.

## Features

- **Tier-based Limits**:
  - Free tier: Maximum 3 stocks
  - Paid/Enterprise: Unlimited stocks
- **JWT Authentication**: Secure user authentication
- **Price Alerts**: Optional price alert configuration
- **Notes**: Add custom notes to watchlist items

## API Endpoints

### `GET /api/watchlist`
Get user's watchlist.

**Response:**
```json
{
  "watchlist": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "symbol": "AAPL",
      "alert_enabled": false,
      "alert_price_above": null,
      "alert_price_below": null,
      "notes": "My favorite stock",
      "added_at": "2025-12-28T10:00:00Z"
    }
  ],
  "total": 1,
  "tier": "free",
  "limit": 3
}
```

### `POST /api/watchlist`
Add stock to watchlist.

**Request:**
```json
{
  "symbol": "AAPL",
  "notes": "Optional notes",
  "alert_enabled": false,
  "alert_price_above": 200.0,
  "alert_price_below": 150.0
}
```

**Response:** `201 Created` with watchlist item

### `DELETE /api/watchlist/{symbol}`
Remove stock from watchlist.

**Response:** `200 OK` with success message

### `PATCH /api/watchlist/{symbol}`
Update watchlist item.

**Request:**
```json
{
  "notes": "Updated notes",
  "alert_enabled": true,
  "alert_price_above": 210.0
}
```

## Environment Variables

See `.env.example` for all configuration options.

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python -m uvicorn app.main:app --reload --port 8012
```

## Docker

```bash
# Build
docker build -t watchlist-service .

# Run
docker run -p 8012:8012 --env-file .env watchlist-service
```

## Testing

```bash
# Health check
curl http://localhost:8012/health

# Get watchlist (requires auth token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8012/api/watchlist

# Add stock
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL"}' \
  http://localhost:8012/api/watchlist
```
