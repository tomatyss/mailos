#!/bin/bash
set -e

# Start Postfix
service postfix start

# Keep container running and execute any passed command
exec "$@"
