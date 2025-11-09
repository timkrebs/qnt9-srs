#!/bin/bash
# Quick Icinga2 Installation - Install only missing components
# For Ubuntu 22.04 LTS

set -e

# Set non-interactive mode
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

echo "Quick Icinga2 installation - installing missing components only..."

# Install PostgreSQL (if not already installed)
if ! dpkg -l | grep -q "^ii  postgresql "; then
    echo "Installing PostgreSQL..."
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
else
    echo "PostgreSQL already installed, skipping..."
fi

# Ensure PostgreSQL is running
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Setup Icinga2 database (if not exists)
echo "Setting up Icinga2 database..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'icinga2'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE icinga2;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='icinga2'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER icinga2 WITH PASSWORD 'icinga2';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE icinga2 TO icinga2;"

# Import Icinga2 schema (if not already imported)
TABLE_COUNT=$(sudo -u postgres psql -d icinga2 -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
if [ "$TABLE_COUNT" -eq "0" ]; then
    echo "Importing Icinga2 database schema..."
    sudo -u postgres psql -d icinga2 < /usr/share/icinga2-ido-pgsql/schema/pgsql.sql
else
    echo "Icinga2 database schema already imported, skipping..."
fi

# Configure IDO PostgreSQL
echo "Configuring IDO PostgreSQL..."
sudo tee /etc/icinga2/features-available/ido-pgsql.conf > /dev/null <<'EOF'
library "db_ido_pgsql"

object IdoPgsqlConnection "ido-pgsql" {
  user = "icinga2"
  password = "icinga2"
  host = "localhost"
  database = "icinga2"
}
EOF

# Enable IDO PostgreSQL feature
sudo icinga2 feature enable ido-pgsql

# Install Apache and PHP (if not already installed)
if ! dpkg -l | grep -q "^ii  apache2 "; then
    echo "Installing Apache and PHP..."
    sudo apt-get install -y apache2 php php-gd php-mbstring php-intl php-pgsql php-curl php-xml php-cli
else
    echo "Apache already installed, skipping..."
fi

# Install Icinga Web 2 (if not already installed)
if ! dpkg -l | grep -q "^ii  icingaweb2 "; then
    echo "Installing Icinga Web 2..."
    sudo debconf-set-selections <<< 'icingaweb2 icingaweb2/dbconfig-install boolean false'
    sudo apt-get install -y icingaweb2 icingacli
else
    echo "Icinga Web 2 already installed, skipping..."
fi

# Setup Icinga Web 2 database
echo "Setting up Icinga Web 2 database..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = 'icingaweb2'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE icingaweb2;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='icingaweb2'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER icingaweb2 WITH PASSWORD 'icingaweb2';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE icingaweb2 TO icingaweb2;"

# Import Icinga Web 2 schema (if not already imported)
TABLE_COUNT=$(sudo -u postgres psql -d icingaweb2 -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
if [ "$TABLE_COUNT" -eq "0" ]; then
    echo "Importing Icinga Web 2 database schema..."
    sudo -u postgres psql -d icingaweb2 < /usr/share/icingaweb2/schema/pgsql.sql
else
    echo "Icinga Web 2 database schema already imported, skipping..."
fi

# Enable Icinga2 API
echo "Enabling Icinga2 API..."
sudo icinga2 api setup

# Create API user for Icinga Web 2
sudo tee /etc/icinga2/conf.d/api-users.conf > /dev/null <<'EOF'
object ApiUser "icingaweb2" {
  password = "icingaweb2"
  permissions = [ "*" ]
}
EOF

# Enable Icinga2 command feature
sudo icinga2 feature enable command

# Configure firewall
echo "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5665/tcp
echo "y" | sudo ufw enable || true

# Restart services
echo "Restarting services..."
sudo systemctl restart icinga2
sudo systemctl restart apache2

# Enable services
sudo systemctl enable icinga2
sudo systemctl enable apache2

# Generate setup token for Icinga Web 2
echo ""
echo "========================================="
echo "Icinga2 installation completed!"
echo "========================================="
echo ""
echo "To complete setup, access Icinga Web 2:"
echo "URL: http://$(curl -s ifconfig.me)/icingaweb2/setup"
echo ""
echo "Run this command to generate setup token:"
echo "  sudo icingacli setup token create"
echo ""
echo "Default API credentials:"
echo "  Username: icingaweb2"
echo "  Password: icingaweb2"
echo ""
echo "Database credentials:"
echo "  Icinga2 DB: icinga2 / icinga2"
echo "  IcingaWeb2 DB: icingaweb2 / icingaweb2"
echo ""
echo "========================================="
