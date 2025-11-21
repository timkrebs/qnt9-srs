#!/bin/bash
set -e

echo "[INFO] Starting Icinga2 Docker Container..."

# Wait for PostgreSQL to be ready
echo "[INFO] Waiting for PostgreSQL..."
until PGPASSWORD=${ICINGA_DB_PASSWORD} psql -h ${ICINGA_DB_HOST} -U ${ICINGA_DB_USER} -d postgres -c '\q' 2>/dev/null; do
  echo "[INFO] PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "[INFO] PostgreSQL is ready!"

# Create Icinga2 IDO database if it doesn't exist
echo "[INFO] Setting up Icinga2 database..."
PGPASSWORD=${ICINGA_DB_PASSWORD} psql -h ${ICINGA_DB_HOST} -U ${ICINGA_DB_USER} -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '${ICINGA_DB_NAME}'" | grep -q 1 || \
  PGPASSWORD=${ICINGA_DB_PASSWORD} psql -h ${ICINGA_DB_HOST} -U ${ICINGA_DB_USER} -d postgres -c "CREATE DATABASE ${ICINGA_DB_NAME};"

# Import schema if tables don't exist
TABLE_COUNT=$(PGPASSWORD=${ICINGA_DB_PASSWORD} psql -h ${ICINGA_DB_HOST} -U ${ICINGA_DB_USER} -d ${ICINGA_DB_NAME} -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
if [ "$TABLE_COUNT" -eq "0" ]; then
  echo "[INFO] Importing Icinga2 IDO schema..."
  PGPASSWORD=${ICINGA_DB_PASSWORD} psql -h ${ICINGA_DB_HOST} -U ${ICINGA_DB_USER} -d ${ICINGA_DB_NAME} < /usr/share/icinga2-ido-pgsql/schema/pgsql.sql
fi

# Create Icinga Web 2 database if it doesn't exist
echo "[INFO] Setting up Icinga Web 2 database..."
PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '${ICINGAWEB_DB_NAME}'" | grep -q 1 || \
  PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d postgres -c "CREATE DATABASE ${ICINGAWEB_DB_NAME};"

# Import Icinga Web 2 schema if tables don't exist
TABLE_COUNT=$(PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d ${ICINGAWEB_DB_NAME} -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
if [ "$TABLE_COUNT" -eq "0" ]; then
  echo "[INFO] Importing Icinga Web 2 schema..."
  PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d ${ICINGAWEB_DB_NAME} < /usr/share/icingaweb2/schema/pgsql.schema.sql
fi

# Grant database permissions
echo "[INFO] Granting database permissions..."
PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d ${ICINGAWEB_DB_NAME} -c "GRANT USAGE ON SCHEMA public TO ${ICINGAWEB_DB_USER};" 2>/dev/null || true
PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d ${ICINGAWEB_DB_NAME} -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${ICINGAWEB_DB_USER};" 2>/dev/null || true
PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d ${ICINGAWEB_DB_NAME} -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${ICINGAWEB_DB_USER};" 2>/dev/null || true

# Create admin user if not exists
echo "[INFO] Creating Icinga Web 2 admin user..."
ADMIN_PASSWORD_HASH=$(openssl passwd -1 "${ICINGAWEB_ADMIN_PASSWORD}")
PGPASSWORD=${ICINGAWEB_DB_PASSWORD} psql -h ${ICINGAWEB_DB_HOST} -U ${ICINGAWEB_DB_USER} -d ${ICINGAWEB_DB_NAME} -c "INSERT INTO icingaweb_user (name, active, password_hash) VALUES ('${ICINGAWEB_ADMIN_USER}', 1, '${ADMIN_PASSWORD_HASH}') ON CONFLICT DO NOTHING;" 2>/dev/null || true

# Update IDO configuration with environment variables
echo "[INFO] Configuring IDO database connection..."
cat > /etc/icinga2/features-available/ido-pgsql.conf <<EOF
library "db_ido_pgsql"

object IdoPgsqlConnection "ido-pgsql" {
  user = "${ICINGA_DB_USER}"
  password = "${ICINGA_DB_PASSWORD}"
  host = "${ICINGA_DB_HOST}"
  database = "${ICINGA_DB_NAME}"
}
EOF

# Update Icinga Web 2 resources with environment variables
echo "[INFO] Configuring Icinga Web 2 resources..."
cat > /etc/icingaweb2/resources.ini <<EOF
[icingaweb_db]
type = db
db = pgsql
host = ${ICINGAWEB_DB_HOST}
port = 5432
dbname = ${ICINGAWEB_DB_NAME}
username = ${ICINGAWEB_DB_USER}
password = ${ICINGAWEB_DB_PASSWORD}
charset = UTF8
use_ssl = 0

[icinga_ido]
type = db
db = pgsql
host = ${ICINGA_DB_HOST}
port = 5432
dbname = ${ICINGA_DB_NAME}
username = ${ICINGA_DB_USER}
password = ${ICINGA_DB_PASSWORD}
charset = UTF8
use_ssl = 0
EOF

# Set proper permissions for Icinga Web 2
echo "[INFO] Setting permissions..."
chown -R www-data:icingaweb2 /etc/icingaweb2 2>/dev/null || true
chmod 2770 /etc/icingaweb2 2>/dev/null || true
find /etc/icingaweb2 -type f -name "*.ini" -exec chmod 660 {} \; 2>/dev/null || true
find /etc/icingaweb2 -type d -exec chmod 2770 {} \; 2>/dev/null || true

# Add www-data to nagios group
usermod -a -G nagios www-data 2>/dev/null || true

# Start Apache in background
echo "[INFO] Starting Apache..."
apache2ctl start

# Start Icinga2 in foreground
echo "[INFO] Starting Icinga2..."
exec /usr/sbin/icinga2 daemon --no-stack-rlimit
