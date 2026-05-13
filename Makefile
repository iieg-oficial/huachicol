.PHONY: help start stop restart logs clean status \
       agent-start agent-stop agent-restart agent-logs agent-clean agent-status \
       alloy-start alloy-stop alloy-restart alloy-logs alloy-status \
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
	@echo "    make agent-start                - Iniciar agente completo (alloy + cadvisor)"
	@echo "    make agent-start PROFILES=\"telemetry cadvisor\"  - Solo servicios especificos"
	@echo "    make agent-stop                 - Detener agente"
	@echo "    make agent-restart              - Reiniciar agente"
	@echo "    make agent-logs                 - Ver logs del agente"
	@echo "    make agent-status               - Ver estado del agente"
	@echo "    make agent-clean                - Detener agente y eliminar datos"
	@echo "    Profiles: telemetry, cadvisor, postgres"
	@echo ""
	@echo "  Alloy local (logs del propio servidor monitoring):"
	@echo "    make alloy-start   - Iniciar alloy local"
	@echo "    make alloy-stop    - Detener alloy local"
	@echo "    make alloy-restart - Reiniciar alloy local"
	@echo "    make alloy-logs    - Ver logs de alloy local"
	@echo "    make alloy-status  - Ver estado de alloy local"
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

PROFILES ?= all
AGENT_PROFILE_FLAGS := $(foreach p,$(PROFILES),--profile $(p))
AGENT_CMD := docker compose -f $(AGENT_DIR)/docker-compose.yml $(AGENT_PROFILE_FLAGS)

agent-start: network
	@if [ ! -f $(AGENT_DIR)/.env ]; then \
		cp $(AGENT_DIR)/.env.example $(AGENT_DIR)/.env; \
		echo "Archivo $(AGENT_DIR)/.env creado. Configura SERVER_NAME y LOKI_URL antes de continuar."; \
		exit 1; \
	fi
	$(AGENT_CMD) up -d
	@echo "Agente iniciado"

agent-stop:
	$(AGENT_CMD) down

agent-restart:
	$(AGENT_CMD) restart

agent-logs:
	$(AGENT_CMD) logs -f

agent-status:
	@$(AGENT_CMD) ps

agent-clean:
	$(AGENT_CMD) down -v
	@echo "Datos del agente eliminados"

# --- Alloy local ---

alloy-start:
	docker compose up -d alloy
	@echo "Alloy local iniciado"

alloy-stop:
	docker compose stop alloy

alloy-restart:
	docker compose restart alloy

alloy-logs:
	docker compose logs -f alloy

alloy-status:
	@docker compose ps alloy

# --- Backups ---

backup:
	@echo "Ejecutando backup manual..."
	@./scripts/backup.sh

backup-list:
	@echo "Listando backups en MinIO..."
	@bash -c 'set -a; source .env; set +a; docker run --rm --network iieg-network --entrypoint sh minio/mc -c \
		"mc alias set acervo $$MINIO_ENDPOINT $$MINIO_BUCKET_USER $$MINIO_BUCKET_PASSWORD && \
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
