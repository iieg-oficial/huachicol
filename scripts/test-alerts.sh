#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "${PROJECT_DIR}/.env" ]; then
    set -a
    . "${PROJECT_DIR}/.env"
    set +a
fi

ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:${ALERTMANAGER_PORT:?ALERTMANAGER_PORT is required}}"
PG_INSTANCE="${DATAENGINE_POSTGRES_TARGET:?DATAENGINE_POSTGRES_TARGET is required}"
NGINX_INSTANCE="${GATEWAY_NGINX_TARGET:?GATEWAY_NGINX_TARGET is required}"
NODE_INSTANCE="node-exporter:9100"

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
            "instance": "'"$NGINX_INSTANCE"'",
            "service": "nginx",
            "project": "gateway-hub",
            "severity": "critical"
        },
        "annotations": {
            "summary": "Servicio gateway-nginx caido",
            "description": "gateway-nginx ('"$NGINX_INSTANCE"') lleva mas de 1 minuto sin responder."
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
            "instance": "'"$NGINX_INSTANCE"'",
            "service": "nginx",
            "project": "gateway-hub",
            "severity": "warning"
        },
        "annotations": {
            "summary": "Latencia alta en gateway-hub",
            "description": "La latencia promedio es 2.5s en gateway-hub."
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
            "instance": "'"$NGINX_INSTANCE"'",
            "service": "nginx",
            "project": "gateway-hub",
            "severity": "critical"
        },
        "annotations": {
            "summary": "Tasa de errores alta en gateway-hub",
            "description": "La tasa de errores 5xx es 12% en gateway-hub."
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
            "instance": "'"$NODE_INSTANCE"'",
            "service": "node-exporter",
            "severity": "warning"
        },
        "annotations": {
            "summary": "Uso de memoria alto en '"$NODE_INSTANCE"'",
            "description": "El uso de memoria supera el 90% en '"$NODE_INSTANCE"'."
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
            "instance": "'"$NODE_INSTANCE"'",
            "service": "node-exporter",
            "mountpoint": "/",
            "severity": "warning"
        },
        "annotations": {
            "summary": "Espacio en disco bajo en '"$NODE_INSTANCE"'",
            "description": "El espacio disponible en disco es menor al 10% en '"$NODE_INSTANCE"'."
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
            "instance": "'"$PG_INSTANCE"'",
            "service": "postgres",
            "project": "dataengine",
            "severity": "critical"
        },
        "annotations": {
            "summary": "PostgreSQL caido",
            "description": "PostgreSQL en '"$PG_INSTANCE"' no responde."
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
            "instance": "'"$PG_INSTANCE"'",
            "service": "postgres",
            "project": "dataengine",
            "severity": "warning"
        },
        "annotations": {
            "summary": "Demasiadas conexiones en la base de datos",
            "description": "Las conexiones estan al 85% del maximo en '"$PG_INSTANCE"'."
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
