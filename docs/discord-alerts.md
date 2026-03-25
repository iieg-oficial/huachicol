# Alertas Discord

## Flujo

```mermaid
graph LR
    P[Prometheus] -->|evalua reglas cada 30s| A[Alertmanager]
    A -->|webhook POST| D[alertmanager-discord :9094]
    D -->|POST con User-Agent| W[Discord Webhook API]
    W --> C[Canal Discord]
```

## Componentes

### Prometheus — Reglas (`prometheus/rules/alerts.yml`)

Evalua las reglas cada 30 segundos. Si una condicion se cumple durante el tiempo definido en `for`, envia la alerta a Alertmanager.

| Alerta | Severidad | Condicion | Espera |
|--------|-----------|-----------|--------|
| ServiceDown | critical | `up == 0` | 1m |
| HighLatency | warning | latencia promedio > 1s | 5m |
| HighErrorRate | critical | tasa de 5xx > 5% | 2m |
| HighMemoryUsage | warning | memoria > 90% | 5m |
| DiskSpaceLow | warning | disco < 10% | 5m |
| PostgreSQLDown | critical | `pg_up == 0` | 1m |
| TooManyConnections | warning | conexiones > 80% del max | 5m |

### Alertmanager (`alertmanager/alertmanager.yml`)

Agrupa, deduplica y enruta alertas al webhook de Discord.

| Parametro | Valor | Descripcion |
|-----------|-------|-------------|
| group_by | alertname, cluster, service | Campos para agrupar alertas |
| group_wait | 10s | Espera antes de enviar un grupo nuevo |
| group_interval | 10s | Intervalo entre envios de un mismo grupo |
| repeat_interval | 12h | Re-notifica alertas no resueltas cada 12h |
| send_resolved | true | Notifica cuando una alerta se resuelve |

**Inhibicion:** alertas `critical` suprimen alertas `warning` del mismo `alertname` e `instance`.

### Webhook Discord (`alertmanager/discord-webhook/`)

Servicio Python que recibe el POST de Alertmanager y lo formatea para Discord.

**Formato:** Discord Embeds con colores por severidad:
- Rojo (`#ED4245`) — critical firing
- Amarillo (`#FEE75C`) — warning firing
- Verde (`#57F287`) — resolved

Cada alerta es un embed independiente con campos: descripcion, servicio, proyecto, instancia y timestamp.

**Limitaciones:**
- Maximo 10 embeds por mensaje (limite de Discord API)
- Sin retry: si Discord falla, el mensaje se pierde

## Pruebas

```bash
# Desde el host (requiere ALERTMANAGER_DISCORD_PORT en .env)
curl -X POST http://localhost:6012/test

# Desde dentro de la red Docker
docker exec alertmanager-discord python3 -c \
  "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://localhost:9094/test', method='POST'))"
```

El endpoint `/test` envia una alerta de prueba (1 firing + 1 resolved) directamente a Discord.

## Variables de entorno

| Variable | Servicio | Descripcion |
|----------|----------|-------------|
| DISCORD_WEBHOOK_URL | alertmanager-discord | URL del webhook de Discord |
| ALERTMANAGER_DISCORD_PORT | alertmanager-discord | Puerto expuesto al host |

## Archivos

```
alertmanager/
├── alertmanager.yml              # Configuracion de routing y receivers
└── discord-webhook/
    ├── Dockerfile                # Imagen Python 3.13 Alpine
    └── server.py                 # Servidor HTTP webhook
prometheus/
└── rules/
    └── alerts.yml                # Reglas de alerta
```
