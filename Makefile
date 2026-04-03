.PHONY: help start stop restart logs clean status \
       agent-start agent-stop agent-restart agent-logs agent-clean agent-status \
       network targets backup backup-list restore backup-cron-install backup-cron-remove

NETWORK_NAME := iieg-network
AGENT_DIR := agent

help:
	@echo ""
	@echo "Huachicol - Stack de Monitoreo IIEG"
	@echo "===================================="
	@echo ""
	@echo "  Stack principal:"
	@echo "    make start       - Crear red e iniciar stack completo"
	@echo "    make stop        - Detener stack"
	@echo "    make restart     - Reiniciar stack"
	@echo "    make logs        - Ver logs del stack"
	@echo "    make status      - Ver estado de servicios"
	@echo "    make clean       - Detener y eliminar datos"
	@echo ""
	@echo "  Agente (servidores remotos):"
	@echo "    make agent-start   - Iniciar agente huachicol"
	@echo "    make agent-stop    - Detener agente"
	@echo "    make agent-restart - Reiniciar agente"
	@echo "    make agent-logs    - Ver logs del agente"
	@echo "    make agent-status  - Ver estado del agente"
	@echo "    make agent-clean   - Detener agente y eliminar datos"
	@echo ""
	@echo "  Backups:"
	@echo "    make backup              - Ejecutar backup manual a MinIO"
	@echo "    make backup-list         - Listar backups disponibles en MinIO"
	@echo "    make restore DATE=YYYY-MM-DD                - Restaurar todo"
	@echo "    make restore DATE=YYYY-MM-DD COMPONENT=grafana  - Restaurar solo Grafana"
	@echo "    make backup-cron-install - Instalar cron semanal (domingos, 3AM)"
	@echo "    make backup-cron-remove  - Desinstalar cron de backup"
	@echo ""
	@echo "  Targets:"
	@echo "    make targets     - Regenerar targets de Prometheus desde .env"
	@echo ""
	@echo "  Red:"
	@echo "    make network     - Crear red compartida ($(NETWORK_NAME))"
	@echo ""

# --- Red compartida ---

network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 \
		|| (docker network create $(NETWORK_NAME) && echo "Red $(NETWORK_NAME) creada") \
		&& echo "Red $(NETWORK_NAME) lista"

# --- Targets ---

targets:
	@./scripts/generate-targets.sh
	@echo "Prometheus recargara los targets en ~30s (file_sd_configs)"

# --- Maestro ---

start: network
	./scripts/start.sh

stop:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

status:
	@docker compose ps

clean:
	docker compose down -v
	@echo "Datos del maestro eliminados"

# --- Agente ---

agent-start: network
	@if [ ! -f $(AGENT_DIR)/.env ]; then \
		cp $(AGENT_DIR)/.env.example $(AGENT_DIR)/.env; \
		echo "Archivo $(AGENT_DIR)/.env creado. Configura SERVER_NAME y LOKI_URL antes de continuar."; \
		exit 1; \
	fi
	docker compose -f $(AGENT_DIR)/docker-compose.yml up -d
	@echo "Agente iniciado"

agent-stop:
	docker compose -f $(AGENT_DIR)/docker-compose.yml down

agent-restart:
	docker compose -f $(AGENT_DIR)/docker-compose.yml restart

agent-logs:
	docker compose -f $(AGENT_DIR)/docker-compose.yml logs -f

agent-status:
	@docker compose -f $(AGENT_DIR)/docker-compose.yml ps

agent-clean:
	docker compose -f $(AGENT_DIR)/docker-compose.yml down -v
	@echo "Datos del agente eliminados"

# --- Backups ---

backup:
	@echo "Ejecutando backup manual..."
	@./scripts/backup.sh

backup-list:
	@echo "Listando backups en MinIO..."
	@bash -c 'set -a; source .env; set +a; docker run --rm --network iieg-network --entrypoint sh minio/mc -c \
		"mc alias set acervo $$MINIO_ENDPOINT $$MINIO_ACCESS_KEY $$MINIO_SECRET_KEY && \
		 mc ls acervo/huachicol/monthly/"'

restore:
	@if [ -z "$(DATE)" ]; then \
		echo "Uso: make restore DATE=YYYY-MM-DD [COMPONENT=all|grafana|prometheus|loki|config]"; \
		exit 1; \
	fi
	@./scripts/restore.sh $(DATE) $(or $(COMPONENT),all)

backup-cron-install:
	@crontab -l 2>/dev/null | grep -v 'huachicol.*backup' | cat - scripts/backup-cron | crontab -
	@echo "Cron de backup instalado (domingos a las 3:00 AM)"

backup-cron-remove:
	@crontab -l 2>/dev/null | grep -v 'huachicol.*backup' | crontab -
	@echo "Cron de backup removido"
