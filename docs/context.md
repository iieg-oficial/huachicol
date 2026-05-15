# Contexto Completo del Ecosistema IIEG: Huachicol + Gateway-Hub

> Referencia completa del ecosistema para onboarding y consulta rapida.
> Ultima actualizacion: 2026-04-13

---

## Quien lo usa

- **Organizacion:** IIEG (Instituto de Informacion Estadistica y Geografica de Jalisco) — organismo publico del gobierno de Jalisco, Mexico.
- **Equipo:** Desarrollo de software del IIEG, liderado por Edgar Villarreal. Cuenta con credenciales de acceso a los servidores GCP y al equipo de administracion.
- **Usuarios del monitoreo:** Equipo de desarrollo y operaciones.
- **Usuarios finales:** Ciudadanos y funcionarios que acceden a los portales publicos.
- **Repositorios:** Todos los proyectos estan versionados en GitHub.

---

## Que es cada proyecto

### Huachicol (`/home/egar/IIEG/huachicol`)

Stack centralizado de monitoreo y observabilidad. Servicios Docker:

| Servicio | Imagen | Funcion | Puerto host |
|---|---|---|---|
| Prometheus | prom/prometheus:v3.2.1 | Metricas (scraping) | PROMETHEUS_PORT (default 9090) |
| Grafana | grafana/grafana:12.0.1 | Dashboards | GRAFANA_PORT (default 3000). Sirve desde subpath `/huachicol/` (`GF_SERVER_SERVE_FROM_SUB_PATH=true`, hardcoded en docker-compose). |
| Alertmanager | prom/alertmanager:v0.28.1 | Alertas a Discord | ALERTMANAGER_PORT (default 9002) |
| Loki | grafana/loki:3.4.2 | Logs centralizados | LOKI_PORT (default 9003) |
| Node Exporter | prom/node-exporter:v1.8.2 | Metricas hardware | NODE_EXPORTER_PORT (default 9010) |
| cAdvisor | gcr.io/cadvisor/cadvisor:v0.55.1 | Metricas contenedores | CADVISOR_PORT (default 9011) |
| nginx-auth | nginx:1.28-alpine | Basic auth para Prometheus/Loki | PROMETHEUS_AUTH_PORT/LOKI_AUTH_PORT (default 9091/3101) |

Agente remoto (`agent/`, nombre: `huachicol-agent`): **Alloy v1.16.1** (logs + node metrics consolidados) + cadvisor (v0.55.1) + postgres-exporter (v0.17.1, opcional). Profiles: `all` (alloy + cadvisor), `telemetry` (solo alloy), `cadvisor`, `postgres`. Containers con prefijo `huachicol-`. Alloy expone su HTTP server en `:12345`; cadvisor y postgres-exporter siguen exponiendo en `/huachicol`.

### Gateway-Hub (`/home/egar/IIEG/gateway-hub`)

Reverse proxy NGINX — punto de entrada unico para todos los servicios publicos.
- SSL/TLS (TLS 1.2+), HSTS, rate limiting por zonas (general/api/static/geoserver), cache GeoServer (2GB/6h) + cache MapaLab assets (500MB/7d)
- Control de acceso VPN para rutas admin
- Exporta metricas NGINX a Prometheus y logs a Loki
- Imagen custom: nginx:1.28.2-alpine + envsubst

### Acervo (`/home/egar/IIEG/acervo`)

Almacenamiento S3 basado en MinIO. Buckets: mapalab, dateengine, portal, huachicol (backups).
- Backup mensual automatizado via cron
- Conectado a iieg-network para que Prometheus scrapee metricas

---

## Arquitectura de red

```
                    INTERNET / RED INTERNA
                            |
                [Gateway-Hub NGINX :443/:80]
                ┌───────────┼───────────────────────────┐
                |           |           |               |
          [Portal]    [MapaLab]   [Acervo]    [GeoServer]
          :8000       :80         :9000        :8080

    ┌──────────────────────────────────────────────────────────┐
    │                STACK DE MONITOREO (Huachicol)             │
    │  Prometheus ──scrape──> node-exporter, cadvisor, nginx    │
    │  Alertmanager ──webhook──> Discord (3 canales)            │
    │  Loki <──promtail── logs Docker                           │
    │  Grafana (visualiza Prometheus + Loki)                    │
    │  nginx-auth (basic auth para Prometheus y Loki externos)  │
    └──────────────────────────────────────────────────────────┘
```

**Red Docker compartida:** `iieg-network` (external bridge).

---

## Estructura de directorios de Huachicol

```
huachicol/
├── docker-compose.yml              # 8 servicios + nginx-auth
├── Makefile                        # start, stop, restart, backup, restore, backup-list, agent-*, targets
├── .env.example                    # Variables: credenciales, IPs, puertos, targets
├── .gitignore                      # .env + prometheus/targets/*.json (generados)
├── prometheus/
│   ├── prometheus.yml              # 9 scrape jobs (5 estaticos + 4 file_sd), scrape_interval 15s
│   ├── rules/alerts.yml            # 3 grupos: service_alerts, database_alerts, monitoring_stack_alerts
│   └── targets/
│       └── *.json                       # Generados por make targets (en .gitignore)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml  # Prometheus (default), Loki
│   │   └── dashboards/dashboards.yml    # 3 providers: default, projects, infrastructure
│   └── dashboards/
│       ├── home.json               # Dashboard "IIEG - Vista General" (25 paneles, 5 secciones)
│       ├── projects/.gitkeep
│       └── infrastructure/.gitkeep
├── alertmanager/
│   └── alertmanager.yml.template   # Template — webhook se inyecta desde .env via sed
├── loki/loki-config.yml            # retention_enabled: true, 744h, TSDB
├── nginx-auth/
│   ├── nginx.conf                  # Proxy auth para Prometheus(:9091) y Loki(:3101)
│   └── entrypoint.sh              # Genera htpasswd desde env vars
├── agent/
│   ├── docker-compose.yml          # huachicol-agent: alloy, cadvisor, postgres-exporter (profiles: all, telemetry, cadvisor, postgres)
│   ├── .env.example                # SERVER_NAME, LOKI_URL, puertos, POSTGRES_DSN
│   └── config.alloy                # Alloy: logs (docker + syslog) + prometheus.exporter.unix
├── scripts/
│   ├── start.sh                    # Genera targets + docker compose up
│   ├── stop.sh
│   ├── logs.sh
│   ├── generate-targets.sh         # Genera targets JSON desde variables del .env
│   ├── backup.sh                   # Backup a MinIO (Prometheus snapshot + Grafana + Loki + config)
│   ├── restore.sh                  # Restaurar backup desde MinIO (todo o por componente)
│   └── backup-cron                 # Cron: domingos 3AM
├── docs/
│   ├── agregar-proyecto.md         # Como agregar proyectos/targets al monitoreo + MinIO JWT
│   ├── configuracion-env.md       # Guia para obtener cada variable del .env (orientada a GCP)
│   ├── onboarding-agente.md        # Guia para desplegar agente en servidor nuevo
│   └── pendientes/
│       ├── authentik.md            # Plan futuro: reemplazar basic auth con Authentik IdP
│       └── gateway-improvements.md # Rate limiting, log rotation, Promtail → Alloy
├── docs/context.md                 # Este archivo
├── .github/workflows/validate.yml  # CI: yamllint, docker compose config, promtool check
├── LICENSE                         # MIT
└── README.md
```

---

## Proyectos del IIEG que pasan por el gateway

| Proyecto | Ruta | Backend | Acceso |
|---|---|---|---|
| Portal IIEG | `/`, `/api/`, `/administrador/` | host.docker.internal:8000 | Publico |
| MapaLab | `/mapalab/` | mapalab-staging-nginx-1:80 | Publico |
| Acervo API | `/acervo/` | host.docker.internal:8333 (SeaweedFS S3) | Publico |
| GeoServer OWS/WFS/WCS | `/geoserver/ows`, etc | host.docker.internal:8080 | Publico (cache+validacion) |
| GeoServer Admin | `/geoserver/web`, `/geoserver/rest` | host.docker.internal:8080 | VPN-only |
| MARIACHI | `/mariachi/` | host.docker.internal:*pendiente* | VPN-only |
| Grafana | `/huachicol/` | host.docker.internal:3000 | VPN-only |

---

## Prometheus: scrape jobs

### Jobs estaticos (stack de monitoreo)
| Job | Target | Etiquetas |
|---|---|---|
| prometheus | localhost:9090 | service=prometheus |
| grafana | grafana:3000 | service=grafana |

> **Nota:** El job `grafana` usa `metrics_path: /huachicol/metrics` porque Grafana sirve desde subpath (`SERVE_FROM_SUB_PATH=true`). Los demas exporters usan `/huachicol` directamente via flags de arranque.
| loki | loki:3100 | service=loki |
| alertmanager | alertmanager:9093 | service=alertmanager |

### Jobs dinamicos (file_sd_configs, generados por `make targets`)
| Job | Archivo targets | metrics_path | Contenido |
|---|---|---|---|
| projects | projects.json | /metrics | Backends de proyectos (mapalab, mariachi, gateway, etc.) |
| acervo-seaweedfs | acervo-seaweedfs.json | /metrics | SeaweedFS (filer/master/volume metrics) |
| node-exporter | node-exporter.json | /huachicol (monitoring) o `/api/v0/component/prometheus.exporter.unix.host/metrics` (remotos via Alloy) | Metricas de host. El path remoto se override por target con `__metrics_path__` en file_sd |
| cadvisor | cadvisor.json | /huachicol | Metricas de contenedores por servidor (monitoring + remotos) |
| postgres-exporter | postgres-exporter.json | /huachicol | PostgreSQL via postgres-exporter del agente |

Los exporters desplegados por el agente usan `/huachicol` como endpoint de metricas (en vez del estandar `/metrics`). Esto se configura con flags de arranque: `--web.telemetry-path=/huachicol` (node-exporter, postgres-exporter) y `-prometheus_endpoint=/huachicol` (cadvisor).

Los targets se configuran via variables en `.env` y se generan con `make targets`.
Ver `docs/agregar-proyecto.md` para instrucciones detalladas.

---

## Alertas configuradas

### service_alerts
- **ServiceDown** (critical, 1m): `up == 0`
- **HighLatency** (warning, 5m): latencia > 1s (con guarda `count > 0` desde 1.19.2 para evitar `+Inf` cuando el servicio esta idle)
- **HighErrorRate** (critical, 2m): errores 5xx > 5% (con guarda `total > 0` desde 1.19.2)
- **HighMemoryUsage** (warning, 5m): memoria > 90%
- **DiskSpaceLow** (warning, 5m): disco < 10%

### ecosystem_integration_alerts (desde 1.19.3)
- **MariachiTreeNotifyFailures** (warning, 1m): `increase(mariachi_tree_notify_failed_total[10m]) > 0`. Detecta drift de `MAPALAB_INTERNAL_TOKEN` entre mariachi y mapalab, caida de `mapalab-backend` o red rota.

### database_alerts
- **PostgreSQLDown** (critical, 1m): `pg_up == 0`
- **TooManyConnections** (warning, 5m): conexiones > 80%

### monitoring_stack_alerts
- **LokiDown** (critical, 1m)
- **GrafanaDown** (critical, 1m)
- **AlertmanagerDown** (critical, 1m)
- **PrometheusStorageHigh** (warning, 10m): TSDB > 30% disco
- **PrometheusTargetScrapeFailure** (warning, 5m)
- **LokiHighIngestionRate** (warning, 5m): > 10MB/s

### Canales Discord
- `alertas-criticas` — severity=critical
- `alertas-warnings` — severity=warning
- `alertas-database` — service=postgres|mysql

---

## Seguridad

### Autenticacion (estado actual)
- **Prometheus y Loki:** Protegidos con basic auth via nginx-auth sidecar (puertos 9091 y 3101)
- **Grafana:** Auth propia con usuario/password de .env. Sirve desde subpath `/huachicol/` via `GF_SERVER_SERVE_FROM_SUB_PATH=true` (hardcoded en docker-compose).
- **Exporters del agente:** Alloy expone metricas en `:12345` (path por componente); cadvisor y postgres-exporter en `/huachicol`
- **MinIO:** Metricas protegidas con JWT (bearer_token_file)
- **Plan futuro:** Migrar a Authentik (ver `docs/pendientes/authentik.md`)

### Acervo (backups, S3-compatible via SeaweedFS)
- Huachicol usa credenciales de `huachicol-user` (definido en `acervo/config/identities.json`), con `actions: ["Read:huachicol","Write:huachicol"]` — scoped al bucket `huachicol`.
- Las variables `MINIO_BUCKET_USER` y `MINIO_BUCKET_PASSWORD` en el `.env` **no son credenciales de admin**. El prefijo `MINIO_` se conserva porque el script `backup.sh` usa el cliente `mc` (MinIO Client) que es S3-compatible.

### Gateway
- TLS 1.2+ con cifrados ECDHE, HSTS 1 ano
- Rate limiting: 10 req/s general, 10 req/s API, 10 req/s GeoServer
- VPN-only: Grafana, GeoServer admin, MARIACHI
- Bot blocking, referrer validation, WFS-T bloqueado (POST + query string) en GeoServer

---

## Retencion y backups

| Servicio | Retencion |
|---|---|
| Prometheus | 30 dias |
| Loki | 744 horas (30 dias), compactor con retention_enabled: true |
| Backups | 30 dias en MinIO (bucket: huachicol), semanal |

### Backup (`make backup`)
Respalda: snapshot Prometheus (via admin API), datos Grafana, datos Loki, archivos de configuracion.
Sube a MinIO como `huachicol/monthly/backup-YYYY-MM-DD.tar.gz`.
Rotacion automatica: elimina backups > 30 dias (~4-5 backups retenidos).

### Restore (`make restore DATE=YYYY-MM-DD [COMPONENT=...]`)
Descarga backup de MinIO, detiene servicios, restaura volumenes, reinicia.
Componentes: `all` (default), `grafana`, `prometheus`, `loki`, `config`.

### Otros
- `make backup-list` — listar backups disponibles en MinIO
- `make backup-cron-install` — cron semanal (domingos, 3AM)
- `make backup-cron-remove` — desinstalar cron

---

## Variables de entorno (.env.example)

```
# Grafana
GRAFANA_USER, GRAFANA_PASSWORD, GRAFANA_ROOT_URL (debe incluir subpath, ej: https://dominio/huachicol/), GRAFANA_ALLOW_SIGN_UP, GRAFANA_PLUGINS

# Discord
DISCORD_WEBHOOK_URL

# Auth basica (temporal)
MONITORING_AUTH_USER, MONITORING_AUTH_PASSWORD

# IPs servidores remotos (solo production)
PORTAL_SERVER_IP, MAPALAB_SERVER_IP, MARIACHI_SERVER_IP, GEOSERVER_SERVER_IP

# Targets de proyectos (formato host:puerto, dejar vacio si no aplica)
MAPALAB_BACKEND_TARGET, MARIACHI_BACKEND_TARGET, GATEWAY_NGINX_TARGET
DATAENGINE_POSTGRES_TARGET
ACERVO_METRICS_TARGET

# MinIO backups (credenciales de huachicol-user, no admin)
MINIO_ENDPOINT, MINIO_BUCKET_USER, MINIO_BUCKET_PASSWORD

# Puertos
GRAFANA_PORT=3000, PROMETHEUS_PORT=9090, ALERTMANAGER_PORT=9002, LOKI_PORT=9003
NODE_EXPORTER_PORT=9010, CADVISOR_PORT=9011
PROMETHEUS_AUTH_PORT=9091, LOKI_AUTH_PORT=3101
```

---

## Resource limits (docker-compose)

| Servicio | RAM | CPU |
|---|---|---|
| Prometheus | 1G | 1.0 |
| Grafana | 512M | 0.5 |
| Alertmanager | 256M | 0.25 |
| Loki | 1G | 1.0 |
| Node Exporter | 128M | 0.25 |
| Alloy (agente) | 512M | 0.5 |
| cAdvisor | 256M | 0.5 |
| nginx-auth | 128M | 0.25 |

---

## Healthchecks

Todos los servicios tienen healthcheck configurado. Grafana depende de Prometheus y Loki (service_healthy). nginx-auth depende de ambos tambien. El healthcheck de Grafana usa `/huachicol/api/health` (por el subpath).

---

## Entornos e infraestructura

### Entornos

| Entorno | Donde corre | Caracteristicas |
|---|---|---|
| **dev** | Maquina local del desarrollador | Todos los servicios en un mismo servidor. Para desarrollo y pruebas locales. |
| **staging** | Servidor local (on-prem) | Todos los servicios en un mismo servidor. Replica de produccion para pruebas pre-release. |
| **staging (GCP)** | Google Cloud Platform | Todos los servicios en un mismo servidor/VM. Mismo esquema que staging local pero en la nube. |
| **production (GCP)** | Google Cloud Platform | **Cada servicio tiene su propio servidor.** Separacion real por proyecto/rol. Gestionado por administracion. |

### Implicaciones por entorno

- **dev / staging / staging GCP:** Todos los servicios corren en la misma maquina. Los targets de Prometheus apuntan a `localhost`, `host.docker.internal` o IPs de la misma red local. No se necesitan agentes remotos — el node-exporter y cadvisor del stack central cubren todo.
- **production (GCP):** Cada proyecto (Portal, MapaLab, Acervo, GeoServer, MARIACHI) corre en su propia VM. Se requiere desplegar el agente remoto (`agent/`) en cada servidor. Los targets de Prometheus usan IPs reales de cada VM. El gateway es el unico punto de entrada publico. Este entorno es gestionado por el equipo de administracion. **Firewall:** GCP no tiene los puertos abiertos por defecto — la apertura de puertos se debe solicitar al equipo de administracion.

### Servidores en produccion (GCP)

| Servidor | Servicios que corre | Rol |
|---|---|---|
| **monitoring** | Huachicol (stack completo de monitoreo) | Observabilidad centralizada |
| **portal** | Portal web del IIEG + agente de monitoreo | Sitio web principal |
| **mapalab** | MapaLab + agente de monitoreo | Plataforma de mapas |
| **mariachi** | MARIACHI + agente de monitoreo | Servicio MARIACHI |
| **geoserver** | GeoServer + agente de monitoreo | Datos geoespaciales |
| **acervo** | Acervo (MinIO) + agente de monitoreo | Almacenamiento S3 |

El gateway corre en el mismo servidor que el portal (o en su propia VM segun la configuracion).

### Dominio
- **staging:** IP interna (ver .env)
- **production:** dominio publico del IIEG (ver .env)

---

## Comandos de operacion

```bash
# Stack principal
make start / stop / restart / logs / status / clean

# Targets (regenerar despues de cambiar IPs o targets en .env)
make targets

# Agente remoto (huachicol-agent) — Alloy + cAdvisor + postgres-exporter (opcional)
make agent-start                                       # Profile all (alloy + cadvisor)
make agent-start PROFILES="telemetry"                  # Solo Alloy (logs + node metrics)
make agent-start PROFILES="telemetry cadvisor postgres" # Incluir postgres-exporter
make agent-stop / agent-restart / agent-logs / agent-status / agent-clean

# Backups y restore
make backup                                        # Backup manual a MinIO
make backup-list                                   # Listar backups disponibles
make restore DATE=2026-04-03                       # Restaurar todo
make restore DATE=2026-04-03 COMPONENT=grafana     # Restaurar solo Grafana
make backup-cron-install / backup-cron-remove       # Cron semanal (domingos, 3AM)
```

---

## CI/CD

- **CI:** `.github/workflows/validate.yml` — yamllint, docker compose config, promtool check rules
- **CD:** Preparado (comentado) para SSH deploy cuando se configure

---

## Notas de implementacion

- Los targets de Prometheus se **generan** desde variables del `.env` via `scripts/generate-targets.sh` (`make targets`). Los `.json` generados estan en `.gitignore`.
- El webhook de Discord se inyecta en alertmanager via `sed` en el entrypoint (template en `alertmanager.yml.template`).
- nginx-auth genera el `.htpasswd` en el entrypoint desde env vars `MONITORING_AUTH_USER`/`MONITORING_AUTH_PASSWORD`.
- Prometheus tiene `--web.enable-lifecycle`, `--web.enable-remote-write-receiver` y `--web.enable-admin-api` (para snapshots de backup) habilitados.
- Alloy del agente reemplaza a Promtail + node-exporter standalone. Logs via `loki.source.docker` (socket Docker) + `loki.source.file` (syslog); metricas de host via `prometheus.exporter.unix`. Positions y estado en volumen `alloy_data`.
- Loki tiene `retention_enabled: true` en el compactor — la retencion de 744h si se aplica.
- Todas las imagenes Docker estan pinneadas a versiones estables especificas. cAdvisor requiere v0.55.1+ para compatibilidad con Docker 29 + storage driver `overlayfs` + cgroups v2.
- Acervo (SeaweedFS) expone metricas en `/metrics` sin auth, en el puerto configurado con `-metricsPort` (default `acervo-seaweedfs:9091`). Se configura via `ACERVO_METRICS_TARGET` del `.env` de huachicol. Ver `docs/agregar-proyecto.md`.
- Los backups usan credenciales de `huachicol-user` definido en `acervo/config/identities.json` (SeaweedFS), con `actions: ["Read:huachicol","Write:huachicol"]` scoped al bucket `huachicol`. El bucket y el usuario se gestionan desde Acervo (`scripts/init-seaweedfs.sh` + `make restart`), no desde huachicol.
- cAdvisor y postgres-exporter del agente sirven en `/huachicol`. Alloy del agente expone su HTTP server en `:12345`; las metricas de host se scrapean en `/api/v0/component/prometheus.exporter.unix.host/metrics` (override `__metrics_path__` por target en file_sd).
- Profiles del agente: `all` (alloy + cadvisor), `telemetry` (solo alloy), `cadvisor`, `postgres`. En servidores donde gateway ya empuja logs propios, usar `PROFILES="cadvisor"` para evitar duplicados de Docker logs.
- Los containers del agente usan prefijo `huachicol-` (ej: `huachicol-alloy`, `huachicol-cadvisor`) para evitar conflictos de nombre con otros proyectos en el mismo servidor.
- postgres-exporter requiere `POSTGRES_DSN` en el `.env` del agente. Se conecta a `dataengine-network` e `iieg-network`.
- cAdvisor usa `-store_container_labels=true` para exportar labels de Docker (name, image, compose project). El volumen `/var/run` se monta read-write para acceso al socket de Docker.
