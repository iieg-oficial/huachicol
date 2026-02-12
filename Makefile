.PHONY: help start stop restart logs clean

help:
	@echo "Monitoring Stack - Available commands:"
	@echo "  make start     - Start all monitoring services"
	@echo "  make stop      - Stop all services"
	@echo "  make restart   - Restart all services"
	@echo "  make logs      - View logs from all services"
	@echo "  make clean     - Stop and remove all data"

start:
	./scripts/start.sh

stop:
	./scripts/stop.sh

restart:
	docker compose restart

logs:
	docker compose logs -f

clean:
	docker compose down -v
	@echo "All data removed"
