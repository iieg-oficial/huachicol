#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

ENV_FILE="${ENV_FILE:-.env}"
if [ -f "$PROJECT_DIR/$ENV_FILE" ]; then
    set -a
    . "$PROJECT_DIR/$ENV_FILE"
    set +a
fi

MINIO_ENDPOINT="${MINIO_ENDPOINT:?MINIO_ENDPOINT is required}"
MINIO_BUCKET_USER="${MINIO_BUCKET_USER:?MINIO_BUCKET_USER is required}"
MINIO_BUCKET_PASSWORD="${MINIO_BUCKET_PASSWORD:?MINIO_BUCKET_PASSWORD is required}"
BUCKET="huachicol"

DATE="${1:-}"
COMPONENT="${2:-all}"

if [ -z "$DATE" ]; then
    echo "Uso: $0 <YYYY-MM-DD> [componente]"
    echo ""
    echo "Componentes disponibles:"
    echo "  all         - Restaurar todo (default)"
    echo "  grafana     - Solo datos de Grafana"
    echo "  prometheus  - Solo datos de Prometheus"
    echo "  loki        - Solo datos de Loki"
    echo "  config      - Solo archivos de configuracion"
    echo ""
    echo "Ejemplo: $0 2026-04-03"
    echo "         $0 2026-04-03 grafana"
    exit 1
fi

RESTORE_DIR="/tmp/huachicol-restore-${DATE}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

cleanup() {
    rm -rf "$RESTORE_DIR" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$RESTORE_DIR"

# Descargar backup de MinIO
log "Descargando backup-${DATE}.tar.gz de MinIO..."
docker run --rm \
    --network iieg-network \
    -v "${RESTORE_DIR}:/restore" \
    --entrypoint sh minio/mc -c "
        mc alias set acervo '${MINIO_ENDPOINT}' '${MINIO_BUCKET_USER}' '${MINIO_BUCKET_PASSWORD}' && \
        mc cp acervo/${BUCKET}/monthly/backup-${DATE}.tar.gz /restore/
    "

if [ ! -f "${RESTORE_DIR}/backup-${DATE}.tar.gz" ]; then
    log "ERROR: No se encontro backup-${DATE}.tar.gz en MinIO"
    exit 1
fi

# Extraer archivo principal
log "Extrayendo archivo..."
tar xzf "${RESTORE_DIR}/backup-${DATE}.tar.gz" -C "$RESTORE_DIR"

# Detener servicios antes de restaurar
log "Deteniendo servicios..."
cd "$PROJECT_DIR"
docker compose stop

restore_grafana() {
    if [ ! -f "${RESTORE_DIR}/grafana.tar.gz" ]; then
        log "WARNING: grafana.tar.gz no encontrado, saltando"
        return
    fi
    log "Restaurando Grafana..."
    docker run --rm \
        -v huachicol_grafana_data:/target \
        -v "${RESTORE_DIR}:/restore:ro" \
        alpine sh -c "rm -rf /target/* && tar xzf /restore/grafana.tar.gz -C /target"
    log "Grafana restaurado"
}

restore_prometheus() {
    if [ ! -f "${RESTORE_DIR}/prometheus.tar.gz" ]; then
        log "WARNING: prometheus.tar.gz no encontrado, saltando"
        return
    fi
    log "Restaurando Prometheus..."
    docker run --rm \
        -v huachicol_prometheus_data:/target \
        -v "${RESTORE_DIR}:/restore:ro" \
        alpine sh -c "rm -rf /target/* && tar xzf /restore/prometheus.tar.gz -C /target"
    log "Prometheus restaurado"
}

restore_loki() {
    if [ ! -f "${RESTORE_DIR}/loki.tar.gz" ]; then
        log "WARNING: loki.tar.gz no encontrado, saltando"
        return
    fi
    log "Restaurando Loki..."
    docker run --rm \
        -v huachicol_loki_data:/target \
        -v "${RESTORE_DIR}:/restore:ro" \
        alpine sh -c "rm -rf /target/* && tar xzf /restore/loki.tar.gz -C /target"
    log "Loki restaurado"
}

restore_config() {
    if [ ! -f "${RESTORE_DIR}/config.tar.gz" ]; then
        log "WARNING: config.tar.gz no encontrado, saltando"
        return
    fi
    log "Restaurando configuracion..."
    tar xzf "${RESTORE_DIR}/config.tar.gz" -C "$PROJECT_DIR"
    log "Configuracion restaurada"
}

case "$COMPONENT" in
    all)
        restore_grafana
        restore_prometheus
        restore_loki
        restore_config
        ;;
    grafana)
        restore_grafana
        ;;
    prometheus)
        restore_prometheus
        ;;
    loki)
        restore_loki
        ;;
    config)
        restore_config
        ;;
    *)
        log "ERROR: Componente desconocido: $COMPONENT"
        log "Componentes validos: all, grafana, prometheus, loki, config"
        exit 1
        ;;
esac

# Reiniciar servicios
log "Reiniciando servicios..."
docker compose up -d

log "=== Restore completo (${COMPONENT}) ==="
