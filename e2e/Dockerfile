FROM python:3.13-slim

# Install system dependencies including Postfix
RUN apt-get update && apt-get install -y \
    postfix \
    libsasl2-modules \
    && rm -rf /var/lib/apt/lists/*

# Set up Postfix for local mail delivery
RUN postconf -e 'inet_interfaces = all' \
    && postconf -e 'mydestination = localhost.localdomain, localhost' \
    && postconf -e 'mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128'

# Create directory for the local package
WORKDIR /app

# Copy the local package files
COPY . .

# Install the package in development mode
RUN pip install -e .

# Install test dependencies
RUN pip install pytest pytest-cov

# Expose SMTP port
EXPOSE 25

# Start script to run both Postfix and keep container running
COPY e2e/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
