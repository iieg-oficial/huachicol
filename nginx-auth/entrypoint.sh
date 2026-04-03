#!/bin/sh
set -e

if [ -z "$MONITORING_AUTH_USER" ] || [ -z "$MONITORING_AUTH_PASSWORD" ]; then
    echo "Error: MONITORING_AUTH_USER and MONITORING_AUTH_PASSWORD are required"
    exit 1
fi

apk add --no-cache apache2-utils > /dev/null 2>&1
htpasswd -cb /etc/nginx/.htpasswd "$MONITORING_AUTH_USER" "$MONITORING_AUTH_PASSWORD"

exec nginx -g 'daemon off;'
