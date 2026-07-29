# Changelog

Cambios notables de `huachicol`. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[Versionado Semantico](https://semver.org/lang/es/).

Desde **2.0.0** este repo es el monitor ligero `/ontoy`. Antes fue el stack de
observabilidad (Grafana, Prometheus, Loki, Alertmanager, cAdvisor, exporters, Alloy),
retirado en 2.0.0; su historico esta en [changelog/v1.md](./changelog/v1.md).

## [2.1.1] - 2026-07-29

### El README describia el stack retirado y los docs 1.x se archivaron

Solo documentacion; sin cambios en el monitor.

#### Cambiado

- **README reescrito.** Se titulaba «IIEG Monitoring Stack», listaba los ocho servicios retirados
  en 2.0.0 con sus puertos y documentaba targets del Makefile que ya no existen (`make targets`,
  `make backup`, `make agent-start`, `make backup-cron-install`). Ahora describe los dos servicios
  reales, las trece variables del `.env`, `monitor/targets.json` con su gotcha de recrear el
  contenedor, y la ventana de despliegue.
- `docs/CHANGELOG-1.x.md` → `docs/changelog/v1.md`, siguiendo el patron de acervo (un archivo por
  major bajo `docs/changelog/`).

#### Eliminado

- `docs/alert-rules.md`, `discord-alerts.md`, `configuracion-env.md` y `agregar-proyecto.md`:
  describian el stack Prometheus/Grafana/Alertmanager/Loki retirado el 2026-07-21, con requisitos
  (`/metrics`) y scripts que ya no existen. Quedaron condensados en
  `historial/2026-07-huachicol-stack-observabilidad-1x.md` del repositorio central de contexto,
  con los umbrales de las siete alertas, el enrutamiento y sus limites conocidos — util para un
  rollback al tag `v1.23.0`.
- `docs/context.md`, `onboarding-agente.md`, `ontoy-contrato.md` y `docs/pendientes/`: viven ahora
  en `repos/huachicol/` del repo central.

## [2.1.0] - 2026-07-29

### Cambiado: las alertas dicen que check esta degradado, no solo cual fallo

El monitor ya trataba `degraded` como estado no sano —tras `MONITOR_FAILURE_THRESHOLD`
sondeos alerta igual que con `down`—, pero el detalle del mensaje solo enumeraba los checks
en `down` o `unreachable`. Un servicio que se reportaba degradado producia una alerta sin
explicacion: "MapaLab: degradado" y nada mas.

Ahora el detalle distingue ambos grupos y arrastra el `detail` que cada check trae en su
`/ontoy`:

```
checks en fallo: db (connection refused) | checks degradados: client_errors (6 errores de
carga en el navegador en 15 min (predomina chunk_load_error))
```

El cambio habilita el patron de reportar sintomas de usuario como checks degradados: mapalab
1.97.0 expone `client_errors` con la cuenta de fallos de carga que reportan los navegadores,
que era justo lo que dejo de verse al retirar Prometheus y Alertmanager en 2.0.0. No requiere
cambios en `targets.json` ni en la configuracion de los servicios monitoreados.

## [2.0.0] - 2026-07-21

### Apagado del stack de observabilidad: el repo queda como monitor ligero

Fin de la migracion planificada en `docs/pendientes/migracion-monitor.md`. Se retira el stack
pesado; el monitor `/ontoy` v2 y su dashboard en Mariachi cubren estado, alertas (Discord) y
disponibilidad. El repo pasa a contener solo `version-api` (sidecar `/ontoy`) y `monitor`.

#### Eliminado

- Servicios del `docker-compose.yml`: `prometheus`, `grafana`, `alertmanager`,
  `alertmanager-discord`, `loki`, `alloy`, `node-exporter`, `cadvisor`, `nginx-auth`, con sus
  volumenes, la red `monitoring` y los puertos 9090/3000/9093/3100/9100/9091/3101.
- Configuracion del stack: `prometheus/`, `grafana/`, `loki/`, `alertmanager/`, `agent/` y
  `nginx-auth/`; los scripts de `scripts/` (backup, restore, generate-targets, etc.) y los
  targets del `Makefile` asociados; los jobs de CI de prometheus/alertmanager/loki/agente.
- Variables del stack en `.env.example`.

#### Cambiado

- `version-api` y `monitor` declaran rotacion local de logs (`json-file`, `max-size` 10m,
  `max-file` 3): unica retencion tras retirar Loki.
- `gateway-hub`: se quitan las locations `/huachicol/` y `/huachicol/public/` (proxy a
  Grafana) y su zona `limit_req`. Se conserva `/huachicol/ontoy`.

#### Datos

- Descartados los volumenes del TSDB de Prometheus, dashboards de Grafana e indice de Loki.
  Sin archivado: no se usaban.

#### Por que major

Cambio incompatible de proposito: el repo deja de desplegar el stack de observabilidad. El
punto de retorno con el stack completo es el tag `v1.23.0`.

### Ventana de despliegue en el monitor

Durante un despliegue los servicios caen y suben; para no spamear alertas, el monitor gana
endpoints `POST /api/deploy/start` y `POST /api/deploy/end`. Entre ambos **suprime** las
alertas individuales de caida/recuperacion (los eventos se registran igual, `notified=0`) y
solo envia un mensaje al iniciar y otro al finalizar (con resumen `N/total ok`). La ventana
expira sola tras `MONITOR_DEPLOY_TIMEOUT` segundos (900 por defecto) si no llega el `end`. El
`make deploy` de cada repo envuelve el deploy con esas llamadas (patron en `monitor/README.md`).
