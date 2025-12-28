# Icinga2 Monitoring Service

Docker-based Icinga2 monitoring solution for QNT9 microservices architecture.

## Overview

This service provides comprehensive monitoring for all QNT9 services including:
- Health checks for all microservices
- Database connectivity monitoring
- Message broker (Kafka) monitoring
- Service discovery (Consul) monitoring
- Response time tracking

## Components

- **Icinga2**: Core monitoring engine
- **Icinga Web 2**: Web-based monitoring dashboard
- **PostgreSQL**: Backend for Icinga2 IDO and Icinga Web 2
- **Apache**: Web server for Icinga Web 2 interface

## Quick Start

1. Start monitoring stack:
```bash
docker-compose up -d icinga2
```

2. Access Icinga Web 2:
```
URL: http://localhost:8888/icingaweb2
Username: admin
Password: admin
```

## Monitored Services

### Backend Services
- **search-service** (port 8000): Stock search API with health endpoint
- **data-ingestion-service** (port 8001): Data ingestion with health endpoint
- **etl-pipeline-service** (port 8002): ETL processing with health endpoint
- **frontend-service** (port 8080): Web UI with health endpoint

### Infrastructure
- **postgres** (port 5432): PostgreSQL database
- **timescaledb** (port 5432): TimescaleDB for time-series data
- **redis** (port 6379): Cache layer
- **kafka** (port 9092): Event streaming
- **consul** (port 8500): Service discovery

## Configuration

### Environment Variables

- `ICINGA_DB_HOST`: PostgreSQL host for Icinga2 IDO (default: postgres)
- `ICINGA_DB_NAME`: Database name for Icinga2 (default: icinga2)
- `ICINGA_DB_USER`: Database user for Icinga2 (default: icinga2)
- `ICINGA_DB_PASSWORD`: Database password for Icinga2 (default: icinga2)
- `ICINGAWEB_DB_HOST`: PostgreSQL host for Icinga Web 2 (default: postgres)
- `ICINGAWEB_DB_NAME`: Database name for Icinga Web 2 (default: icingaweb2)
- `ICINGAWEB_DB_USER`: Database user for Icinga Web 2 (default: icingaweb2)
- `ICINGAWEB_DB_PASSWORD`: Database password for Icinga Web 2 (default: icingaweb2)
- `ICINGAWEB_ADMIN_USER`: Admin username (default: admin)
- `ICINGAWEB_ADMIN_PASSWORD`: Admin password (default: admin)

### Custom Checks

Add custom service checks in `config/services.conf`:

```
apply Service "custom_check" {
  import "generic-service"
  check_command = "http"
  vars.http_vhost = host.address
  vars.http_port = 8000
  vars.http_uri = "/custom/endpoint"
  
  assign where host.name == "service-name"
}
```

### Adding New Hosts

Add new hosts in `config/hosts.conf`:

```
object Host "new-service" {
  import "generic-host"
  address = "new-service"
  vars.http_port = 8003
  vars.http_uri = "/health"
  vars.notification["mail"] = {
    groups = [ "icingaadmins" ]
  }
}
```

## Monitoring Checks

### Health Checks
- HTTP health endpoints for all services
- Expected response contains "healthy" status
- Check interval: 15 seconds
- Retry interval: 5 seconds

### Response Time Monitoring
- Warning threshold: 2000ms (services), 1000ms (frontend)
- Critical threshold: 5000ms (services), 3000ms (frontend)

### Database Checks
- PostgreSQL connection tests
- TCP port availability
- Check interval: 30 seconds

### Network Checks
- Ping4 checks for all hosts
- TCP port checks for services without HTTP endpoints

## Troubleshooting

### Check Icinga2 Status
```bash
docker-compose exec icinga2 icinga2 daemon -C
```

### View Icinga2 Logs
```bash
docker-compose logs -f icinga2
```

### Restart Icinga2
```bash
docker-compose restart icinga2
```

### Verify Database Connection
```bash
docker-compose exec icinga2 psql -h postgres -U icinga2 -d icinga2 -c "SELECT 1;"
```

### Check Service Status
```bash
docker-compose exec icinga2 icinga2 object list --type Service
```

## Security Notes

IMPORTANT: Change default passwords in production:
- Update `ICINGAWEB_ADMIN_PASSWORD` in docker-compose.yml
- Update database passwords
- Configure proper authentication backend
- Enable HTTPS for web interface

## Architecture

```
┌─────────────────┐
│  Icinga Web 2   │ (Port 8888)
│    (Apache)     │
└────────┬────────┘
         │
┌────────▼────────┐
│    Icinga2      │
│  Monitoring     │
│     Engine      │
└────────┬────────┘
         │
┌────────▼────────┐
│   PostgreSQL    │ (Port 5432)
│  icinga2 DB     │
│  icingaweb2 DB  │
└─────────────────┘
```

## Performance

- Monitoring checks run every 15-30 seconds
- Minimal resource overhead
- Scales to monitor hundreds of services
- Historical data stored in PostgreSQL

## Integration

### Prometheus Integration
Icinga2 can export metrics to Prometheus for long-term storage and advanced visualization.

### Alerting
Configure notifications in Icinga2 for:
- Email notifications
- Slack webhooks
- PagerDuty integration

## Maintenance

### Backup Database
```bash
docker-compose exec postgres pg_dump -U icinga2 icinga2 > icinga2_backup.sql
docker-compose exec postgres pg_dump -U icingaweb2 icingaweb2 > icingaweb2_backup.sql
```

### Update Configuration
1. Edit configuration files in `config/`
2. Rebuild container: `docker-compose build icinga2`
3. Restart service: `docker-compose up -d icinga2`

## Links

- Icinga2 Documentation: https://icinga.com/docs/icinga-2/latest/
- Icinga Web 2 Documentation: https://icinga.com/docs/icinga-web-2/latest/
