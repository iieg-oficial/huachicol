# Changelog

Todos los cambios notables del proyecto se documentan en este archivo.

El formato esta basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Versionado Semantico](https://semver.org/lang/es/). El
versionado del repo `huachicol` es independiente del de las imagenes de Prometheus,
Grafana, Loki, Alertmanager y cAdvisor; aqui registramos los cambios sobre la
configuracion del stack, dashboards, alertas, agente remoto y el webhook de Discord.
Bumps por caracteristica registrada en commit. Considerando 1.x desde que el repo
salio a production con el commit inicial del stack de monitoreo.

## [No publicado]

---

## [1.19.5] - 2026-05-15

### Docs alineados: `MinIO` se engloba como `Acervo`

#### Cambiado

- **`docs/configuracion-env.md`** (seccion "Backups a Acervo (S3)"): texto simplificado. Se quito la nota "Acervo migro internamente de MinIO a SeaweedFS en acervo 1.22.0..." (contexto historico que ya vive en `acervo/docs/CHANGELOG.md`). Las variables conservan el prefijo `MINIO_` por compatibilidad con `scripts/backup.sh` (que usa `mc`); la descripcion del endpoint ya no compara con "antes 9000 en MinIO".

---

## [1.19.4] - 2026-05-15

### Documentacion sincronizada con SeaweedFS y alertas

#### Cambiado

- **`docs/configuracion-env.md`** (seccion "Backups a Acervo (S3)"): renombrada de "Backups a MinIO". Aclara que las variables `MINIO_*` se conservan por compatibilidad con `mc` pero apuntan a Acervo (SeaweedFS) en puerto `:8333`. Comando `make init-buckets BUCKET=huachicol` (ya no existe en acervo) reemplazado por la referencia al flujo nuevo: `acervo/config/identities.json`.
- **`docs/context.md`** (seccion `service_alerts`): documentadas las guardas `count > 0` en `HighLatency`/`HighErrorRate` (desde 1.19.2) + agregado nuevo grupo `ecosystem_integration_alerts.MariachiTreeNotifyFailures` (desde 1.19.3).
- **`docs/context.md`** (tabla "Endpoints del ecosistema"): linea de `Acervo Console` removida (servicio inexistente desde acervo 1.22.0); puerto de `Acervo API` corregido de `9000` (MinIO) a `8333` (SeaweedFS).
- **`docs/context.md`** (seccion "Acervo (backups)"): clarificada la fuente de las credenciales (`acervo/config/identities.json` con `actions: ["Read:huachicol","Write:huachicol"]`).
- **`docs/context.md`** (notas de gateway): "VPN-only" ya no menciona Acervo Console; bot-protection mencionada como "WFS-T bloqueado (POST + query string)" reflejando el cambio de gateway-hub 1.24.15.

---

## [1.19.3] - 2026-05-15

### Alerta para fallos del notifier mariachi → mapalab

Nuevo grupo `ecosystem_integration_alerts` con la regla `MariachiTreeNotifyFailures`. Cierra una clase de fallos silenciosos del ecosistema: si `MAPALAB_INTERNAL_TOKEN` queda distinto entre `mariachi/.env` y `mapalab/.env` (o si mapalab-backend cae, o iieg-network se rompe), el tree de capas se queda stale hasta el cron 04:00 UTC y no había forma de enterarse antes.

#### Agregado

- **`prometheus/rules/alerts.yml`** (`ecosystem_integration_alerts.MariachiTreeNotifyFailures`):
  - `expr: increase(mariachi_tree_notify_failed_total[10m]) > 0`
  - `for: 1m`
  - severity `warning`, service `mariachi`
  - description menciona las 3 causas habituales (token desalineado, mapalab-backend caído, red rota) para acelerar diagnóstico desde Discord.
- Se usa `increase()` (no `rate()`) porque el counter solo se materializa en `/metrics` tras el primer incremento — `rate(...) > 0` con la serie inexistente no dispararía.

#### Notas

- Coordinado con `mariachi 1.0.3+` (counter `mariachi_tree_notify_failed_total` ya expuesto) y `mapalab 1.28.5+` (auth interna que es la causa más probable del fallo).

---

## [1.19.2] - 2026-05-15

### Healthcheck de alloy y guardas en alertas HTTP

Dos fixes independientes que estaban generando ruido en operacion.

#### Cambiado

- **`docker-compose.yml`** (servicio `alloy`, healthcheck): test cambiado de `wget --spider http://localhost:12345/-/ready` a `bash -c 'exec 3<>/dev/tcp/127.0.0.1/12345 && exec 3<&-'`. La imagen `grafana/alloy:v1.16.1` **no incluye** `wget` (`bash`, `apt`, `b2sum` y el binario `alloy` si estan, pero no curl/wget). Resultado del healthcheck previo: `OCI runtime exec failed ... exec: "wget": executable file not found in $PATH` y container reportado `unhealthy` aunque alloy funcionaba normal. La nueva prueba usa el redirector `/dev/tcp` de bash (presente en la imagen) para verificar que el puerto 12345 acepta conexiones. Confirmado: alloy ahora reporta `healthy`.

- **`prometheus/rules/alerts.yml`** (`HighLatency`, `HighErrorRate`): agregada guarda `and rate(...count[5m]) > 0` al final de la expresion. Cuando `count==0` durante una ventana (servicio idle), `rate(sum)/rate(count)` produce `NaN`/`+Inf`, y la comparacion `> 1` o `> 0.05` evalua como `True` para ese label set — la regla disparaba `HighLatency` con `description: "... es +Inf en mariachi"` cada `repeat_interval` (12h) hacia Discord. Con la guarda, la alerta solo se evalua cuando hay trafico real. Validado tras `kill -HUP` a prometheus: 0 alertas activas en alertmanager.

---

## [1.19.1] - 2026-05-13

### Arreglado
- **`Datasource ${DS_PROMETHEUS} was not found`** en `ecosistema-iieg.json`: el dashboard provisionado dejaba `current: {}` vacío en las variables datasource, por lo que `${DS_PROMETHEUS}`/`${DS_LOKI}` nunca resolvían en runtime. Cambio: se fijan UIDs estables en `grafana/provisioning/datasources/datasources.yml` (`uid: prometheus` y `uid: loki`) y el dashboard referencia esos UIDs directamente (`{ "type": "prometheus", "uid": "prometheus" }`). Variables `DS_PROMETHEUS`/`DS_LOKI` removidas del templating.
  - Para forzar el UID fijo sobre datasources ya existentes con UID autogenerado se añadió `deleteDatasources` al provisioning. Recreación: `docker compose up -d --force-recreate grafana`.
- **`Cannot read properties of undefined (reading 'scopedVars')` en `TablePanel.tsx`** con Grafana 12.0.1: los `custom.cellOptions` tipo `gauge` con `mode: gradient` y `color-background` con `mode: gradient` requieren panel context (scopedVars) y crasheaban en columnas computed. Cambio: todas las columnas (`Uptime`, `Última actividad`, `Memoria`, `CPU`, `Red RX`, `Red TX`) usan ahora `cellOptions: { type: "color-text" }`. Se pierde la visual de barras gauge pero el panel deja de tirar excepciones. El color por threshold/gradient del campo se mantiene.
- **`400 /api/ruler/.../api/v1/rules/test/test`** del panel `alertlist`: sin `datasource` definido, Grafana consultaba el ruler de cada datasource (Prometheus + Loki); Loki no tiene ruler en esa ruta y devolvía 400. Cambio: `datasource: { type: "datasource", uid: "grafana" }` para que solo lea managed alerts de Grafana. `dashboardAlerts: false` mantiene el comportamiento previo.

### Cambiado
- **`loki/loki-config.yml`**: `server.log_level: warn` (antes default `info`). Loki en `info` registra ~7-10 líneas por cada query del frontend (`engine.go:263`, `metrics.go:237`, `metrics.go:409`, `roundtrip.go:359`, `table_manager.go:195`, `index_set.go:*`), lo que con el refresh del dashboard `Ecosistema IIEG` generaba ~3.2 logs/s sostenidos (98.5% nivel info, 1.5% warn/error). Las warns/errors (`failed mapping AST err="context canceled"`, `scheduler_processor` notifying finished query) son benignas: ocurren cuando Grafana cancela queries al refrescar paneles. Con `warn` el volumen baja ~98%; las trazas detalladas por traceID siguen disponibles temporalmente subiendo el nivel si se necesita debug puntual.

### Notas operativas
- Tras el fix de `node-exporter` (1.19.0) que eliminó ~6.4 logs/s de `broken pipe`, Loki quedó como el contenedor con más volumen de logs en los paneles "Volumen logs/s por container" y "Actividad de logs". El volumen no respondía a errores reales sino a verbosidad por defecto del propio Loki sirviendo queries del dashboard.

---

## [1.19.0] - 2026-05-13

### Agregado
- **Dashboard `Ecosistema IIEG`** (`grafana/dashboards/general/ecosistema-iieg.json`, uid `iieg-ecosystem`, en raíz): fusión de los antiguos `home.json` y `containers.json` en una vista única organizada en 12 secciones — Resumen general, Estado de servicios, Bases de datos, Distribución de contenedores, Gateway/Red, Top consumo, Estado de contenedores, Inventario detallado, Recursos del servidor, Tendencias de contenedores, Actividad de logs, Logs y alertas. Variables: `DS_PROMETHEUS`, `DS_LOKI` y `container` (multi, includeAll) que filtra todos los paneles por-contenedor.
- **Servicio `alloy` en el stack principal** (`docker-compose.yml`): reutiliza `agent/config.alloy` con `LOKI_URL=http://loki:3100` y `SERVER_NAME=monitoring`. Recolecta logs de todos los contenedores del propio servidor de monitoring y los envía a Loki. Funciona igual en local y en producción.
- **Job `alloy` en `prometheus.yml`**: scrappea `alloy:12345` con etiquetas `service=alloy, server=monitoring` para observar salud del agente.
- **Targets `alloy-start`/`-stop`/`-restart`/`-logs`/`-status` en `Makefile`** para gestionar el alloy local sin recordar comandos `docker compose`.
- **Loki `reject_old_samples_max_age: 744h`** (`loki/loki-config.yml`): alinea la ventana de aceptación de muestras con `retention_period`, permitiendo backfill del historial del docker daemon en el primer arranque del alloy.
- **Alias `postgres-exporter` en `iieg-network`** (`agent/docker-compose.yml`): el postgres-exporter del agent expone alias DNS estable resolvible desde Prometheus, evitando depender de container_name entre compose projects. Esto permite levantar `make agent-start PROFILES=postgres` con DSN apuntando a `dataengine-primary` local y que Prometheus lo descubra como `postgres-exporter:9187`.

### Cambiado
- **`GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH`** apunta ahora a `ecosistema-iieg.json` (antes `home.json`).
- **Healthcheck de `node-exporter`** cambiado de `wget --spider http://localhost:9100/huachicol` a `http://localhost:9100/`. La ruta `/huachicol` devuelve ~163KB de métricas; `wget --spider` cerraba antes de leer el body, causando spam continuo de `write: connection reset by peer` en los logs. La ruta `/` retorna ~150 bytes de HTML y el healthcheck termina limpio.
- **Provider `infrastructure` removido de `grafana/provisioning/dashboards/dashboards.yml`** y carpeta `grafana/dashboards/infrastructure/` eliminada. Todo lo que estaba ahí quedó incluido en `ecosistema-iieg.json`.
- **Panel "Proyectos" del ecosistema**: query `up{job="minio"}` reemplazada por `up{job="acervo-seaweedfs"}` (el job se renombró en 6640395 y dejaba "acervo" sin reportar).
- **Panel "Monitoreo" del ecosistema**: añadido `alloy` al filtro de servicios del stack.

### Eliminado
- `grafana/dashboards/general/home.json` y `grafana/dashboards/general/gateway-subroutes.json`: contenido absorbido por `ecosistema-iieg.json` o ya no necesario.
- `grafana/dashboards/infrastructure/containers.json` y la carpeta `infrastructure/`.
- Data links de `Container` en las dos tablas del ecosistema: causaban `Cannot read properties of undefined (reading 'scopedVars')` en `TablePanel.tsx` con Grafana 12 cuando la celda interpolaba `${__value.raw}`. Los logs siguen accesibles desde Explore manualmente.

### Notas operativas
- **Bind mounts y edición de archivos**: Grafana puede quedarse con la versión vieja de `dashboards.yml` si el archivo se edita con herramientas que crean un inode nuevo (Edit, vim sin `:set backupcopy=yes`, etc.). El bind mount apunta al inode original. Solución: `docker compose up -d --force-recreate grafana` después de editar archivos individuales montados.
- **Series stale tras quitar targets**: al vaciar `DATAENGINE_*` del `.env` quedaron series `up{job="postgres-exporter", project="dataengine"}=0` reportando DOWN por la retención de Prometheus. Para limpiar: `curl -sX POST "http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]=<selector>"` + `clean_tombstones`. Requiere `--web.enable-admin-api` (ya habilitado).

---

## [1.18.0] - 2026-05-13

### Agregado
- **Dashboard `Aplicaciones — Mapalab & Mariachi`** (`grafana/dashboards/projects/aplicaciones.json`, uid `iieg-aplicaciones`, folder `Projects`): 37 paneles distribuidos en 4 secciones colapsables que consumen las métricas HTTP estándar (instrumentator) y custom de negocio (`mapalab_*`, `mariachi_*`).
  - **MapaLab — HTTP**: stats de RPS, latencia p95, error rate 5xx y total 1h; timeseries de RPS por handler (top 10), latencias p50/p95/p99, status codes apilados; bargauge de top 5 handlers más lentos.
  - **MapaLab — Negocio**: descargas/min, shares creados 1h, cache hit ratio, embeds denegados 1h; timeseries de embeds (requests/denied/quota), shares (creados/accedidos/pinneados), `mapalab_embed_vital_ms` p50/p95, búsquedas+tree+refresh.
  - **Mariachi — HTTP**: mismas visualizaciones que mapalab pero filtrando `project="mariachi"`.
  - **Mariachi — Negocio**: stats de logins success/failed/locked y rate-limit hits 1h; timeseries de logins, geoserver+tree_notify, media uploads/deletes y pipeline SIEEJ (formularios/envios/expired/reabierto); bargauge de writes por entidad (users, projects, layers, eventos, etc).
- **Reglas `HighLatency` y `HighErrorRate` ahora aplicables a mapalab-backend y mariachi-backend** porque ambos exponen `http_request_duration_seconds` y `http_requests_total{status}` via `prometheus-fastapi-instrumentator`. Documentado en `docs/alert-rules.md`.

### Cambiado
- `docs/alert-rules.md`: actualizada la nota sobre qué servicios aplican para las reglas HTTP.

### Notas para integración con mapalab y mariachi
- Mapalab (`/IIEG/mapalab`): nuevos cambios en `backend/requirements.txt`, `backend/app/server.py` (Instrumentator con presets `requests()` y `latency()`), `backend/app/metrics.py` (`generate_latest(REGISTRY)` concat al render manual) y `nginx/nginx.conf` (bloqueo `^/mapalab/api/metrics$` con `return 403` — defense-in-depth contra exposición pública vía `mapalab-nginx:3006`). Se aplica al rebuildear con `make deploy`.
- Mariachi (`/IIEG/mariachi`): nuevos cambios en `api/pyproject.toml`, `api/app/main.py`, `api/app/api/metrics.py` (mismo patrón). Mariachi no publica puerto host, por lo que no requiere bloqueo en nginx.
- **Cuidado con regex**: `excluded_handlers` del instrumentator usa `re.search`, no match exacto. Patrones como `"/"` matchean cualquier path. Usar anclas `^...$` (e.g. `^/metrics$`).

---

## [1.17.4] - 2026-05-13

### Agregado
- **`MAPALAB_BACKEND_TARGET=mapalab-backend-1:8000` y `MARIACHI_BACKEND_TARGET=mariachi-api:8000`** activados. Ambos proyectos ya exponen `/metrics` (implementado a mano en `app/metrics.py` y `app/api/metrics.py` respectivamente, sin `prometheus-fastapi-instrumentator`). Targets verificados UP en `http://localhost:9090/api/v1/targets`.
  - **Métricas que exponen son de negocio** (counters/histograms con prefijo `mapalab_*` y `mariachi_*`: requests al árbol, descargas, embebidos, logins, escrituras de capas, etc.). NO incluyen `http_request_duration_seconds` ni `http_requests_total{status_code=~"5.."}`, por lo que las reglas `HighLatency` y `HighErrorRate` en `prometheus/rules/alerts.yml` **no se disparan** para estos servicios. La regla `ServiceDown` (`up == 0`) sí funciona.
  - Para habilitar alertas estándar de latencia/errores 5xx en estos backends habría que instrumentar middlewares HTTP adicionales en sus apps FastAPI (issue pendiente, no crítico).

### Cambiado
- `docs/alert-rules.md`: aclarado que mapalab/mariachi exponen métricas de negocio pero no de HTTP estándar, y que `HighLatency`/`HighErrorRate` quedan inactivas para ellos.

---

## [1.17.3] - 2026-05-13

### Removido
- **`PROMETHEUS_EXTERNAL_URL` y `GRAFANA_EXTERNAL_URL` eliminadas del stack.** Razon: la UI de Prometheus no tiene auth nativa y expone query API + metricas internas, por lo que publicarla al exterior no aplica; los enlaces a Grafana en los embeds aportaban poco valor frente al ruido que generaban. Cambios:
  - Removidas del `.env`, `.env.example` y de `docker-compose.yml` (service `alertmanager-discord`).
  - `alertmanager/discord-webhook/server.py`: eliminadas las constantes, la funcion `_links()`, el import `urllib.parse.quote` y el campo `Enlaces` de los embeds.

### Removido
- **Servicio `urlschiquitas` eliminado del stack** (proyecto descontinuado). Limpieza completa de referencias en `.env`, `.env.example`, `scripts/generate-targets.sh`, `scripts/test-alerts.sh`, `docs/agregar-proyecto.md`, `docs/context.md`, `docs/configuracion-env.md` y `docs/alert-rules.md`. Alertas de prueba `HighLatency`/`HighErrorRate` reapuntadas a `gateway-hub/nginx`, y `PostgreSQLDown`/`TooManyConnections` a `dataengine/postgres`.
- **Variables muertas en `.env`** removidas: `TEMPO_PORT`, `TEMPO_OTLP_GRPC_PORT`, `TEMPO_OTLP_HTTP_PORT`, `TEMPO_ZIPKIN_PORT`, `TEMPO_JAEGER_PORT` (no existe servicio `tempo` en `docker-compose.yml`).
- **Job legacy de MinIO en `generate-targets.sh`** removido: bloque que generaba `minio.json` y `minio-token` con `ACERVO_MINIO_TARGET`/`ACERVO_MINIO_TOKEN`. El job `acervo-minio` ya no existe en `prometheus.yml` desde `6640395` (reemplazado por `acervo-seaweedfs`). Variables `ACERVO_MINIO_*` removidas de `.env.example` y de la doc de provisioning JWT (SeaweedFS no requiere JWT).
- **Entrada de `prometheus/targets/minio-token`** removida del `.gitignore`.

### Cambiado
- **`ACERVO_METRICS_TARGET` ahora se lee desde `.env`** en lugar de tener `acervo-seaweedfs:9091` hardcodeado en `prometheus/targets/acervo-seaweedfs.json`. Production tiene servidores separados; el target se inyecta via env. `generate-targets.sh` genera el JSON desde la variable.
- **`scripts/test-alerts.sh` ahora carga `.env`** y resuelve targets desde variables (`DATAENGINE_POSTGRES_TARGET`, `GATEWAY_NGINX_TARGET`) con `:?` para fallar explicitamente si no estan definidas. Sin defaults hardcoded.

### Agregado
- **`PROMETHEUS_EXTERNAL_URL` y `GRAFANA_EXTERNAL_URL` en `.env`** (vacias por default). Las consume el webhook de Discord en `alertmanager/discord-webhook/server.py` para incluir enlaces a Prometheus/Grafana en los embeds de alertas. Si quedan vacias, los embeds salen sin botones de enlace (no rompe nada).
- **`MARIACHI_BACKEND_TARGET` en `.env`** (vacia) para futura activacion cuando `mariachi/api` exponga `/metrics` via `prometheus-fastapi-instrumentator`.

---

## [1.17.1] - 2026-05-12

### Cambiado
- **Dashboard `Contenedores - Vista Detallada` enriquecido** (`grafana/dashboards/infrastructure/containers.json`): pasa de tabla + timeseries basicos a 29 panels distribuidos en 8 secciones con filas colapsables. Nuevas visualizaciones:
  - **Resumen ejecutivo** con stat cards de contenedores activos, CPU agregado, memoria total y logs/s del cluster.
  - **Distribucion por proyecto** con piechart (`container_memory_usage_bytes` agrupado por `container_label_com_docker_compose_project`) y bargauge gradiente de containers por proyecto.
  - **Top consumo** con dos bargauges horizontales para top 10 memoria y top 10 CPU.
  - **Tabla de estado** con CPU%/memoria/uptime/ultima actividad y celdas color-background segun threshold.
  - **Inventario detallado** con CPU/memoria como gauges, red RX/TX y tasa de logs en una sola fila clickable.
  - **State-timeline** "Mapa de actividad por container" (logs/min via Loki `count_over_time`).
  - **Drill-down links** en las tablas: click en un container abre Loki Explore con la query `{container_name="..."}` preseteada.
- **Panel de reinicios reemplazado por trafico HTTP del gateway**:
  - Removidos: annotation `Reinicios de containers` y stat cards `Reinicios (30 min)` y `Containers reiniciados (5 min)` (poco utiles en operacion diaria).
  - Agregados: stat `Requests/seg (gateway)` con `sum(rate(nginx_http_requests_total[5m]))` y sparkline, y stat horizontal `Conexiones activas (gateway)` con las 4 series de `nginx_connections_*` (activas/leyendo/escribiendo/en espera).
  - **Limitacion conocida:** el `nginx-exporter` instalado es de tipo stub_status, no expone status codes, URIs ni latencia. Para drill-down por endpoint queda pendiente migrar a `nginx-prometheus-exporter` con modulo `vts` o cruzar con logs de gateway en Loki.

---

## [1.17.0] - 2026-05-11

### Cambiado
- **Agente remoto: Promtail y node-exporter reemplazados por Grafana Alloy v1.16.1**. Motivacion: Promtail entro en EOL en marzo 2026 (auditoria externa lo marca como deuda tecnica). Se aprovecha la migracion para consolidar node-exporter en el mismo binario.
  - Nuevo archivo `agent/config.alloy` con: `loki.source.docker` (logs de containers via socket Docker), `loki.source.file` (syslog), `loki.write` (push a Loki central), y `prometheus.exporter.unix` (metricas host).
  - `agent/docker-compose.yml`: services `promtail` y `node-exporter` reemplazados por `alloy`. Imagen `grafana/alloy:v1.16.1`. Volumen `promtail_positions` reemplazado por `alloy_data`.
  - Profiles del agente reorganizados: `all` (alloy + cadvisor), `telemetry` (solo alloy), `cadvisor`, `postgres`. Profiles previos `node` y `promtail` removidos.
  - `prometheus.yml` sin cambios estructurales: el job `node-exporter` mantiene path `/huachicol` para el server `monitoring` (sigue usando node-exporter standalone en el stack central), y cada target remoto override su path con `__metrics_path__: /api/v0/component/prometheus.exporter.unix.host/metrics` en `node-exporter.json` (generado por `scripts/generate-targets.sh`).
  - `scripts/generate-targets.sh`: targets remotos de node-exporter ahora apuntan a `:12345` con `__metrics_path__` por target.
  - `agent/.env.example`: `NODE_EXPORTER_PORT` removido, `ALLOY_PORT` agregado (default 12345).
  - Documentacion actualizada: `docs/context.md`, `docs/onboarding-agente.md`, `docs/pendientes/alloy-migration.md`, `docs/pendientes/gateway-improvements.md`.

### Corregido
- **`alertmanager-discord` quedaba aislado en la red `huachicol_default`** (sin bloque `networks` en `docker-compose.yml`) mientras el resto del stack vive en `huachicol_monitoring`. `alertmanager` no podia resolver `alertmanager-discord` por DNS (`NXDOMAIN`), las alertas reintentaban 7-8 veces y se dropeaban silenciosamente. Bug detectado por el dashboard nuevo de containers al ver los errores de `dispatch.go` en logs de `alertmanager`. Fix: agregar `networks: [monitoring]` al service.

### Agregado
- **Dashboard `Contenedores - Vista Detallada`** (`grafana/dashboards/infrastructure/containers.json`): vista unificada con stats de resumen, inventario de containers (tabla con CPU+memoria desde cAdvisor y rate de logs desde Loki), timeseries de CPU/memoria/red por container, volumen de logs por container, y panel de logs en vivo filtrable. Variable `$container` multi-select.
- **Env vars de Grafana para reducir carga inicial** (`docker-compose.yml`): `GF_PLUGINS_DISABLE_PLUGINS` para los 4 plugins de drilldown que Grafana 12 precarga (`grafana-exploretraces-app`, `grafana-lokiexplore-app`, `grafana-metricsdrilldown-app`, `grafana-pyroscope-app`), `GF_FEATURE_TOGGLES_DISABLE=preinstallAutoUpdate,dashgpt`, y `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` apuntando al `general/home.json`. Reduce ~10 requests innecesarias al cargar la UI. El problema raiz (rate limit del gateway) queda documentado en `docs/pendientes/gateway-improvements.md` punto 3.

### Cambiado
- **Provisioning de dashboards reorganizado**: provider `default` renombrado a `general` y apuntando a `dashboards/general/` (donde se movieron `home.json` y `gateway-subroutes.json`). Antes el provider escaneaba la raiz e incluia recursivamente las subcarpetas `projects/` e `infrastructure/`, generando duplicados que impedian a Grafana guardar updates de los dashboards.

### Pendiente (fases posteriores documentadas en `docs/pendientes/alloy-migration.md`)
- Fase 2: consolidar cAdvisor y postgres-exporter en Alloy (queda 1 solo servicio en el agente).
- Fase 3: migrar a modelo push con `prometheus.remote_write` para resolver dependencia de firewall GCP.

---

## [1.16.1] - 2026-04-28

### Corregido
- **Healthcheck de `alertmanager-discord` siempre `unhealthy`**: el test apuntaba a `http://localhost:9093/-/healthy` pero `9093` es el puerto de `alertmanager`, no de `alertmanager-discord` (que escucha en `9094`). Ademas el container alpine no resolvia `localhost` (solo `127.0.0.1`). Como el `server.py` de discord-webhook solo expone `do_POST`, no hay endpoint GET para `wget --spider`; cambiado a un TCP socket check con `python3 -c "import socket; socket.create_connection(('127.0.0.1', 9094), timeout=3).close()"` (Python ya esta en la imagen). Verifica que el server este aceptando conexiones, suficiente como liveness.

---

## [1.16.0] - 2026-04-28

### Agregado
- **Configuracion del proyecto `mariachi-api` en el stack de monitoreo**: targets, dashboards y documentacion para que Prometheus scrappee metricas y Loki recolecte logs del backend de mariachi.

---

## [1.15.0] - 2026-04-14

### Cambiado
- **Rate limiting diferenciado en gateway**: zonas separadas (`api`, `general`, `download`, `console`) con limits y bursts ajustados por tipo de endpoint.
- **Asset caching** para `js`/`css`/`woff2`/`png`/`svg` con `expires 1y` + `Cache-Control: public, immutable`.
- **`cAdvisor` resource limits** en compose: `mem_limit: 256m` y `cpus: 0.25` para evitar que devore CPU del host.

---

## [1.14.0] - 2026-04-13

### Agregado
- **`DATAENGINE_SERVER_IP`** env var en target generation: permite agregar el server de DataEngine como target separado (Prometheus + Loki) sin reescribir los JSONs manualmente. Scripts de generacion de targets actualizados.

### Eliminado
- **Tempo** (tracing service): no se uso en production y agregaba 2GB+ de uso de disco. Removido del compose, configs y datasource de Grafana.

---

## [1.13.0] - 2026-04-04

### Cambiado
- **cAdvisor**: serie de fixes para que funcione consistente en hosts con docker reciente:
  - `cgroup` volume mount path actualizado a `/sys/fs/cgroup`.
  - Docker socket volume mount cambiado a read-write (algunas operaciones lo requieren).
  - `containerd` socket path agregado (cAdvisor lo usa para metricas de contenedores).
  - Image: `v0.55.1` con `ghcr.io` registry (previo `0.52.1`/`0.56.2` tenian regresiones).
  - Removidos flags deprecated.

---

## [1.12.0] - 2026-04-04

### Agregado
- **Docker compose profiles** en agent (`node`, `cadvisor`, `promtail`, `postgres`): permite habilitar selectivamente que servicios corren en cada server remoto. `make agent-start PROFILES="node cadvisor"` arranca solo los seleccionados.
- **Docker-only mode** y **container label storage** en agent configurations: cAdvisor scrap solo containers (no procesos del host) y guarda labels para correlacion en Grafana.
- **Environment configuration guide** documentando cada profile y sus envs.

---

## [1.11.0] - 2026-04-04

### Cambiado
- **Grafana sub-path routing**: configuracion para que Grafana sirva en `/huachicol/` (no en root) sin perder paths internos.
- **MinIO bucket-specific creds**: en lugar de usar root credentials para acceso a Loki/backups, ahora se usan credenciales por bucket via `ACERVO_*_ACCESS_KEY`/`ACERVO_*_SECRET_KEY`.

---

## [1.10.0] - 2026-04-03

### Cambiado
- **Overhaul completo del stack de monitoreo**: nuevos backup scripts (Prometheus snapshots + Loki bucket sync hacia acervo MinIO), auth proxy intermedio (`nginx-auth` con basic auth para Loki + Prometheus), documentacion expandida en `docs/` con runbooks de incidentes y arquitectura del stack.

---

## [1.9.0] - 2026-03-25

### Agregado
- **`acervo-minio` job en Prometheus**: scraping de metricas del MinIO de acervo para alertas sobre uso de disco, errores de S3 y rate de uploads.

---

## [1.8.0] - 2026-03-25

### Agregado
- **Discord webhook custom Python** (`alertmanager/discord-webhook/server.py`): replace de `discord.sh` (bash) por un servidor Python que parsea el payload de Alertmanager y arma embeds Discord ricos (color por severity, title/description localizadas a Espanol, links a Grafana/Prometheus). Endpoint dedicado en puerto `9094`.
- **Logging de errores HTTP** del webhook + Python output unbuffered (logs en tiempo real).
- **`User-Agent` header** en requests salientes a Discord (el de `urllib` default era genrico).
- **`docs/discord.md`** con setup + testing + scripts de prueba (`scripts/test-discord-alert.sh`).
- **`scripts/test-discord-alert.sh`** — payload de Alertmanager v2 simulado para validar el webhook end-to-end.

### Cambiado
- **Alertas localizadas a Espanol**: titulos y descripciones generadas dinamicamente en Espanol; severities mapeadas a colores Discord (red=critical, yellow=warning, green=resolved).
- **`ServiceDown` alert delay** aumentado para reducir false positives durante deploys.

### Eliminado
- Test payload + endpoint de prueba del webhook (no debian estar en production).

---

## [1.7.0] - 2026-03-24

### Agregado
- **`alertmanager-discord` proxy service** integrado en el compose: reemplaza el receiver `discord_*` directo de Alertmanager con un servicio intermedio que enriquece el payload antes de enviar a Discord.
- Receiver de Alertmanager consolidado en uno generico que apunta al webhook custom.
- Image inicial: `benjojo/alertmanager-discord` (luego reemplazada por la implementacion Python en `1.8.0`).

---

## [1.6.0] - 2026-03-24

### Agregado
- **Dashboard de Grafana para Gateway Hub** (`grafana/dashboards/gateway-hub.json`): metricas de requests/sec, status codes (2xx/4xx/5xx), latencias p50/p95/p99, top URIs, top user-agents, logs de errores via Loki.
- Provisioning automatico de dashboards via `grafana/provisioning/dashboards/`.

### Cambiado
- Estructura del JSON del dashboard: removido el wrapper `dashboard` y `overwrite` para que Grafana lo importe directo.
- Volume mounts y paths de provisioning simplificados.

---

## [1.5.0] - 2026-03-24

### Eliminado
- **Tempo (tracing)**: removido del stack inicial. La complejidad de instrumentar OpenTelemetry en cada servicio del ecosistema no justificaba el costo de infra. Configuracion residual de `block duration` y `retention` se limpio del compose y de los configs.

---

## [1.4.0] - 2026-03-24

### Agregado
- **Grafana sub-path** (`/huachicol/`): config para servir Grafana detras de gateway-hub via subpath en lugar de subdomain.
- **`iieg-network`** (network external) — Grafana se conecta para que gateway pueda hacer proxy.
- **Env vars para puertos** de cada servicio del stack (Prometheus, Grafana, Alertmanager, Loki) sourcing desde `.env`.
- **Custom path scraping** para metricas de Grafana en Prometheus (no usa default `/metrics`).

---

## [1.3.0] - 2026-03-24

### Eliminado
- **Matomo** (analytics on-prem): nunca se uso despues del setup inicial; la analytics se maneja ahora via GTM/GA4 desde gateway-hub. Removidos servicios, configs y env vars.

---

## [1.2.0] - 2026-03-24

### Agregado
- **Agente de monitoreo remoto** (`agent/`): stack reducido (Node Exporter + cAdvisor + Promtail) que se despliega en servers remotos del ecosistema. El stack principal en `monitoring` los detecta via file-based service discovery (`prometheus/targets/*.json`) y scrap-ea sus metricas + logs.
- **Comandos `make` para el agente**: `agent-start`, `agent-stop`, `agent-restart`, `agent-logs`, `agent-status`, `agent-clean`.
- Estructura completa del Makefile expandida para diferenciar stack principal vs agente remoto.

---

## [1.1.0] - 2026-02-12

### Agregado
- **Stack de monitoreo completo via Docker Compose**: Prometheus + Grafana + Alertmanager + Loki + Tempo. Configuraciones iniciales en `prometheus/`, `grafana/`, `alertmanager/`, `loki/` y `tempo/`. Network compartida para la comunicacion intra-stack.

---

## [1.0.0] - 2025-11-13

Primera version del repo `huachicol` en production.

### Agregado
- Inicializacion del repositorio.
- Estructura base del proyecto.
