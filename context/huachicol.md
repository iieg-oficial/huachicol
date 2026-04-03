# Contexto Completo del Ecosistema IIEG: Huachicol + Gateway-Hub

> Referencia completa para que cualquier sesion de Claude Code entienda el ecosistema sin re-analizar archivos.
> Ultima actualizacion: 2026-04-03

---

## Quien lo usa

- **Organizacion:** IIEG (Instituto de Informacion Estadistica y Geografica de Jalisco) — organismo publico del gobierno de Jalisco, Mexico.
- **Equipo:** Desarrollo de software del IIEG, liderado por Edgar Villarreal.
- **Usuarios del monitoreo:** Equipo de desarrollo y operaciones.
- **Usuarios finales:** Ciudadanos y funcionarios que acceden a los portales publicos.

---

## Que es cada proyecto

### Huachicol (`/home/egar/IIEG/huachicol`)

Stack centralizado de monitoreo y observabilidad. Servicios Docker:

| Servicio | Imagen | Funcion | Puerto host |
|---|---|---|---|
| Prometheus | prom/prometheus:v3.2.1 | Metricas (scraping) | PROMETHEUS_PORT (default 9090) |
| Grafana | grafana/grafana:12.0.1 | Dashboards | GRAFANA_PORT (default 3000) |
| Alertmanager | prom/alertmanager:v0.28.1 | Alertas a Discord | ALERTMANAGER_PORT (default 9002) |
| Loki | grafana/loki:3.4.2 | Logs centralizados | LOKI_PORT (default 9003) |
| Tempo | grafana/tempo:2.7.0 | Trazas distribuidas | TEMPO_PORT (default 9004) |
| Node Exporter | prom/node-exporter:v1.8.2 | Metricas hardware | NODE_EXPORTER_PORT (default 9010) |
| cAdvisor | gcr.io/cadvisor/cadvisor:v0.51.0 | Metricas contenedores | CADVISOR_PORT (default 9011) |
| nginx-auth | nginx:1.28-alpine | Basic auth para Prometheus/Loki | PROMETHEUS_AUTH_PORT/LOKI_AUTH_PORT (default 9091/3101) |

Agente remoto (`agent/`, nombre: `huachicol-agent`): node-exporter (v1.8.2) + cadvisor (v0.51.0) + promtail (3.4.2) + postgres-exporter (v0.17.1, perfil opcional). Todos los exporters del agente sirven metricas en `/huachicol` en vez de `/metrics`.

### Gateway-Hub (`/home/egar/IIEG/gateway-hub`)

Reverse proxy NGINX — punto de entrada unico para todos los servicios publicos.
- SSL/TLS (TLS 1.2+), HSTS, rate limiting, cache GeoServer (2GB/6h)
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
    │  Tempo <──OTLP/Jaeger── trazas de backends                │
    │  Grafana (visualiza Prometheus + Loki + Tempo)            │
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
├── .env.example                    # Variables: credenciales, IPs, puertos, MinIO
├── .gitignore                      # .env + prometheus/targets/*.json (generados)
├── prometheus/
│   ├── prometheus.yml              # 10 scrape jobs (5 estaticos + 5 file_sd), scrape_interval 15s
│   ├── rules/alerts.yml            # 3 grupos: service_alerts, database_alerts, monitoring_stack_alerts
│   └── targets/
│       ├── *.json                       # Generados por make targets (en .gitignore)
│       └── minio-token                  # JWT para scraping MinIO (generado)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml  # Prometheus (default), Loki, Tempo
│   │   └── dashboards/dashboards.yml    # 3 providers: default, projects, infrastructure
│   └── dashboards/
│       ├── home.json               # Dashboard "IIEG - Vista General" (25 paneles, 5 secciones)
│       ├── projects/.gitkeep
│       └── infrastructure/.gitkeep
├── alertmanager/
│   └── alertmanager.yml.template   # Template — webhook se inyecta desde .env via sed
├── loki/loki-config.yml            # retention_enabled: true, 744h, TSDB
├── tempo/tempo-config.yml          # 168h retention, OTLP+Jaeger+Zipkin, metrics_generator → Prometheus
├── nginx-auth/
│   ├── nginx.conf                  # Proxy auth para Prometheus(:9091) y Loki(:3101)
│   └── entrypoint.sh              # Genera htpasswd desde env vars
├── agent/
│   ├── docker-compose.yml          # huachicol-agent: node-exporter, cadvisor, promtail, postgres-exporter (perfil)
│   ├── .env.example                # SERVER_NAME, LOKI_URL, puertos, POSTGRES_DSN
│   └── promtail-config.yml         # backoff_config, batchwait, positions persistentes
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
│   ├── onboarding-agente.md        # Guia para desplegar agente en servidor nuevo
│   └── pendientes/
│       ├── authentik.md            # Plan futuro: reemplazar basic auth con Authentik IdP
│       └── gateway-improvements.md # Rate limiting, log rotation, Promtail → Alloy
├── context/huachicol.md            # Este archivo
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
| Acervo API | `/acervo/` | host.docker.internal:9000 | Publico |
| Acervo Console | `/acervo/console/` | host.docker.internal:9001 | VPN-only |
| GeoServer OWS/WFS/WCS | `/geoserver/ows`, etc | host.docker.internal:8080 | Publico (cache+validacion) |
| GeoServer Admin | `/geoserver/web`, `/geoserver/rest` | host.docker.internal:8080 | VPN-only |
| MARIACHI | `/mariachi/` | host.docker.internal:TBD | VPN-only |
| Grafana | `/huachicol/` | host.docker.internal:3000 | VPN-only |

---

## Prometheus: scrape jobs

### Jobs estaticos (stack de monitoreo)
| Job | Target | Etiquetas |
|---|---|---|
| prometheus | localhost:9090 | service=prometheus |
| grafana | grafana:3000 | service=grafana |
| loki | loki:3100 | service=loki |
| tempo | tempo:3200 | service=tempo |
| alertmanager | alertmanager:9093 | service=alertmanager |

### Jobs dinamicos (file_sd_configs, generados por `make targets`)
| Job | Archivo targets | metrics_path | Contenido |
|---|---|---|---|
| projects | projects.json | /metrics | Backends de proyectos (urlschiquitas, mapalab, gateway, etc.) |
| minio | minio.json | /minio/v2/metrics/cluster | MinIO con bearer_token_file para JWT auth |
| node-exporter | node-exporter.json | /huachicol | Metricas de host por servidor (monitoring + remotos) |
| cadvisor | cadvisor.json | /huachicol | Metricas de contenedores por servidor (monitoring + remotos) |
| postgres-exporter | postgres-exporter.json | /huachicol | PostgreSQL via postgres-exporter del agente |

Los exporters desplegados por el agente usan `/huachicol` como endpoint de metricas (en vez del estandar `/metrics`). Esto se configura con flags de arranque: `--web.telemetry-path=/huachicol` (node-exporter, postgres-exporter) y `-prometheus_endpoint=/huachicol` (cadvisor).

Los targets se configuran via variables en `.env` y se generan con `make targets`.
Ver `docs/agregar-proyecto.md` para instrucciones detalladas.

---

## Alertas configuradas

### service_alerts
- **ServiceDown** (critical, 1m): `up == 0`
- **HighLatency** (warning, 5m): latencia > 1s
- **HighErrorRate** (critical, 2m): errores 5xx > 5%
- **HighMemoryUsage** (warning, 5m): memoria > 90%
- **DiskSpaceLow** (warning, 5m): disco < 10%

### database_alerts
- **PostgreSQLDown** (critical, 1m): `pg_up == 0`
- **TooManyConnections** (warning, 5m): conexiones > 80%

### monitoring_stack_alerts
- **LokiDown** (critical, 1m)
- **TempoDown** (critical, 1m)
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
- **Grafana:** Auth propia con usuario/password de .env
- **Exporters del agente:** Endpoint de metricas en `/huachicol` en vez de `/metrics` (node-exporter, cadvisor, postgres-exporter)
- **MinIO:** Metricas protegidas con JWT (bearer_token_file)
- **Plan futuro:** Migrar a Authentik (ver `docs/pendientes/authentik.md`)

### Gateway
- TLS 1.2+ con cifrados ECDHE, HSTS 1 ano
- Rate limiting: 10 req/s general, 10 req/s API, 10 req/s GeoServer
- VPN-only: Grafana, GeoServer admin, MARIACHI, Acervo Console
- Bot blocking, referrer validation, transaction blocking en GeoServer

---

## Retencion y backups

| Servicio | Retencion |
|---|---|
| Prometheus | 30 dias |
| Loki | 744 horas (30 dias), compactor con retention_enabled: true |
| Tempo | 168 horas (7 dias) |
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
GRAFANA_USER, GRAFANA_PASSWORD, GRAFANA_ROOT_URL, GRAFANA_ALLOW_SIGN_UP, GRAFANA_PLUGINS

# Discord
DISCORD_WEBHOOK_URL

# Auth basica (temporal)
MONITORING_AUTH_USER, MONITORING_AUTH_PASSWORD

# IPs servidores remotos (solo production)
PORTAL_SERVER_IP, MAPALAB_SERVER_IP, MARIACHI_SERVER_IP, GEOSERVER_SERVER_IP

# Targets de proyectos (formato host:puerto, dejar vacio si no aplica)
URLSCHIQUITAS_BACKEND_TARGET, URLSCHIQUITAS_POSTGRES_TARGET
MAPALAB_BACKEND_TARGET, GATEWAY_NGINX_TARGET
DATAENGINE_POSTGRES_TARGET
ACERVO_MINIO_TARGET, ACERVO_MINIO_TOKEN (JWT)

# MinIO backups
MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY

# Puertos
GRAFANA_PORT=3000, PROMETHEUS_PORT=9090, ALERTMANAGER_PORT=9002, LOKI_PORT=9003
TEMPO_PORT=9004, NODE_EXPORTER_PORT=9010, CADVISOR_PORT=9011
PROMETHEUS_AUTH_PORT=9091, LOKI_AUTH_PORT=3101
TEMPO_OTLP_GRPC_PORT=4317, TEMPO_OTLP_HTTP_PORT=4318, TEMPO_ZIPKIN_PORT=9411, TEMPO_JAEGER_PORT=14268
```

---

## Resource limits (docker-compose)

| Servicio | RAM | CPU |
|---|---|---|
| Prometheus | 1G | 1.0 |
| Grafana | 512M | 0.5 |
| Alertmanager | 256M | 0.25 |
| Loki | 1G | 1.0 |
| Tempo | 512M | 0.5 |
| Node Exporter | 128M | 0.25 |
| cAdvisor | 256M | 0.5 |
| nginx-auth | 128M | 0.25 |

---

## Healthchecks

Todos los servicios tienen healthcheck configurado. Grafana depende de Prometheus y Loki (service_healthy). nginx-auth depende de ambos tambien.

---

## Entornos e infraestructura

### Entornos

| Entorno | Donde corre | Caracteristicas |
|---|---|---|
| **dev** | Maquina local del desarrollador | Todos los servicios en el mismo servidor. Para desarrollo y pruebas locales. |
| **staging** | Servidor local | Todos los servicios en el mismo servidor. Replica de produccion para pruebas pre-release. |
| **production (GCP)** | Google Cloud Platform | **Cada servicio tiene su propio servidor.** Separacion real por proyecto/rol. |

### Implicaciones por entorno

- **dev/staging:** Los targets de Prometheus apuntan a `localhost`, `host.docker.internal` o IPs de la misma red local. El gateway, los backends, el monitoreo y los agentes corren todos en la misma maquina. No se necesitan agentes remotos — el node-exporter y cadvisor del stack central cubren todo.
- **production (GCP):** Cada proyecto (Portal, MapaLab, Acervo, GeoServer, MARIACHI) corre en su propia VM. Se requiere desplegar el agente remoto (`agent/`) en cada servidor. Los targets de Prometheus usan IPs reales de cada VM. El gateway es el unico punto de entrada publico.

### Servidores en produccion (GCP)

| Servidor | Servicios que corre | Rol |
|---|---|---|
| **monitoring** | Huachicol (stack completo de monitoreo) | Observabilidad centralizada |
| **portal** | Portal web del IIEG + agente de monitoreo | Sitio web principal |
| **mapalab** | MapaLab + agente de monitoreo | Plataforma de mapas |
| **mariachi** | MARIACHI + agente de monitoreo | Servicio MARIACHI |
| **geoserver** | GeoServer + agente de monitoreo | Datos geoespaciales |

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

# Agente remoto (huachicol-agent)
make agent-start / agent-stop / agent-restart / agent-logs / agent-status / agent-clean

# Backups y restore
make backup                                        # Backup manual a MinIO
make backup-list                                   # Listar backups disponibles
make restore DATE=2026-04-03                       # Restaurar todo
make restore DATE=2026-04-03 COMPONENT=grafana     # Restaurar solo Grafana
make backup-cron-install / backup-cron-remove       # Cron mensual
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
- Tempo genera metricas (service-graphs, span-metrics) y las envia a Prometheus via remote write.
- Promtail del agente tiene `backoff_config` y positions persistentes en volumen nombrado.
- Loki tiene `retention_enabled: true` en el compactor — la retencion de 744h si se aplica.
- Todas las imagenes Docker estan pinneadas a versiones estables especificas.
- MinIO expone metricas via JWT auth. El token se genera desde Acervo con `make prometheus-token` y se pone en `ACERVO_MINIO_TOKEN` del `.env` de huachicol. Ver `docs/agregar-proyecto.md`.
- Los exporters del agente (node-exporter, cadvisor, postgres-exporter) sirven en `/huachicol` en vez de `/metrics`. Prometheus los scrapea con `metrics_path: /huachicol`.
- postgres-exporter se activa con Docker Compose profiles: `docker compose --profile postgres up -d`. Requiere `POSTGRES_DSN` en el `.env` del agente. Se conecta a `dataengine-network` e `iieg-network`.
