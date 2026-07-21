.PHONY: help start stop restart logs clean status network version-json

NETWORK_NAME := iieg-network

help:
	@echo ""
	@echo "Huachicol - Monitor ligero /ontoy"
	@echo "================================="
	@echo ""
	@echo "    make start        - Crear red e iniciar monitor + version-api"
	@echo "    make stop         - Detener"
	@echo "    make restart      - Reiniciar"
	@echo "    make logs         - Ver logs"
	@echo "    make status       - Ver estado"
	@echo "    make clean        - Detener y eliminar datos"
	@echo "    make network      - Crear red compartida ($(NETWORK_NAME))"
	@echo "    make version-json - Regenerar version-api/html/version.json desde VERSION"
	@echo ""

network:
	@docker network inspect $(NETWORK_NAME) >/dev/null 2>&1 \
		|| (docker network create $(NETWORK_NAME) && echo "Red $(NETWORK_NAME) creada") \
		&& echo "Red $(NETWORK_NAME) lista"

start: network version-json
	docker compose up -d --build

stop:
	docker compose down

restart: version-json
	docker compose restart

version-json:
	@SERVICE=huachicol; \
	 VERSION=$$(tr -d '[:space:]' < VERSION); \
	 RELEASED_AT=$$(grep -m1 "^## \[$$VERSION\]" docs/CHANGELOG.md | sed -E 's/^## \[[^]]+\] - ([0-9-]+).*/\1/'); \
	 if [ -z "$$RELEASED_AT" ]; then echo "WARN: no se encontro entrada '## [$$VERSION] - YYYY-MM-DD' en docs/CHANGELOG.md" >&2; fi; \
	 printf '{"version":"%s","service":"%s","released_at":"%s"}\n' "$$VERSION" "$$SERVICE" "$$RELEASED_AT" > version-api/html/version.json; \
	 echo "version.json -> $$VERSION ($$SERVICE, $$RELEASED_AT)"

logs:
	docker compose logs -f

status:
	@docker compose ps

clean:
	docker compose down -v
	@echo "Datos eliminados"
