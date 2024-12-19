#!/bin/bash
set -e

# Start Postfix
service postfix start

# Start Dovecot
service dovecot start

# Wait for services to be ready (max 5 seconds)
count=0
until (postfix status | grep -q 'is running' && dovecot status | grep -q 'is running') || [ $count -eq 5 ]; do
  echo "Waiting for services to start... ($count/5)"
  sleep 1
  count=$((count + 1))
done
echo "Continuing with startup..."

# Start mailos in headless mode with the test config
if [ -f "/app/e2e/email_config.json" ]; then
  echo "Starting mailos in headless mode with test config..."
  python -m mailos.app --headless --config /app/e2e/email_config.json --log-level debug
else
  echo "Error: Test config file not found"
  exit 1
fi

# Keep container running
exec "$@"
