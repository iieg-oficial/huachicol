# IIEG Monitoring Stack

Servidor centralizado de monitoreo y observabilidad para todos los proyectos del IIEG.

## Stack

- **Prometheus** — Metricas y monitoreo
- **Grafana** — Dashboards
- **AlertManager** — Alertas a Discord
- **Loki** — Logs centralizados
- **Node Exporter** — Metricas del servidor
- **cAdvisor** — Metricas de contenedores

## Inicio Rapido

```bash
cp .env.example .env
nano .env            # Configurar variables
make start
```

## Servicios

Puertos por defecto (configurables en `.env`). Los marcados como *solo local* escuchan
en `BIND_ADDR` (`127.0.0.1`): no son alcanzables desde otro host, el acceso remoto
autenticado va por nginx-auth.

| Servicio | Puerto | Alcance |
|----------|--------|---------|
| Grafana | 3000 | Expuesto (via gateway, `/huachicol/`) |
| Prometheus | 9090 | Solo local |
| Prometheus (auth) | 9091 | Expuesto — nginx-auth |
| AlertManager | 9002 | Solo local |
| Loki | 9003 | Expuesto — push de agentes |
| Loki (auth) | 3101 | Expuesto — nginx-auth |
| Node Exporter | 9010 | Solo local |
| cAdvisor | 9011 | Solo local |

## Comandos

```bash
# Stack principal
make start       # Crear red e iniciar stack
make stop        # Detener
make restart     # Reiniciar
make logs        # Ver logs
make status      # Ver estado
make clean       # Detener y eliminar datos

# Agente remoto
make agent-start   # Iniciar agente en servidor remoto
make agent-stop    # Detener agente

# Backups
make backup              # Backup manual a Acervo (S3)
make backup-list         # Listar backups disponibles
make restore DATE=YYYY-MM-DD [COMPONENT=grafana|prometheus|loki|config]
make backup-cron-install # Cron semanal (domingos, 3AM)
make backup-cron-remove  # Remover cron
```

## Configurar Alertas Discord

1. Discord: Server Settings > Integrations > Webhooks > New Webhook
2. Copiar URL y agregar `/slack` al final
3. Poner en .env: `DISCORD_WEBHOOK_URL=<TU_WEBHOOK_URL>/slack`
4. `make restart`

## Agregar Proyecto

Los targets se generan desde el `.env`, no se editan a mano en `prometheus.yml`:

```bash
# 1. Definir el target en .env y .env.example (formato host:puerto)
MIAPP_BACKEND_TARGET=host.docker.internal:8080

# 2. Registrar la linea add_target en scripts/generate-targets.sh
# 3. Regenerar (Prometheus lo recoge en ~30s via file_sd)
make targets
```

Guia completa: [docs/agregar-proyecto.md](docs/agregar-proyecto.md)

## Integracion con Backends

### Metricas (Prometheus)

```javascript
const promClient = require('prom-client');
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});
```

### Logs (Loki)

```javascript
const winston = require('winston');
const LokiTransport = require('winston-loki');

logger.add(new LokiTransport({
  host: 'http://localhost:3100',
  labels: { app: 'mi-proyecto' }
}));
```

## Documentacion

- [Onboarding agente](docs/onboarding-agente.md) — Desplegar agente en servidor nuevo
- [Pendientes](docs/pendientes/) — Mejoras planeadas (Authentik, gateway)

## Retencion de Datos

| Servicio | Retencion |
|----------|-----------|
| Prometheus | 30 dias |
| Loki | 30 dias (744h) |
| Backups | 30 dias en Acervo (bucket huachicol), semanal |
