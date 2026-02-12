#!/bin/bash

SERVICE=${1:-}

if [ -z "$SERVICE" ]; then
	docker compose logs -f
else
	docker compose logs -f "$SERVICE"
fi
