.PHONY: help start stop restart logs clean status \
       agent-start agent-stop agent-restart agent-logs agent-clean agent-status \
       network test-alert test-alerts alert-list

NETWORK_NAME := iieg-network
AGENT_DIR := agent

help:
	@echo ""
	@echo "Monitoring Stack"
	@echo "================"
	@echo ""
	@echo "  Maestro (stack completo):"
	@echo "    make start       - Crear red e iniciar stack completo"
	@echo "    make stop        - Detener stack"
	@echo "    make restart     - Reiniciar stack"
	@echo "    make logs        - Ver logs del stack"
	@echo "    make status      - Ver estado de servicios"
	@echo "    make clean       - Detener y eliminar datos"
	@echo ""
	@echo "  Agente (servidores remotos):"
	@echo "    make agent-start   - Iniciar agente de monitoreo"
	@echo "    make agent-stop    - Detener agente"
	@echo "    make agent-restart - Reiniciar agente"
	@echo "    make agent-logs    - Ver logs del agente"
	@echo "    make agent-status  - Ver estado del agente"
	@echo "    make agent-clean   - Detener agente y eliminar datos"
	@echo ""
	@echo "  Alertas:"
	@echo "    make test-alert ALERT=service-down  - Probar una alerta especifica"
	@echo "    make test-alerts                    - Probar todas las alertas"
	@echo "    make alert-list                     - Ver alertas activas"
	@echo ""
	@echo "  Red:"
	@echo "    make network     - Crear red compartida ($(NETWORK_NAME))"
	@echo ""

# --- Red compartida ---

network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 \
		|| (docker network create $(NETWORK_NAME) && echo "Red $(NETWORK_NAME) creada") \
		&& echo "Red $(NETWORK_NAME) lista"

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

# --- Alertas ---

test-alert:
	@./scripts/test-alerts.sh $(ALERT)

test-alerts:
	@./scripts/test-alerts.sh all

alert-list:
	@./scripts/test-alerts.sh list
