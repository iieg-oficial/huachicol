# Changelog

Cambios notables de `huachicol`. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[Versionado Semantico](https://semver.org/lang/es/).

Desde **2.0.0** este repo es el monitor ligero `/ontoy`. Antes fue el stack de
observabilidad (Grafana, Prometheus, Loki, Alertmanager, cAdvisor, exporters, Alloy),
retirado en 2.0.0; su historico esta en [CHANGELOG-1.x.md](./CHANGELOG-1.x.md).

## [No publicado]

---

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
