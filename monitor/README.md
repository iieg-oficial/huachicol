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
| `POST /api/deploy/start` | Abre una ventana de despliegue (suprime alertas) |
| `POST /api/deploy/end` | Cierra la ventana y reactiva alertas |

Escucha en `${BIND_ADDR}:${MONITOR_API_PORT}` (8090 por defecto), solo local. Mariachi la
consume por la red Docker `iieg-network`.

## Ventana de despliegue

Un despliegue apaga y prende varios servicios: sin esto, el monitor mandaria una cascada de
"caido/recuperado". En vez de eso, envuelve el deploy entre `/api/deploy/start` y
`/api/deploy/end`: durante la ventana **se suprimen** las alertas individuales (los eventos se
guardan igual, `notified=0`) y solo se manda un mensaje al abrir y otro al cerrar (con el
resumen `N/total ok`). Si no llega el `end`, la ventana expira sola tras
`MONITOR_DEPLOY_TIMEOUT` segundos (900 por defecto) y las alertas se reactivan.

Patron para el `make deploy` de cualquier repo (el `trap` garantiza el cierre aunque el
deploy falle):

```makefile
MONITOR_URL ?= http://127.0.0.1:8090

deploy:
	@curl -fsS -X POST "$(MONITOR_URL)/api/deploy/start" >/dev/null 2>&1 || true
	@bash -c 'trap "curl -fsS -X POST \"$(MONITOR_URL)/api/deploy/end\" >/dev/null 2>&1 || true" EXIT; \
	          docker compose up -d --build'
```

En produccion multi-VM, `MONITOR_URL` apunta al monitor de S1 (no `127.0.0.1`); la VM que
despliega debe poder alcanzarlo.

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

## Dead-man's switch

El monitor no puede vigilarse a si mismo: si cae, el silencio se ve igual que "todo bien".
Para cubrirlo hace ping HTTP a `MONITOR_DEADMAN_URL` al terminar **cada ciclo exitoso**.
Si el proceso muere o el ciclo se cuelga, el ping se detiene y el receptor externo alerta
tras su periodo de gracia. El monitor es agnostico al receptor: solo hace un `GET` a esa
URL, asi que sirve cualquier backend de ping.

- **healthchecks.io (SaaS):** crear un check con periodo `60s` + gracia (ej. `120s`) y pegar
  su ping URL en `MONITOR_DEADMAN_URL`. Cero infra; requiere salida HTTPS del monitor.
- **healthchecks.io self-hosted u otro receptor:** misma URL, sin dependencia de terceros.

Vacio = desactivado. El ping nunca rompe el ciclo: si falla, solo se loguea.

## Limites conocidos

- **No guarda logs.** Detecta que algo esta caido, no por que. Para el diagnostico
  retrospectivo sigue haciendo falta Loki o rotacion de logs en el host.
- **Sondeo cada 60s.** Una caida de menos de un minuto puede pasar inadvertida.
