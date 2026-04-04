# IIEG Monitoring Stack

Servidor centralizado de monitoreo y observabilidad para todos los proyectos del IIEG.

## Stack

- **Prometheus** — Metricas y monitoreo
- **Grafana** — Dashboards
- **AlertManager** — Alertas a Discord
- **Loki** — Logs centralizados
- **Tempo** — Distributed tracing
- **Node Exporter** — Metricas del servidor
- **cAdvisor** — Metricas de contenedores

## Inicio Rapido

```bash
cp .env.example .env
nano .env            # Configurar variables
make start
```

## Servicios

| Servicio | Puerto | URL |
|----------|--------|-----|
| Grafana | 9000 | http://localhost:9000 |
| Prometheus | 9001 | http://localhost:9001 |
| Prometheus (auth) | 9091 | http://localhost:9091 |
| AlertManager | 9002 | http://localhost:9002 |
| Loki | 9003 | http://localhost:9003 |
| Loki (auth) | 3101 | http://localhost:3101 |
| Tempo | 9004 | http://localhost:9004 |
| Node Exporter | 9010 | http://localhost:9010 |
| cAdvisor | 9011 | http://localhost:9011 |

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
make backup              # Backup manual a MinIO
make backup-cron-install # Cron mensual (dia 1, 3AM)
make backup-cron-remove  # Remover cron
```

## Configurar Alertas Discord

1. Discord: Server Settings > Integrations > Webhooks > New Webhook
2. Copiar URL y agregar `/slack` al final
3. Poner en .env: `DISCORD_WEBHOOK_URL=<TU_WEBHOOK_URL>/slack`
4. `make restart`

## Agregar Proyecto

Editar `prometheus/prometheus.yml`:

```yaml
- job_name: 'mi-proyecto'
  static_configs:
    - targets: ['<SERVER_IP>:9090']
      labels:
        project: 'mi-proyecto'
```

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
| Loki | 30 dias |
| Tempo | 7 dias |
| Backups | 3 meses |
