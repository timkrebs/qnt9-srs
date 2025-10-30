# Frontend Service

Web UI for the QNT9 Stock Recommendation System. Provides an interactive interface for searching stocks by ISIN, WKN, or symbol using HTMX for progressive enhancement.

## Features

- **Stock Search**: Search by ISIN, WKN, or stock symbol
- **Real-time Autocomplete**: Suggestions based on search history
- **Modern UI**: Built with HTMX + Tailwind CSS for responsive design
- **Detailed Stock Cards**: Display comprehensive stock information
- **Fast & Lightweight**: No heavy JavaScript frameworks
- **Accessible**: Keyboard navigation and screen reader support

## Technology Stack

- **FastAPI**: Web framework
- **HTMX**: Progressive enhancement without heavy JS
- **Jinja2**: Server-side templating
- **Tailwind CSS**: Utility-first CSS framework
- **httpx**: Async HTTP client for service communication

## Prerequisites

- Python 3.11+
- Running [search-service](../search-service) instance
- pip or poetry for dependency management

## Installation

```bash
# Clone the repository (if not already done)
cd services/frontend-service

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the service root:

```bash
# Copy example configuration
cp .env.example .env
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SEARCH_SERVICE_URL` | URL of the search-service backend | `http://localhost:8000` |
| `HOST` | Host to bind the service | `0.0.0.0` |
| `PORT` | Port to run the service | `8001` |
| `DEBUG` | Enable debug mode | `false` |
| `APP_NAME` | Application name | `QNT9 Stock Search` |

## Running the Service

### Development Mode (with hot reload)

```bash
make fastapi-dev
```

This starts the service on `http://localhost:8001` with auto-reload enabled.

### Production Mode

```bash
make fastapi-prod
```

### Using Docker

```bash
# Build image
make docker-build

# Run container
make docker-run

# Or use docker-compose
docker-compose up
```

## Usage

### Web Interface

1. Navigate to `http://localhost:8001`
2. Enter an ISIN, WKN, or stock symbol in the search bar
3. Click "Search" or press Enter
4. View detailed stock information

### Keyboard Shortcuts

- `Ctrl/Cmd + K`: Focus search input
- `Escape`: Close suggestions dropdown
- `Enter`: Submit search
- `Tab`: Navigate between elements

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage with search interface |
| `/search` | GET | HTMX endpoint for stock search |
| `/api/suggestions` | GET | Autocomplete suggestions |
| `/about` | GET | About page |
| `/health` | GET | Health check |

## Architecture

### HTMX Pattern

The frontend uses HTMX for dynamic interactions without complex JavaScript:

```html
<!-- Search form triggers HTMX request -->
<form hx-get="/search" 
      hx-target="#search-results" 
      hx-indicator="#loading-overlay">
    <input name="query" type="text" />
</form>

<!-- Results container updated by HTMX -->
<div id="search-results"></div>
```

### Service Communication

```
┌──────────────┐      HTTP GET      ┌──────────────┐
│   Browser    │ ←─────────────────→ │   Frontend   │
│   (HTMX)     │   HTML Partials    │   Service    │
└──────────────┘                     └───────┬──────┘
                                             │
                                             │ HTTP GET
                                             │ JSON API
                                             │
                                     ┌───────▼──────┐
                                     │    Search    │
                                     │   Service    │
                                     └──────────────┘
```

## Testing

### Run All Tests

```bash
make test
```

### Run Tests with Coverage

```bash
make test-coverage
```

### Run Specific Test File

```bash
pytest tests/test_app.py -v
```

### Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_app.py             # Main application tests
└── test_api_client.py      # API client tests
```

## Development

### Code Formatting

```bash
# Format code with black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Type checking with mypy
mypy app/
```

### Project Structure

```
frontend-service/
├── app/
│   ├── __init__.py
│   ├── app.py              # Main FastAPI application
│   ├── config.py           # Configuration settings
│   ├── api_client.py       # Search service HTTP client
│   ├── templates/          # Jinja2 templates
│   │   ├── base.html       # Base layout with HTMX
│   │   ├── index.html      # Homepage
│   │   ├── about.html      # About page
│   │   └── components/     # Reusable components
│   │       ├── search_bar.html
│   │       ├── stock_card.html
│   │       ├── suggestions.html
│   │       └── error.html
│   └── static/             # Static assets
│       ├── css/
│       │   └── styles.css
│       └── js/
│           └── main.js
├── tests/                  # Test suite
├── Dockerfile
├── Makefile
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Troubleshooting

### Search Service Not Available

**Error**: "Search Service Unavailable"

**Solution**:
1. Ensure search-service is running: `cd ../search-service && make fastapi-dev`
2. Verify `SEARCH_SERVICE_URL` in `.env`
3. Check network connectivity

### Templates Not Found

**Error**: "Template not found"

**Solution**:
- Verify `app/templates/` directory exists
- Check template paths in `app.py`
- Restart the service

### Static Files Not Loading

**Error**: 404 on `/static/` resources

**Solution**:
- Ensure `app/static/` directory exists
- Check static mount in `app.py`
- Clear browser cache

### HTMX Not Working

**Issue**: Page refreshes instead of partial updates

**Solution**:
- Verify HTMX script is loaded in `base.html`
- Check browser console for JavaScript errors
- Ensure `hx-*` attributes are correctly set

## Performance

### Response Times

- Homepage: <50ms
- Search (cached): <100ms
- Search (uncached): <2s (depends on search-service)
- Autocomplete: <100ms

### Optimization

- Static assets served directly via FastAPI
- HTMX reduces bandwidth (only HTML partials)
- Server-side rendering for better SEO
- Browser caching for static resources

## Security

### Headers

```python
# Added in production
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

### Input Validation

- Query length limits (1-20 characters)
- FastAPI Pydantic validation
- HTML escaping via Jinja2

## Deployment

### Docker Deployment

```bash
# Build production image
docker build -t frontend-service:latest .

# Run with environment variables
docker run -p 8001:8001 \
  -e SEARCH_SERVICE_URL=http://search-service:8000 \
  frontend-service:latest
```

### Kubernetes (via Helm)

See `infrastructure/helm-charts/frontend-service/`

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 30
```

## Contributing

1. Follow [Conventional Commits](https://www.conventionalcommits.org/)
2. Write tests for new features
3. Maintain >80% code coverage
4. Format code with black/isort
5. Update documentation

## License

MIT License - see [LICENSE](../../LICENSE)

## Related Services

- [search-service](../search-service) - Stock search backend
- [auth-service](../auth-service) - Authentication service
- [analysis-service](../analysis-service) - Stock analysis engine

## Support

For issues and questions:
- GitHub Issues: [qnt9-srs/issues](https://github.com/your-org/qnt9-srs/issues)
- Documentation: [docs/](../../docs/)
