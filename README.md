# IIEG Monitoring Stack

Servidor centralizado de monitoreo y analytics para todos los proyectos.

## Stack Incluido

- **Prometheus** - Métricas y monitoreo
- **Grafana** - Visualización y dashboards
- **AlertManager** - Gestión de alertas
- **Loki** - Logs centralizados
- **Tempo** - Distributed tracing
- **Matomo** - Analytics de usuarios
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
| Tempo | 9004 | http://localhost:9004 |
| Matomo | 9009 | http://localhost:9009 |
| cAdvisor | 9011 | http://localhost:9011 |
| Node Exporter | 9010 | http://localhost:9010 |

## Credenciales Default

**Grafana:**
- Usuario: (configurar en .env)
- Password: (configurar en .env)

**Matomo:**
- Configurar en primer acceso

## Configurar Discord Alerts

1. En Discord: Server Settings → Integrations → Webhooks → New Webhook
2. Copiar webhook URL y agregar `/slack` al final
3. Agregar al .env: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/ID/TOKEN/slack`
4. Reiniciar: `make restart`

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

### Analytics con Matomo

```html
<script>
var _paq = window._paq = window._paq || [];
_paq.push(['trackPageView']);
_paq.push(['enableLinkTracking']);
(function() {
	var u="//localhost:8081/";
	_paq.push(['setTrackerUrl', u+'matomo.php']);
	_paq.push(['setSiteId', '1']);
	var d=document, g=d.createElement('script');
	g.async=true; g.src=u+'matomo.js';
	d.getElementsByTagName('head')[0].appendChild(g);
})();
</script>
```

## Recursos

- Prometheus: ~500MB RAM
- Grafana: ~200MB RAM
- Loki: ~300MB RAM
- Tempo: ~200MB RAM
- Matomo: ~500MB RAM
- Total: ~2GB RAM recomendado

## Retención de Datos

- Prometheus: 30 días
- Loki: 30 días (744h)
- Tempo: 7 días (168h)
