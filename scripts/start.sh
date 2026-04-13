#!/bin/bash

if [ ! -f .env ]; then
	echo "Creating .env from .env.example..."
	cp .env.example .env
	echo "Please edit .env with your configuration"
	exit 1
fi

echo "Generating target files..."
./scripts/generate-targets.sh

echo "Starting monitoring stack..."
docker compose up -d

echo "Waiting for services to start..."
sleep 10

echo "Services started:"
echo "  Grafana: http://localhost:9000"
echo "  Prometheus: http://localhost:9001"
echo "  AlertManager: http://localhost:9002"
echo "  Loki: http://localhost:9003"
echo "  Node Exporter: http://localhost:9010"
echo "  cAdvisor: http://localhost:9011"
echo "  Prometheus (auth): http://localhost:9091"
echo "  Loki (auth): http://localhost:3101"
