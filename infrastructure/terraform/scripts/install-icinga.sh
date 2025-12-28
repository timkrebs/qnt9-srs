#!/bin/bash
# Icinga2 Installation Script for Ubuntu 22.04 LTS
# This script installs Icinga2, Icinga Web 2, and necessary plugins

set -e

# Set non-interactive mode for apt
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

echo "Starting Icinga2 installation..."

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Add Icinga repository
wget -O - https://packages.icinga.com/icinga.key | sudo apt-key add -
echo "deb https://packages.icinga.com/ubuntu icinga-$(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/icinga.list
echo "deb-src https://packages.icinga.com/ubuntu icinga-$(lsb_release -cs) main" | \
  sudo tee -a /etc/apt/sources.list.d/icinga.list

sudo apt-get update

# Install Icinga2
echo "Installing Icinga2..."
sudo apt-get install -y icinga2

# Install monitoring plugins
echo "Installing monitoring plugins..."
sudo apt-get install -y monitoring-plugins

# Install IDO modules for PostgreSQL
echo "Installing IDO modules..."
sudo debconf-set-selections <<< 'icinga2-ido-pgsql icinga2-ido-pgsql/dbconfig-install boolean true'
sudo debconf-set-selections <<< 'icinga2-ido-pgsql icinga2-ido-pgsql/pgsql/method select unix socket'
sudo debconf-set-selections <<< 'icinga2-ido-pgsql icinga2-ido-pgsql/database-type select pgsql'
sudo debconf-set-selections <<< 'icinga2-ido-pgsql icinga2-ido-pgsql/db/app-user string icinga2'
sudo apt-get install -y icinga2-ido-pgsql

# Install PostgreSQL
echo "Installing PostgreSQL..."
sudo apt-get install -y postgresql postgresql-contrib

# Setup Icinga2 database
echo "Setting up Icinga2 database..."
sudo -u postgres psql -c "CREATE DATABASE icinga2;"
sudo -u postgres psql -c "CREATE USER icinga2 WITH PASSWORD 'icinga2';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE icinga2 TO icinga2;"

# Import Icinga2 schema
sudo -u postgres psql -d icinga2 < /usr/share/icinga2-ido-pgsql/schema/pgsql.sql

# Enable IDO PostgreSQL feature
sudo icinga2 feature enable ido-pgsql

# Configure IDO PostgreSQL
sudo tee /etc/icinga2/features-available/ido-pgsql.conf > /dev/null <<'EOF'
object IdoPgsqlConnection "ido-pgsql" {
  user = "icinga2"
  password = "icinga2"
  host = "localhost"
  database = "icinga2"
}
EOF

# Install Apache and PHP
echo "Installing Apache and PHP..."
sudo apt-get install -y apache2 php php-{gd,mbstring,intl,pgsql,curl,xml,cli}

# Install Icinga Web 2
echo "Installing Icinga Web 2..."
sudo debconf-set-selections <<< 'icingaweb2 icingaweb2/dbconfig-install boolean true'
sudo debconf-set-selections <<< 'icingaweb2 icingaweb2/pgsql/method select unix socket'
sudo debconf-set-selections <<< 'icingaweb2 icingaweb2/database-type select pgsql'
sudo debconf-set-selections <<< 'icingaweb2 icingaweb2/db/app-user string icingaweb2'
sudo apt-get install -y icingaweb2 icingacli

# Setup Icinga Web 2 database
echo "Setting up Icinga Web 2 database..."
sudo -u postgres psql -c "CREATE DATABASE icingaweb2;"
sudo -u postgres psql -c "CREATE USER icingaweb2 WITH PASSWORD 'icingaweb2';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE icingaweb2 TO icingaweb2;"

# Import Icinga Web 2 schema
sudo -u postgres psql -d icingaweb2 < /usr/share/icingaweb2/schema/pgsql.schema.sql

# Enable Icinga2 API
echo "Enabling Icinga2 API..."
sudo icinga2 api setup

# Create API user for Icinga Web 2
sudo tee /etc/icinga2/conf.d/api-users.conf > /dev/null <<'EOF'
object ApiUser "icingaweb2" {
  password = "icingaweb2"
  permissions = [ "status/query", "actions/*", "objects/modify/*", "objects/query/*" ]
}
EOF

# Enable command feature
sudo icinga2 feature enable command

# Configure firewall (if ufw is active)
if sudo ufw status | grep -q "Status: active"; then
  echo "Configuring firewall..."
  sudo ufw allow 'Apache Full'
  sudo ufw allow 5665/tcp
fi

# Restart services
echo "Restarting services..."
sudo systemctl restart icinga2
sudo systemctl restart apache2
sudo systemctl enable icinga2
sudo systemctl enable apache2

# Generate Icinga Web 2 setup token
echo ""
echo "========================================="
echo "Icinga2 Installation Complete!"
echo "========================================="
echo ""
echo "Setup token for Icinga Web 2:"
icingacli setup token create
echo ""
echo "Access Icinga Web 2 at: http://$(curl -s ifconfig.me)/icingaweb2/setup"
echo ""
echo "Database credentials:"
echo "  Icinga2 DB: icinga2 / icinga2"
echo "  Icinga Web 2 DB: icingaweb2 / icingaweb2"
echo ""
echo "API credentials:"
echo "  User: icingaweb2"
echo "  Password: icingaweb2"
echo ""
echo "NOTE: Change these default passwords in production!"
echo "========================================="
