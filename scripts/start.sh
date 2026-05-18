#!/bin/bash
set -euo pipefail

if [ ! -f .env ]; then
	echo "Creating .env from .env.example..."
	cp .env.example .env
	echo "Please edit .env with your configuration"
	exit 1
fi

set -a
. ./.env
set +a

echo "Generating target files..."
./scripts/generate-targets.sh

echo "Starting monitoring stack..."
docker compose up -d

echo "Waiting for services to start..."
sleep 10

echo "Services started:"
echo "  Grafana:           http://localhost:${GRAFANA_PORT}"
echo "  Prometheus:        http://localhost:${PROMETHEUS_PORT}"
echo "  AlertManager:      http://localhost:${ALERTMANAGER_PORT}"
echo "  Loki:              http://localhost:${LOKI_PORT}"
echo "  Node Exporter:     http://localhost:${NODE_EXPORTER_PORT}"
echo "  cAdvisor:          http://localhost:${CADVISOR_PORT}"
echo "  Prometheus (auth): http://localhost:${PROMETHEUS_AUTH_PORT}"
echo "  Loki (auth):       http://localhost:${LOKI_AUTH_PORT}"
