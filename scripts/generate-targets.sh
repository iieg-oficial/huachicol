#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TARGETS_DIR="${PROJECT_DIR}/prometheus/targets"

if [ ! -f "${PROJECT_DIR}/.env" ]; then
    echo "Error: .env not found"
    exit 1
fi

set -a
. "${PROJECT_DIR}/.env"
set +a

# Helper: agrega un target al JSON si la variable no esta vacia
add_target() {
    local target="$1" label_key="$2" label_val="$3" extra_labels="${4:-}"
    if [ -n "$target" ]; then
        if [ "$FIRST" = "false" ]; then printf ',\n'; fi
        printf '  {\n    "targets": ["%s"],\n    "labels": { "%s": "%s"%s }\n  }' \
            "$target" "$label_key" "$label_val" "$extra_labels"
        FIRST=false
    fi
}

ALLOY_NODE_PATH='/api/v0/component/prometheus.exporter.unix.host/metrics'
ALLOY_PORT=12345

# --- node-exporter targets ---
FIRST=false
{
    printf '[\n  {\n    "targets": ["node-exporter:9100"],\n    "labels": { "server": "monitoring" }\n  }'
    PORTAL_IP="${PORTAL_SERVER_IP:-}"
    MAPALAB_IP="${MAPALAB_SERVER_IP:-}"
    MARIACHI_IP="${MARIACHI_SERVER_IP:-}"
    GEOSERVER_IP="${GEOSERVER_SERVER_IP:-}"
    DATAENGINE_IP="${DATAENGINE_SERVER_IP:-}"
    REMOTE_PATH_EXTRA=", \"__metrics_path__\": \"${ALLOY_NODE_PATH}\""
    add_target "${PORTAL_IP:+${PORTAL_IP}:${ALLOY_PORT}}" "server" "portal" "${REMOTE_PATH_EXTRA}"
    add_target "${MAPALAB_IP:+${MAPALAB_IP}:${ALLOY_PORT}}" "server" "mapalab" "${REMOTE_PATH_EXTRA}"
    add_target "${MARIACHI_IP:+${MARIACHI_IP}:${ALLOY_PORT}}" "server" "mariachi" "${REMOTE_PATH_EXTRA}"
    add_target "${GEOSERVER_IP:+${GEOSERVER_IP}:${ALLOY_PORT}}" "server" "geoserver" "${REMOTE_PATH_EXTRA}"
    add_target "${DATAENGINE_IP:+${DATAENGINE_IP}:${ALLOY_PORT}}" "server" "dataengine" "${REMOTE_PATH_EXTRA}"
    printf '\n]\n'
} > "${TARGETS_DIR}/node-exporter.json"
echo "Generated node-exporter.json"

# --- cadvisor targets ---
FIRST=false
{
    printf '[\n  {\n    "targets": ["cadvisor:8080"],\n    "labels": { "server": "monitoring" }\n  }'
    add_target "${PORTAL_IP:+${PORTAL_IP}:8080}" "server" "portal"
    add_target "${MAPALAB_IP:+${MAPALAB_IP}:8080}" "server" "mapalab"
    add_target "${MARIACHI_IP:+${MARIACHI_IP}:8080}" "server" "mariachi"
    add_target "${GEOSERVER_IP:+${GEOSERVER_IP}:8080}" "server" "geoserver"
    add_target "${DATAENGINE_IP:+${DATAENGINE_IP}:8080}" "server" "dataengine"
    printf '\n]\n'
} > "${TARGETS_DIR}/cadvisor.json"
echo "Generated cadvisor.json"

# --- projects targets ---
FIRST=true
{
    printf '['
    add_target "${URLSCHIQUITAS_BACKEND_TARGET:-}" "project" "urlschiquitas" ', "service": "backend"'
    add_target "${URLSCHIQUITAS_POSTGRES_TARGET:-}" "project" "urlschiquitas" ', "service": "postgres"'
    add_target "${MAPALAB_BACKEND_TARGET:-}" "project" "mapalab" ', "service": "backend"'
    add_target "${MARIACHI_BACKEND_TARGET:-}" "project" "mariachi" ', "service": "backend"'
    add_target "${GATEWAY_NGINX_TARGET:-}" "project" "gateway-hub" ', "service": "nginx"'
    printf '\n]\n'
} > "${TARGETS_DIR}/projects.json"
echo "Generated projects.json"

# --- postgres-exporter targets (agente, usa /huachicol) ---
FIRST=true
{
    printf '['
    add_target "${DATAENGINE_POSTGRES_TARGET:-}" "project" "dataengine" ', "service": "postgres"'
    printf '\n]\n'
} > "${TARGETS_DIR}/postgres-exporter.json"
echo "Generated postgres-exporter.json"

# --- minio targets (endpoint especial /minio/v2/metrics/cluster) ---
FIRST=true
{
    printf '['
    add_target "${ACERVO_MINIO_TARGET:-}" "project" "acervo" ', "service": "minio"'
    printf '\n]\n'
} > "${TARGETS_DIR}/minio.json"
echo "Generated minio.json"

# --- minio token ---
printf '%s' "${ACERVO_MINIO_TOKEN:-}" > "${TARGETS_DIR}/minio-token"
echo "Generated minio-token"
