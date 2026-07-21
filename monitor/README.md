# huachicol-monitor

Monitor ligero del ecosistema IIEG. Sondea el `/ontoy` de cada servicio, guarda el estado
en SQLite y notifica a Discord y Telegram con histeresis.

Sin dependencias externas: solo la biblioteca estandar de Python. ~15 MB de RAM.

## Como funciona

```
cada 60s:
  sondea /ontoy de cada target (en paralelo, timeout 5s)
  compara con el estado anterior en SQLite
  si un servicio acumula N fallos seguidos -> evento "down"
  si se recupera tras haber alertado       -> evento "recovered"
  si cambio de version                     -> evento "deployed"
  agrupa todos los eventos del ciclo en UN mensaje por canal
```

La histeresis es lo que evita el spam: un corte de red de 2 segundos no dispara nada,
porque hacen falta `MONITOR_FAILURE_THRESHOLD` fallos consecutivos (3 por defecto = 3 min).
Y no se repite la alerta mientras el servicio siga caido.

## Configuracion

Targets en `targets.json` (copiar de `targets.example.json`):

```json
[
  { "slug": "geoserver", "label": "GeoServer",
    "url": "http://geoserver-version-api:8088/ontoy", "timeout": 5 }
]
```

Resto por variables de entorno, documentadas en el `.env.example` del repo raiz.
Los secretos (`MONITOR_DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)
nunca van en `targets.json`.

### Telegram

1. Crear el bot con [@BotFather](https://t.me/BotFather) y copiar el token
2. Agregar el bot al grupo
3. Obtener el `chat_id`:
   `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq '.result[0].message.chat.id'`
   (los grupos tienen id negativo, ej. `-1001234567890`)

## API

| Ruta | Devuelve |
|---|---|
| `GET /api/status` | Estado de todos los servicios + resumen |
| `GET /api/status/<slug>` | Detalle de uno, con historial (`?limit=100`) |
| `GET /api/events` | Ultimos eventos registrados (`?limit=50`) |
| `GET /healthz` | Liveness |
| `GET /ontoy` | Version del propio monitor |

Escucha en `${BIND_ADDR}:${MONITOR_API_PORT}` (8090 por defecto), solo local. Mariachi la
consume por la red Docker `iieg-network`.

## Operacion

```bash
docker compose up -d monitor      # levantar
docker compose logs -f monitor    # ver ciclos
docker compose restart monitor    # recargar targets.json
```

`targets.json` se monta como bind: al editarlo hay que **recrear** el contenedor
(`docker compose up -d --force-recreate monitor`), no basta `restart` si cambio el archivo
en disco pero el contenedor ya lo tenia cacheado en memoria.

## Tests

```bash
cd monitor && python -m unittest discover -s tests -v
```

Cubren la histeresis, que es donde estan los errores caros: alertar de mas (spam) o de
menos (silencio en un incidente real).

## Limites conocidos

- **Se monitorea a si mismo.** Si el monitor cae, nadie avisa. Hace falta un dead-man's
  switch externo (cron en otra maquina que consulte `/healthz`, o healthchecks.io).
- **No guarda logs.** Detecta que algo esta caido, no por que. Para el diagnostico
  retrospectivo sigue haciendo falta Loki o rotacion de logs en el host.
- **Sondeo cada 60s.** Una caida de menos de un minuto puede pasar inadvertida.
