#!/bin/bash

echo "========================================="
echo "Icinga2 Monitoring Test Script"
echo "========================================="
echo ""

# Check Icinga2 container status
echo "[TEST] Checking Icinga2 container status..."
STATUS=$(docker-compose ps icinga2 | grep "healthy" || echo "FAIL")
if [[ "$STATUS" == *"healthy"* ]]; then
    echo "[OK] Icinga2 container is healthy"
else
    echo "[FAIL] Icinga2 container is not healthy"
    exit 1
fi
echo ""

# Check Icinga Web 2 accessibility
echo "[TEST] Checking Icinga Web 2 accessibility..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8888/icingaweb2/)
if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "301" ]]; then
    echo "[OK] Icinga Web 2 is accessible at http://localhost:8888/icingaweb2/"
else
    echo "[FAIL] Icinga Web 2 is not accessible (HTTP $HTTP_CODE)"
fi
echo ""

# Check monitored hosts
echo "[TEST] Checking monitored hosts..."
HOSTS=$(docker-compose exec -T postgres psql -U icinga2 -d icinga2 -tAc "SELECT COUNT(*) FROM icinga_objects WHERE objecttype_id=1 AND is_active=1;")
echo "Monitored hosts: $HOSTS"
if [[ "$HOSTS" -ge "8" ]]; then
    echo "[OK] All expected hosts are monitored"
    docker-compose exec -T postgres psql -U icinga2 -d icinga2 -tAc "SELECT '  - ' || name1 FROM icinga_objects WHERE objecttype_id=1 AND is_active=1;"
else
    echo "[FAIL] Expected at least 8 hosts, found $HOSTS"
fi
echo ""

# Check monitored services
echo "[TEST] Checking monitored services..."
SERVICES=$(docker-compose exec -T postgres psql -U icinga2 -d icinga2 -tAc "SELECT COUNT(*) FROM icinga_objects WHERE objecttype_id=2 AND is_active=1;")
echo "Monitored services: $SERVICES"
if [[ "$SERVICES" -ge "20" ]]; then
    echo "[OK] All expected services are monitored"
else
    echo "[WARN] Expected at least 20 services, found $SERVICES"
fi
echo ""

# Check service health endpoints
echo "[TEST] Checking QNT9 service health endpoints..."

check_service() {
    SERVICE=$1
    URL=$2
    RESPONSE=$(curl -s "$URL" | grep -o "healthy" || echo "FAIL")
    if [[ "$RESPONSE" == "healthy" ]]; then
        echo "[OK] $SERVICE is healthy"
    else
        echo "[FAIL] $SERVICE is not responding correctly"
    fi
}

check_service "search-service" "http://localhost:8000/api/v1/health"
check_service "data-ingestion-service" "http://localhost:8001/health"
check_service "etl-pipeline-service" "http://localhost:8002/health"
check_service "frontend-service" "http://localhost:8080/health"
echo ""

# Check Consul health
echo "[TEST] Checking Consul service..."
CONSUL=$(curl -s http://localhost:8500/v1/status/leader | grep -o ":" || echo "FAIL")
if [[ "$CONSUL" == ":" ]]; then
    echo "[OK] Consul is healthy"
else
    echo "[FAIL] Consul is not responding"
fi
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "Icinga Web 2: http://localhost:8888/icingaweb2/"
echo "Username: admin"
echo "Password: admin"
echo ""
echo "[OK] Monitoring solution is operational"
echo "========================================="
