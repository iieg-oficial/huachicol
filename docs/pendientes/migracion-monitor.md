# Migracion del stack de observabilidad al monitor ligero

Plan por fases para reemplazar Prometheus/Grafana/Loki por `huachicol-monitor`.
Estado actual: **fase 1 completa** — el monitor corre en paralelo, no se ha apagado nada.

---

## Punto de partida

| | RAM | Que aporta |
|---|---|---|
| Stack actual (9 contenedores) | ~670 MB | Metricas historicas, logs centralizados, dashboards, alertas |
| `huachicol-monitor` | ~15 MB | Estado, version, fecha de despliegue, contenedores, alertas |

El ahorro real no es la RAM (670 MB sobre 30 GB es 2.2%): es dejar de mantener nueve
piezas para el uso que se les da.

---

## Fase 1 — Monitor en paralelo ✅

- [x] Contrato `/ontoy` v2 implementado en huachicol como referencia
- [x] `huachicol-monitor` sondeando los 8 proyectos del ecosistema
- [x] Histeresis validada con tests
- [x] API consumida por Mariachi (`/sistema/plataformas` enriquecido)
- [x] Pestana de documentacion en Mariachi para futuras integraciones
- [ ] Configurar `MONITOR_DISCORD_WEBHOOK_URL` y Telegram
- [ ] **Dejarlo correr una semana y confirmar que detecta una caida real**

No avanzar hasta que el monitor haya reportado correctamente al menos un incidente.

---

## Fase 2 — Migrar `/ontoy` a v2 en cada repo

Sin esto el panel da falsos verdes: hoy el sidecar responde `200` aunque el servicio
este caido, porque solo lee un archivo de version.

Orden sugerido, de menor a mayor riesgo:

1. `geoserver`, `acervo` — ya tienen sidecar, solo copiar el `ontoy_server.py` nuevo
2. `dataengine` — sidecar en `jobs/`; agregar check de Postgres y de conexiones
3. `mapalab`, `mariachi` — backend FastAPI, agregar `status` y `checks` al handler
4. `gateway-hub` — hoy es estatico en nginx; requiere decidir como generar el JSON

Guia por repo en [`docs/ontoy-contrato.md`](../ontoy-contrato.md), y la misma referencia
publicada en Mariachi (Documentacion → Contrato /ontoy).

---

## Fase 3 — Dead-man's switch

**Bloqueante antes de apagar nada.** Hoy Prometheus vigila al monitor; cuando se apague,
si el monitor cae nadie avisa y el silencio se ve igual que "todo bien".

**Mecanismo implementado (push).** El monitor hace `GET` a `MONITOR_DEADMAN_URL` tras cada
ciclo exitoso. Si el proceso muere o el ciclo se cuelga, el ping se detiene y el receptor
externo alerta tras su periodo de gracia. No requiere abrir puertos entrantes ni otra
maquina con acceso al monitor; solo salida HTTPS (la misma que ya usa para Discord/Telegram).

**Pendiente: elegir el receptor** (decision de deployment, el codigo es agnostico).

| Opcion | Infra | Dependencia externa |
|---|---|---|
| healthchecks.io (SaaS, tier gratuito) | ninguna | si (SaaS de terceros) |
| healthchecks.io self-hosted en otra VM | un contenedor en S2/S3 | no |

Configuracion: crear el check con periodo `60s` + gracia (ej. `120s`) y pegar su ping URL
en `MONITOR_DEADMAN_URL`. En prod la salida del monitor a ese receptor debe estar permitida.

---

## Fase 4 — Apagado por capas

Apagar de menor a mayor perdida. Entre cada paso, **una semana de margen**.

| Orden | Servicio | RAM | Que se pierde |
|---|---|---|---|
| 1 | cAdvisor | 81 MB | Metricas por contenedor. `/ontoy` v2 ya reporta estado |
| 2 | Grafana | 102 MB | Dashboards. La vista queda en Mariachi |
| 3 | node-exporter | 11 MB | Metricas de host. El check de disco de `/ontoy` cubre lo critico |
| 4 | Prometheus | 167 MB | **Historico de metricas.** Sin vuelta atras: decidir si archivar el TSDB |
| 5 | alertmanager + discord | 38 MB | Ruteo de alertas. Ya lo hace el monitor |
| 6 | nginx-auth | 3 MB | Solo protegia Prometheus y Loki |

**Loki + Alloy (255 MB) se quedan al final.** Decision tomada: el historico de Loki **no se
migra ni se archiva** — no se ha usado. Al apagar se descarta y se deja solo **rotacion
local** en cada servicio (docker logging driver con `max-size`/`max-file`), suficiente para
que los logs corrientes sobrevivan en el host sin llenar disco y sean accesibles con
`docker logs`. El cambio de logging entra en el mismo PR que quita Loki/Alloy; no hay
migracion previa.

Antes del paso 4: exportar el TSDB o aceptar que se pierde el historico. `make backup`
sigue funcionando y sube un snapshot a Acervo.

---

## Lo que el monitor no cubre

Reconocerlo por adelantado evita sorpresas:

- **Sin logs.** Detecta que algo esta caido, no por que.
- **Sin metricas historicas.** No responde "¿cuando empezo a degradarse?".
- **Sondeo cada 60 s.** Una caida de menos de un minuto pasa inadvertida.
- **Sin percentiles de latencia** por handler ni tasas de error por endpoint. Las alertas
  `MapalabMcpHighLatency` y `HighErrorRate` no tienen equivalente.

Si alguna de estas hace falta mas adelante, conviene reconsiderar antes de apagar
Prometheus, no despues.

---

## Reversion

Mientras el stack viejo siga instalado, volver atras es `docker compose up -d`. El punto
de retorno es el tag **`v1.23.0`**, con el stack completo verificado en runtime.
