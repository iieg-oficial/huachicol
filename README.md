# IIEG Monitoring Stack

Servidor centralizado de monitoreo y analytics para todos los proyectos.

## Stack Incluido

- **Prometheus** - Métricas y monitoreo
- **Grafana** - Visualización y dashboards
- **AlertManager** - Gestión de alertas
- **Loki** - Logs centralizados
- **Node Exporter** - Métricas del servidor
- **cAdvisor** - Métricas de containers

## Inicio Rápido

```bash
cp .env.example .env
nano .env
make start
```

## Acceso a Servicios

| Servicio | Puerto | URL |
|----------|--------|-----|
| Grafana | 9000 | http://localhost:9000 |
| Prometheus | 9001 | http://localhost:9001 |
| AlertManager | 9002 | http://localhost:9002 |
| Loki | 9003 | http://localhost:9003 |
| cAdvisor | 9011 | http://localhost:9011 |
| Node Exporter | 9010 | http://localhost:9010 |

## Credenciales Default

**Grafana:**
- Usuario: (configurar en .env)
- Password: (configurar en .env)

## Configurar Discord Alerts

1. En Discord: Server Settings → Integrations → Webhooks → New Webhook
2. Copiar webhook URL
3. Agregar al .env: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/ID/TOKEN`
4. Reiniciar: `make restart`
5. Probar: `curl -X POST http://localhost:9094/test`

## Agregar Proyectos

Editar `prometheus/prometheus.yml`:

```yaml
- job_name: 'mi-proyecto'
  static_configs:
    - targets: ['192.168.1.x:9090']
      labels:
        project: 'mi-proyecto'
```

## Comandos

```bash
make start    # Iniciar stack
make stop     # Detener stack
make restart  # Reiniciar stack
make logs     # Ver logs
make clean    # Limpiar datos
```

## Integración con Proyectos

### Backend Node.js

```javascript
const promClient = require('prom-client');
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

app.get('/metrics', async (req, res) => {
	res.set('Content-Type', register.contentType);
	res.end(await register.metrics());
});
```

### Logs con Loki

```javascript
const winston = require('winston');
const LokiTransport = require('winston-loki');

logger.add(new LokiTransport({
	host: 'http://localhost:3100',
	labels: { app: 'mi-proyecto' }
}));
```

## Recursos

- Prometheus: ~500MB RAM
- Grafana: ~200MB RAM
- Loki: ~300MB RAM
- Total: ~1.5GB RAM recomendado

## Retención de Datos

- Prometheus: 30 días
- Loki: 30 días (744h)
