# Pendiente: Migracion a Grafana Alloy — fases posteriores

> Contexto: Promtail entro en EOL en marzo 2026. Grafana recomienda migrar a Alloy.
> Version objetivo: **`grafana/alloy:v1.16.1`** (latest estable al 2026-05-11).
>
> **Fase 1 ejecutada** (rama `feat/agent-alloy-migration`): Alloy reemplaza Promtail + node-exporter en el agente. cAdvisor y postgres-exporter se quedan como containers independientes (postgres-exporter se posterga a fase 2 por la complejidad del bloque condicional con `POSTGRES_DSN` vacio).
> Este archivo lista las fases **2 y 3** que quedan pendientes.

---

## Fase 2: Consolidar cAdvisor y postgres-exporter dentro de Alloy

**Objetivo:** Eliminar los dos servicios independientes que quedan del agente reemplazandolos por componentes integrados en Alloy: `prometheus.exporter.cadvisor` y `prometheus.exporter.postgres`.

**Beneficio:** El agente queda con **un solo servicio** (Alloy) en lugar de tres. Una sola imagen que pinear/actualizar, un solo healthcheck, un solo set de volumenes.

### Sub-tarea A: cAdvisor en Alloy

**Bloqueador a validar antes:**

- cAdvisor requirio fixes especificos en `1.13.0` del repo para funcionar con Docker 29 + cgroups v2 + overlayfs. Imagen actual fijada en `gcr.io/cadvisor/cadvisor:v0.55.1` porque `0.52.1` y `0.56.2` tenian regresiones.
- `prometheus.exporter.cadvisor` de Alloy embebe su propia version de la libreria cadvisor — **confirmar que la version embebida en Alloy estable cubre los mismos casos sin regresiones** (Docker 29, cgroups v2, overlayfs, label storage).
- Probar exhaustivamente en staging antes de production: comparar metricas y labels resultantes con cAdvisor standalone, especialmente `container_label_*` y `storage_duration`.

**Archivos a tocar:**

- `agent/docker-compose.yml`: borrar service `cadvisor`, quitar profile `cadvisor`
- `agent/config.alloy`: agregar bloque `prometheus.exporter.cadvisor` con `docker_host = "unix:///var/run/docker.sock"` y `storage_duration = "5m"`
- `scripts/generate-targets.sh`: `cadvisor.json` para remotos apunta a `:12345` con `__metrics_path__ = /api/v0/component/prometheus.exporter.cadvisor.NAME/metrics`
- `docs/context.md`: actualizar tabla del agente

### Sub-tarea B: postgres-exporter en Alloy

**Bloqueador a validar antes:**

- `prometheus.exporter.postgres` requiere `data_source_names` con al menos 1 DSN no vacio. Si `POSTGRES_DSN` esta vacio, el componente falla y Alloy entero no arranca.
- Soluciones a evaluar:
  1. Servicio Alloy adicional (`alloy-postgres`) con profile `postgres` y config separada que SI incluye el bloque postgres. Mantiene un solo binario pero dos containers en server `dataengine`.
  2. Entrypoint custom que genera el `config.alloy` final por concatenacion segun `POSTGRES_DSN` este o no seteado.
  3. Usar `import.file` con archivo opcional (mas complejo).
- Decidir antes de implementar; opcion 1 es la mas simple y reusa la imagen base.

**Archivos a tocar:**

- `agent/docker-compose.yml`: borrar service `postgres-exporter`, agregar service `alloy-postgres` (opcion 1) o ajustar `alloy` actual segun opcion elegida
- `agent/config-postgres.alloy` (si opcion 1) o ajuste a `config.alloy`
- `scripts/generate-targets.sh`: `postgres-exporter.json` apunta al endpoint nuevo
- `docs/context.md` y `docs/onboarding-agente.md`

---

## Fase 3: Cambio de modelo pull → push (remote_write)

**Objetivo:** Migrar el agente Alloy de exponer endpoints scrapeable por Prometheus, a empujar metricas via `prometheus.remote_write` directamente al Prometheus central.

**Beneficio principal:** Resuelve la friccion documentada en `docs/context.md` linea 314 — "production (GCP): GCP no tiene los puertos abiertos por defecto, la apertura de puertos se debe solicitar al equipo de administracion".

- **Modelo actual (pull):** Prometheus en `monitoring` debe alcanzar el puerto de Alloy de cada VM remota → ticket de firewall por puerto/VM al equipo de administracion GCP.
- **Modelo push:** cada Alloy empuja a `monitoring`. Se abre **un solo puerto entrante** en monitoring (el endpoint de remote-write). **Cero puertos entrantes** en las VMs de proyectos.

**Trade-offs:**

- La alerta `ServiceDown` (regla `up == 0` en `service_alerts`) deja de funcionar tal cual. Sin endpoint scrapeable no hay metrica `up`. Hay que reescribirla con `absent_over_time()` por job/server, o agregar un heartbeat artificial que Alloy empuje periodicamente.
- Logs (Loki) ya van push, este cambio aplica **solo a metricas**.
- Si Alloy se cae, Prometheus deja de recibir — la deteccion de "agente caido" se vuelve indirecta (basada en ausencia de samples en ventana).

**Cambios principales:**

- `prometheus/prometheus.yml`: `--web.enable-remote-write-receiver` ya esta habilitado (`docs/context.md:372`). Exponer el endpoint a las VMs remotas via gateway-hub o nginx-auth con auth fuerte.
- `agent/config.alloy`: cada `prometheus.exporter.*` alimenta `prometheus.scrape` interno → `prometheus.remote_write` en lugar de exponerse en `/metrics`.
- Seguridad del endpoint remote-write entrante: definir auth (basic auth via nginx-auth existente, mTLS, o token bearer). Idealmente alinear con migracion a Authentik (`docs/pendientes/authentik.md`).
- `prometheus/rules/alerts.yml`: reescribir `ServiceDown`, `PostgreSQLDown` y `LokiDown` para que no dependan de `up`.
- `scripts/generate-targets.sh`: simplificacion — `node-exporter.json`, `cadvisor.json` y `postgres-exporter.json` dejan de generarse para VMs remotas (solo se mantienen para servicios scrap-eables internos del stack monitoring).
- `docs/onboarding-agente.md`: actualizar flujo (ya no requiere apertura de puerto entrante en la VM nueva).
- `docs/context.md`: actualizar seccion de scrape jobs y entornos.

**Cuando hacerlo:**

- Despues de fase 1 y fase 2 estabilizadas.
- Idealmente alineado con la migracion a Authentik (`docs/pendientes/authentik.md`) para reusar el IdP en el auth del endpoint remote-write.
