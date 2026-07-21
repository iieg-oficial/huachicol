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

Opciones:

- Cron en otra maquina que consulte `GET /healthz` del monitor y avise si no responde
- Servicio externo tipo healthchecks.io al que el monitor haga ping en cada ciclo
- El agente de otro servidor vigilando al de S1

La opcion mas barata: el propio monitor hace `GET` a un endpoint externo tras cada ciclo
exitoso; si deja de hacerlo, el externo alerta.

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

**Loki + Alloy (255 MB) se quedan al final, y su apagado es una decision aparte.** Son lo
unico que responde "que paso anoche". Sin ellos, un incidente raro no se puede reconstruir.
Si se apagan, dejar al menos rotacion de logs en el host y una forma de llegar a ellos.

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
