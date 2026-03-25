#!/bin/bash

ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:${ALERTMANAGER_PORT:-6002}}"

send_alert() {
    local name="$1"
    local payload="$2"
    echo -n "Enviando $name... "
    code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$ALERTMANAGER_URL/api/v2/alerts" \
        -H "Content-Type: application/json" \
        -d "$payload")
    if [ "$code" = "200" ]; then
        echo "OK ($code)"
    else
        echo "ERROR ($code)"
    fi
}

NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

usage() {
    echo "Uso: $0 [alerta|all|list]"
    echo ""
    echo "Alertas disponibles:"
    echo "  service-down         ServiceDown (critical)"
    echo "  high-latency         HighLatency (warning)"
    echo "  high-error-rate      HighErrorRate (critical)"
    echo "  high-memory          HighMemoryUsage (warning)"
    echo "  disk-low             DiskSpaceLow (warning)"
    echo "  postgres-down        PostgreSQLDown (critical)"
    echo "  too-many-connections TooManyConnections (warning)"
    echo "  all                  Enviar todas las alertas"
    echo "  list                 Mostrar alertas activas en Alertmanager"
    echo ""
    echo "Ejemplo: $0 service-down"
    echo "         $0 all"
}

alert_service_down() {
    send_alert "ServiceDown" '[{
        "status": "firing",
        "labels": {
            "alertname": "ServiceDown",
            "job": "gateway-nginx",
            "instance": "nginx-exporter:9113",
            "service": "nginx",
            "project": "gateway-hub",
            "severity": "critical"
        },
        "annotations": {
            "summary": "Service gateway-nginx is down",
            "description": "gateway-nginx (nginx-exporter:9113) has been down for more than 1 minute."
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

alert_high_latency() {
    send_alert "HighLatency" '[{
        "status": "firing",
        "labels": {
            "alertname": "HighLatency",
            "instance": "host.docker.internal:9090",
            "service": "backend",
            "project": "urlschiquitas",
            "severity": "warning"
        },
        "annotations": {
            "summary": "High latency on urlschiquitas",
            "description": "Average latency is 2.5s for urlschiquitas"
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

alert_high_error_rate() {
    send_alert "HighErrorRate" '[{
        "status": "firing",
        "labels": {
            "alertname": "HighErrorRate",
            "instance": "host.docker.internal:9090",
            "service": "backend",
            "project": "urlschiquitas",
            "severity": "critical"
        },
        "annotations": {
            "summary": "High error rate on urlschiquitas",
            "description": "Error rate is 12% on urlschiquitas"
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

alert_high_memory() {
    send_alert "HighMemoryUsage" '[{
        "status": "firing",
        "labels": {
            "alertname": "HighMemoryUsage",
            "instance": "portal-nvo:9100",
            "service": "node-exporter",
            "severity": "warning"
        },
        "annotations": {
            "summary": "High memory usage on portal-nvo:9100",
            "description": "Memory usage is above 90% on portal-nvo:9100"
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

alert_disk_low() {
    send_alert "DiskSpaceLow" '[{
        "status": "firing",
        "labels": {
            "alertname": "DiskSpaceLow",
            "instance": "portal-nvo:9100",
            "service": "node-exporter",
            "mountpoint": "/",
            "severity": "warning"
        },
        "annotations": {
            "summary": "Low disk space on portal-nvo:9100",
            "description": "Disk space is below 10% on portal-nvo:9100"
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

alert_postgres_down() {
    send_alert "PostgreSQLDown" '[{
        "status": "firing",
        "labels": {
            "alertname": "PostgreSQLDown",
            "instance": "host.docker.internal:9187",
            "service": "postgres",
            "project": "urlschiquitas",
            "severity": "critical"
        },
        "annotations": {
            "summary": "PostgreSQL is down",
            "description": "PostgreSQL on host.docker.internal:9187 is down"
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

alert_too_many_connections() {
    send_alert "TooManyConnections" '[{
        "status": "firing",
        "labels": {
            "alertname": "TooManyConnections",
            "instance": "host.docker.internal:9187",
            "service": "postgres",
            "project": "urlschiquitas",
            "severity": "warning"
        },
        "annotations": {
            "summary": "Too many database connections",
            "description": "Database connections are at 85% of max on host.docker.internal:9187"
        },
        "startsAt": "'"$NOW"'",
        "generatorURL": "'"$ALERTMANAGER_URL"'/test"
    }]'
}

list_alerts() {
    echo "Alertas activas en Alertmanager:"
    echo ""
    curl -s "$ALERTMANAGER_URL/api/v2/alerts" | python3 -m json.tool 2>/dev/null || \
        curl -s "$ALERTMANAGER_URL/api/v2/alerts"
}

case "${1:-}" in
    service-down)         alert_service_down ;;
    high-latency)         alert_high_latency ;;
    high-error-rate)      alert_high_error_rate ;;
    high-memory)          alert_high_memory ;;
    disk-low)             alert_disk_low ;;
    postgres-down)        alert_postgres_down ;;
    too-many-connections) alert_too_many_connections ;;
    list)                 list_alerts ;;
    all)
        alert_service_down
        alert_high_latency
        alert_high_error_rate
        alert_high_memory
        alert_disk_low
        alert_postgres_down
        alert_too_many_connections
        echo ""
        echo "Todas las alertas enviadas. Alertmanager las agrupara y enviara a Discord en ~10s."
        ;;
    *)
        usage
        exit 1
        ;;
esac
