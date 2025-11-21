FROM ubuntu:22.04

# Set non-interactive mode
ENV DEBIAN_FRONTEND=noninteractive
ENV NEEDRESTART_MODE=a

# Install basic packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    software-properties-common \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Add Icinga repository
RUN wget -O - https://packages.icinga.com/icinga.key | apt-key add - \
    && echo "deb https://packages.icinga.com/ubuntu icinga-jammy main" > /etc/apt/sources.list.d/icinga.list \
    && echo "deb-src https://packages.icinga.com/ubuntu icinga-jammy main" >> /etc/apt/sources.list.d/icinga.list

# Update package list
RUN apt-get update

# Install Icinga2 and plugins
RUN apt-get install -y \
    icinga2 \
    monitoring-plugins \
    icinga2-ido-pgsql \
    && rm -rf /var/lib/apt/lists/*

# Install Apache and PHP for Icinga Web 2
RUN apt-get update && apt-get install -y \
    apache2 \
    php \
    php-gd \
    php-mbstring \
    php-intl \
    php-pgsql \
    php-curl \
    php-xml \
    php-cli \
    icingaweb2 \
    icingacli \
    && rm -rf /var/lib/apt/lists/*

# Enable Apache modules
RUN a2enmod rewrite && a2enmod ssl

# Create necessary directories
RUN mkdir -p /var/run/icinga2 \
    && mkdir -p /var/log/icinga2 \
    && mkdir -p /etc/icingaweb2 \
    && mkdir -p /var/lib/icinga2

# Set permissions
RUN chown -R nagios:nagios /var/run/icinga2 \
    && chown -R nagios:nagios /var/log/icinga2 \
    && chown -R nagios:nagios /var/lib/icinga2

# Copy configuration files
COPY config/templates.conf /etc/icinga2/conf.d/templates.conf
COPY config/notifications.conf /etc/icinga2/conf.d/notifications.conf
COPY config/commands.conf /etc/icinga2/conf.d/commands.conf
COPY config/ido-pgsql.conf /etc/icinga2/features-available/ido-pgsql.conf
COPY config/hosts.conf /etc/icinga2/conf.d/hosts.conf
COPY config/services.conf /etc/icinga2/conf.d/services.conf
COPY config/servicegroups.conf /etc/icinga2/conf.d/servicegroups.conf
COPY config/users.conf /etc/icinga2/conf.d/users.conf
COPY config/resources.ini /etc/icingaweb2/resources.ini
COPY config/authentication.ini /etc/icingaweb2/authentication.ini
COPY config/roles.ini /etc/icingaweb2/roles.ini
COPY config/config.ini /etc/icingaweb2/config.ini
COPY config/monitoring-config.ini /etc/icingaweb2/modules/monitoring/config.ini
COPY config/monitoring-backends.ini /etc/icingaweb2/modules/monitoring/backends.ini
COPY config/monitoring-commandtransports.ini /etc/icingaweb2/modules/monitoring/commandtransports.ini

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Enable IDO feature and disable notifications (not configured)
RUN icinga2 feature enable ido-pgsql command && icinga2 feature disable notification

# Enable monitoring module
RUN icingacli module enable monitoring

# Expose ports
EXPOSE 80 5665

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/icingaweb2 || exit 1

# Start services
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
