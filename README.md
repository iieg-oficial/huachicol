# huachicol

Monitoreo y alertas del ecosistema IIEG. Sondea el `/ontoy` de cada servicio, guarda el estado en
SQLite y notifica a Discord y Telegram con histeresis.

**Desde 2.0.0 (2026-07-21) es un monitor ligero, no un stack de observabilidad.** Prometheus,
Grafana, Alertmanager, Loki, Alloy, node-exporter, cAdvisor, `nginx-auth` y el agente remoto se
retiraron por completo. El punto de retorno con el stack anterior es el tag `v1.23.0`; como estaba
armado quedo documentado en el repositorio central de contexto (`historial/`).

## Requisitos

- Docker >= v28 y Docker Compose >= v2.36
- La red externa `iieg-network`, que gestiona gateway-hub (`make network` la crea si falta)

## Puesta en marcha

```bash
cp .env.example .env
nano .env                 # webhook de Discord, token de Telegram, umbrales
make start
```

## Comandos

**Este repo no tiene `deploy` ni `up`:** sus targets son distintos al resto del ecosistema.

```bash
make start        # crear la red e iniciar
make stop
make restart
make network      # crear iieg-network
make version-json # regenerar el payload de /ontoy
make logs
make status
make clean        # detener y eliminar datos
```

## Servicios

| Servicio | Contenedor | Funcion |
|----------|------------|---------|
| `monitor` | `huachicol-monitor` | Sondea, guarda estado y alerta. API en `${BIND_ADDR}:${MONITOR_API_PORT}` (8090, solo local) |
| `version-api` | `huachicol-version-api` | Sidecar que expone el `/ontoy` del propio repo en `:8088` |

## Variables de entorno

Todas vienen del `.env`; el compose falla si falta alguna.

| Variable | Para que |
|----------|----------|
| `BIND_ADDR` | Interfaz donde escucha la API del monitor (`127.0.0.1`) |
| `MONITOR_POLL_INTERVAL` | Segundos entre sondeos (60) |
| `MONITOR_FAILURE_THRESHOLD` | Fallos seguidos antes de alertar (3) |
| `MONITOR_RECOVERY_THRESHOLD` | Sondeos correctos para declarar recuperacion |
| `MONITOR_HISTORY_RETENTION_DAYS` | Retencion del historial en SQLite |
| `MONITOR_REMINDER_HOURS` | Cada cuanto recordar un servicio que sigue caido |
| `MONITOR_ENVIRONMENT` | Etiqueta del entorno en los mensajes |
| `MONITOR_API_PORT` | Puerto de la API interna (8090) |
| `MONITOR_DEADMAN_URL` | Receptor del dead-man's switch; vacio lo desactiva |
| `MONITOR_DEPLOY_TIMEOUT` | Expiracion de la ventana de despliegue (900 s) |
| `MONITOR_DISCORD_WEBHOOK_URL` | Webhook del canal de alertas |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Canal alterno de alertas |

## Que se monitorea

Los servicios sondeados viven en `monitor/targets.json` (hoy son 8), que se monta como **bind**: al
editarlo hay que **recrear** el contenedor, no basta `restart`.

```bash
docker compose up -d --force-recreate monitor
```

`monitor/targets.example.json` es la plantilla. Agregar un servicio es agregar su entrada con el URL
de su `/ontoy`: no hace falta que exponga metricas ni que instale nada, que es justo lo que hacia
pesado el modelo anterior.

## Ventana de despliegue

Antes de tocar produccion, abrir la ventana para que las alertas en cascada no suenen:

```bash
curl -X POST http://<monitor>:8090/api/deploy/start
# ... desplegar ...
curl -X POST http://<monitor>:8090/api/deploy/end
```

Expira sola tras `MONITOR_DEPLOY_TIMEOUT`.

## Documentacion

- [Monitor](monitor/README.md) — detalle operativo del monitor: histeresis, eventos, SQLite
- [CHANGELOG](docs/CHANGELOG.md) — serie 2.x; el historico 1.x en [changelog/v1.md](docs/changelog/v1.md)

El contexto, el contrato `/ontoy` que consume el monitor y los pendientes viven en el repositorio
central de contexto (`repos/huachicol/`). Los planes cerrados y el stack 1.x retirado, en
`historial/`.
