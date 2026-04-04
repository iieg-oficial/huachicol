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
RETENTION_DAYS=30

DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="/tmp/huachicol-backup-${TIMESTAMP}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

cleanup() {
    rm -rf "$BACKUP_DIR" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$BACKUP_DIR"

log "=== Backup del stack de monitoreo ==="

# Respaldar datos de Grafana
log "Respaldando Grafana..."
docker run --rm \
    -v huachicol_grafana_data:/source:ro \
    -v "${BACKUP_DIR}:/backup" \
    alpine tar czf /backup/grafana.tar.gz -C /source .
log "Grafana OK"

# Respaldar Prometheus via snapshot API
log "Creando snapshot de Prometheus..."
SNAPSHOT_RESULT=$(docker exec prometheus wget -q -O - --post-data='' "http://localhost:9090/api/v1/admin/tsdb/snapshot" 2>/dev/null || echo '{"status":"error"}')
if echo "$SNAPSHOT_RESULT" | grep -q '"success"'; then
    SNAPSHOT_NAME=$(echo "$SNAPSHOT_RESULT" | sed 's/.*"name":"\([^"]*\)".*/\1/')
    docker run --rm \
        -v huachicol_prometheus_data:/source:ro \
        -v "${BACKUP_DIR}:/backup" \
        alpine tar czf /backup/prometheus.tar.gz -C "/source/snapshots/${SNAPSHOT_NAME}" .
    docker exec prometheus rm -rf "/prometheus/snapshots/${SNAPSHOT_NAME}" 2>/dev/null || true
    log "Prometheus snapshot OK"
else
    log "WARNING: Snapshot fallo, respaldando TSDB completo..."
    docker run --rm \
        -v huachicol_prometheus_data:/source:ro \
        -v "${BACKUP_DIR}:/backup" \
        alpine tar czf /backup/prometheus.tar.gz -C /source .
    log "Prometheus full backup OK"
fi

# Respaldar Loki
log "Respaldando Loki..."
docker run --rm \
    -v huachicol_loki_data:/source:ro \
    -v "${BACKUP_DIR}:/backup" \
    alpine tar czf /backup/loki.tar.gz -C /source .
log "Loki OK"

# Respaldar configuracion
log "Respaldando configuracion..."
tar czf "${BACKUP_DIR}/config.tar.gz" \
    -C "$PROJECT_DIR" \
    prometheus/prometheus.yml \
    prometheus/rules \
    alertmanager \
    loki \
    tempo \
    grafana/provisioning \
    grafana/dashboards \
    .env.example
log "Config OK"

# Comprimir todo
ARCHIVE="${BACKUP_DIR}/backup-${DATE}.tar.gz"
log "Comprimiendo archivo final..."
tar czf "$ARCHIVE" -C "$BACKUP_DIR" grafana.tar.gz prometheus.tar.gz loki.tar.gz config.tar.gz

# Subir a MinIO
log "Subiendo a MinIO (bucket: ${BUCKET})..."
docker run --rm \
    --network iieg-network \
    -v "${ARCHIVE}:/backup/backup-${DATE}.tar.gz:ro" \
    --entrypoint sh minio/mc -c "
        mc alias set acervo '${MINIO_ENDPOINT}' '${MINIO_BUCKET_USER}' '${MINIO_BUCKET_PASSWORD}' && \
        mc cp /backup/backup-${DATE}.tar.gz acervo/${BUCKET}/monthly/
    "
log "Subida OK"

# Rotacion: eliminar backups mayores a RETENTION_MONTHS meses
log "Rotando backups antiguos (retencion: ${RETENTION_DAYS} dias)..."
docker run --rm \
    --network iieg-network \
    --entrypoint sh minio/mc -c "
        mc alias set acervo '${MINIO_ENDPOINT}' '${MINIO_BUCKET_USER}' '${MINIO_BUCKET_PASSWORD}' && \
        mc rm --recursive --force --older-than ${RETENTION_DAYS}d acervo/${BUCKET}/monthly/ 2>/dev/null || true
    "

log "=== Backup completo ==="
