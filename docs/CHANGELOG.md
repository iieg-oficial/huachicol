# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El
versionado del repo `huachicol` es independiente del de las imagenes de Prometheus,
Grafana, Loki, Alertmanager y cAdvisor; aqui registramos los cambios sobre la
configuracion del stack, dashboards, alertas, agente remoto y el webhook de Discord.
Bumps por caracteristica registrada en commit. Considerando 1.x desde que el repo
salio a production con el commit inicial del stack de monitoreo.

## [No publicado]

---

## [1.17.0] - 2026-05-11

### Cambiado
- **Agente remoto: Promtail y node-exporter reemplazados por Grafana Alloy v1.16.1**. Motivacion: Promtail entro en EOL en marzo 2026 (auditoria externa lo marca como deuda tecnica). Se aprovecha la migracion para consolidar node-exporter en el mismo binario.
  - Nuevo archivo `agent/config.alloy` con: `loki.source.docker` (logs de containers via socket Docker), `loki.source.file` (syslog), `loki.write` (push a Loki central), y `prometheus.exporter.unix` (metricas host).
  - `agent/docker-compose.yml`: services `promtail` y `node-exporter` reemplazados por `alloy`. Imagen `grafana/alloy:v1.16.1`. Volumen `promtail_positions` reemplazado por `alloy_data`.
  - Profiles del agente reorganizados: `all` (alloy + cadvisor), `telemetry` (solo alloy), `cadvisor`, `postgres`. Profiles previos `node` y `promtail` removidos.
  - `prometheus.yml` sin cambios estructurales: el job `node-exporter` mantiene path `/huachicol` para el server `monitoring` (sigue usando node-exporter standalone en el stack central), y cada target remoto override su path con `__metrics_path__: /api/v0/component/prometheus.exporter.unix.host/metrics` en `node-exporter.json` (generado por `scripts/generate-targets.sh`).
  - `scripts/generate-targets.sh`: targets remotos de node-exporter ahora apuntan a `:12345` con `__metrics_path__` por target.
  - `agent/.env.example`: `NODE_EXPORTER_PORT` removido, `ALLOY_PORT` agregado (default 12345).
  - Documentacion actualizada: `docs/context.md`, `docs/onboarding-agente.md`, `docs/pendientes/alloy-migration.md`, `docs/pendientes/gateway-improvements.md`.

### Corregido
- **`alertmanager-discord` quedaba aislado en la red `huachicol_default`** (sin bloque `networks` en `docker-compose.yml`) mientras el resto del stack vive en `huachicol_monitoring`. `alertmanager` no podia resolver `alertmanager-discord` por DNS (`NXDOMAIN`), las alertas reintentaban 7-8 veces y se dropeaban silenciosamente. Bug detectado por el dashboard nuevo de containers al ver los errores de `dispatch.go` en logs de `alertmanager`. Fix: agregar `networks: [monitoring]` al service.

### Agregado
- **Dashboard `Contenedores - Vista Detallada`** (`grafana/dashboards/infrastructure/containers.json`): vista unificada con stats de resumen, inventario de containers (tabla con CPU+memoria desde cAdvisor y rate de logs desde Loki), timeseries de CPU/memoria/red por container, volumen de logs por container, y panel de logs en vivo filtrable. Variable `$container` multi-select.
- **Env vars de Grafana para reducir carga inicial** (`docker-compose.yml`): `GF_PLUGINS_DISABLE_PLUGINS` para los 4 plugins de drilldown que Grafana 12 precarga (`grafana-exploretraces-app`, `grafana-lokiexplore-app`, `grafana-metricsdrilldown-app`, `grafana-pyroscope-app`), `GF_FEATURE_TOGGLES_DISABLE=preinstallAutoUpdate,dashgpt`, y `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` apuntando al `general/home.json`. Reduce ~10 requests innecesarias al cargar la UI. El problema raiz (rate limit del gateway) queda documentado en `docs/pendientes/gateway-improvements.md` punto 3.

### Cambiado
- **Provisioning de dashboards reorganizado**: provider `default` renombrado a `general` y apuntando a `dashboards/general/` (donde se movieron `home.json` y `gateway-subroutes.json`). Antes el provider escaneaba la raiz e incluia recursivamente las subcarpetas `projects/` e `infrastructure/`, generando duplicados que impedian a Grafana guardar updates de los dashboards.

### Pendiente (fases posteriores documentadas en `docs/pendientes/alloy-migration.md`)
- Fase 2: consolidar cAdvisor y postgres-exporter en Alloy (queda 1 solo servicio en el agente).
- Fase 3: migrar a modelo push con `prometheus.remote_write` para resolver dependencia de firewall GCP.

---

## [1.16.1] - 2026-04-28

### Corregido
- **Healthcheck de `alertmanager-discord` siempre `unhealthy`**: el test apuntaba a `http://localhost:9093/-/healthy` pero `9093` es el puerto de `alertmanager`, no de `alertmanager-discord` (que escucha en `9094`). Ademas el container alpine no resolvia `localhost` (solo `127.0.0.1`). Como el `server.py` de discord-webhook solo expone `do_POST`, no hay endpoint GET para `wget --spider`; cambiado a un TCP socket check con `python3 -c "import socket; socket.create_connection(('127.0.0.1', 9094), timeout=3).close()"` (Python ya esta en la imagen). Verifica que el server este aceptando conexiones, suficiente como liveness.

---

## [1.16.0] - 2026-04-28

### Agregado
- **Configuracion del proyecto `mariachi-api` en el stack de monitoreo**: targets, dashboards y documentacion para que Prometheus scrappee metricas y Loki recolecte logs del backend de mariachi.

---

## [1.15.0] - 2026-04-14

### Cambiado
- **Rate limiting diferenciado en gateway**: zonas separadas (`api`, `general`, `download`, `console`) con limits y bursts ajustados por tipo de endpoint.
- **Asset caching** para `js`/`css`/`woff2`/`png`/`svg` con `expires 1y` + `Cache-Control: public, immutable`.
- **`cAdvisor` resource limits** en compose: `mem_limit: 256m` y `cpus: 0.25` para evitar que devore CPU del host.

---

## [1.14.0] - 2026-04-13

### Agregado
- **`DATAENGINE_SERVER_IP`** env var en target generation: permite agregar el server de DataEngine como target separado (Prometheus + Loki) sin reescribir los JSONs manualmente. Scripts de generacion de targets actualizados.

### Eliminado
- **Tempo** (tracing service): no se uso en production y agregaba 2GB+ de uso de disco. Removido del compose, configs y datasource de Grafana.

---

## [1.13.0] - 2026-04-04

### Cambiado
- **cAdvisor**: serie de fixes para que funcione consistente en hosts con docker reciente:
  - `cgroup` volume mount path actualizado a `/sys/fs/cgroup`.
  - Docker socket volume mount cambiado a read-write (algunas operaciones lo requieren).
  - `containerd` socket path agregado (cAdvisor lo usa para metricas de contenedores).
  - Image: `v0.55.1` con `ghcr.io` registry (previo `0.52.1`/`0.56.2` tenian regresiones).
  - Removidos flags deprecated.

---

## [1.12.0] - 2026-04-04

### Agregado
- **Docker compose profiles** en agent (`node`, `cadvisor`, `promtail`, `postgres`): permite habilitar selectivamente que servicios corren en cada server remoto. `make agent-start PROFILES="node cadvisor"` arranca solo los seleccionados.
- **Docker-only mode** y **container label storage** en agent configurations: cAdvisor scrap solo containers (no procesos del host) y guarda labels para correlacion en Grafana.
- **Environment configuration guide** documentando cada profile y sus envs.

---

## [1.11.0] - 2026-04-04

### Cambiado
- **Grafana sub-path routing**: configuracion para que Grafana sirva en `/huachicol/` (no en root) sin perder paths internos.
- **MinIO bucket-specific creds**: en lugar de usar root credentials para acceso a Loki/backups, ahora se usan credenciales por bucket via `ACERVO_*_ACCESS_KEY`/`ACERVO_*_SECRET_KEY`.

---

## [1.10.0] - 2026-04-03

### Cambiado
- **Overhaul completo del stack de monitoreo**: nuevos backup scripts (Prometheus snapshots + Loki bucket sync hacia acervo MinIO), auth proxy intermedio (`nginx-auth` con basic auth para Loki + Prometheus), documentacion expandida en `docs/` con runbooks de incidentes y arquitectura del stack.

---

## [1.9.0] - 2026-03-25

### Agregado
- **`acervo-minio` job en Prometheus**: scraping de metricas del MinIO de acervo para alertas sobre uso de disco, errores de S3 y rate de uploads.

---

## [1.8.0] - 2026-03-25

### Agregado
- **Discord webhook custom Python** (`alertmanager/discord-webhook/server.py`): replace de `discord.sh` (bash) por un servidor Python que parsea el payload de Alertmanager y arma embeds Discord ricos (color por severity, title/description localizadas a Espanol, links a Grafana/Prometheus). Endpoint dedicado en puerto `9094`.
- **Logging de errores HTTP** del webhook + Python output unbuffered (logs en tiempo real).
- **`User-Agent` header** en requests salientes a Discord (el de `urllib` default era genrico).
- **`docs/discord.md`** con setup + testing + scripts de prueba (`scripts/test-discord-alert.sh`).
- **`scripts/test-discord-alert.sh`** — payload de Alertmanager v2 simulado para validar el webhook end-to-end.

### Cambiado
- **Alertas localizadas a Espanol**: titulos y descripciones generadas dinamicamente en Espanol; severities mapeadas a colores Discord (red=critical, yellow=warning, green=resolved).
- **`ServiceDown` alert delay** aumentado para reducir false positives durante deploys.

### Eliminado
- Test payload + endpoint de prueba del webhook (no debian estar en production).

---

## [1.7.0] - 2026-03-24

### Agregado
- **`alertmanager-discord` proxy service** integrado en el compose: reemplaza el receiver `discord_*` directo de Alertmanager con un servicio intermedio que enriquece el payload antes de enviar a Discord.
- Receiver de Alertmanager consolidado en uno generico que apunta al webhook custom.
- Image inicial: `benjojo/alertmanager-discord` (luego reemplazada por la implementacion Python en `1.8.0`).

---

## [1.6.0] - 2026-03-24

### Agregado
- **Dashboard de Grafana para Gateway Hub** (`grafana/dashboards/gateway-hub.json`): metricas de requests/sec, status codes (2xx/4xx/5xx), latencias p50/p95/p99, top URIs, top user-agents, logs de errores via Loki.
- Provisioning automatico de dashboards via `grafana/provisioning/dashboards/`.

### Cambiado
- Estructura del JSON del dashboard: removido el wrapper `dashboard` y `overwrite` para que Grafana lo importe directo.
- Volume mounts y paths de provisioning simplificados.

---

## [1.5.0] - 2026-03-24

### Eliminado
- **Tempo (tracing)**: removido del stack inicial. La complejidad de instrumentar OpenTelemetry en cada servicio del ecosistema no justificaba el costo de infra. Configuracion residual de `block duration` y `retention` se limpio del compose y de los configs.

---

## [1.4.0] - 2026-03-24

### Agregado
- **Grafana sub-path** (`/huachicol/`): config para servir Grafana detras de gateway-hub via subpath en lugar de subdomain.
- **`iieg-network`** (network external) — Grafana se conecta para que gateway pueda hacer proxy.
- **Env vars para puertos** de cada servicio del stack (Prometheus, Grafana, Alertmanager, Loki) sourcing desde `.env`.
- **Custom path scraping** para metricas de Grafana en Prometheus (no usa default `/metrics`).

---

## [1.3.0] - 2026-03-24

### Eliminado
- **Matomo** (analytics on-prem): nunca se uso despues del setup inicial; la analytics se maneja ahora via GTM/GA4 desde gateway-hub. Removidos servicios, configs y env vars.

---

## [1.2.0] - 2026-03-24

### Agregado
- **Agente de monitoreo remoto** (`agent/`): stack reducido (Node Exporter + cAdvisor + Promtail) que se despliega en servers remotos del ecosistema. El stack principal en `monitoring` los detecta via file-based service discovery (`prometheus/targets/*.json`) y scrap-ea sus metricas + logs.
- **Comandos `make` para el agente**: `agent-start`, `agent-stop`, `agent-restart`, `agent-logs`, `agent-status`, `agent-clean`.
- Estructura completa del Makefile expandida para diferenciar stack principal vs agente remoto.

---

## [1.1.0] - 2026-02-12

### Agregado
- **Stack de monitoreo completo via Docker Compose**: Prometheus + Grafana + Alertmanager + Loki + Tempo. Configuraciones iniciales en `prometheus/`, `grafana/`, `alertmanager/`, `loki/` y `tempo/`. Network compartida para la comunicacion intra-stack.

---

## [1.0.0] - 2025-11-13

Primera version del repo `huachicol` en production.

### Agregado
- Inicializacion del repositorio.
- Estructura base del proyecto.
