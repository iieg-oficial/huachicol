# Agregar un proyecto al monitoreo

## Requisitos

- El proyecto debe exponer un endpoint de metricas Prometheus (`/metrics`)
- Debe ser accesible desde la red Docker `iieg-network` o via `host.docker.internal`

## Pasos

### 1. Agregar la variable en `.env`

Editar `.env` y agregar el target con formato `host:puerto`:

```bash
# Ejemplo: nuevo proyecto "miapp" con metricas en puerto 8080
MIAPP_BACKEND_TARGET=host.docker.internal:8080
```

### 2. Agregar la variable en `.env.example`

Para que quede documentada para otros entornos:

```bash
MIAPP_BACKEND_TARGET=
```

### 3. Registrar en `scripts/generate-targets.sh`

Agregar una linea `add_target` en la seccion de projects:

```bash
# --- projects targets ---
FIRST=true
{
    printf '['
    add_target "${URLSCHIQUITAS_BACKEND_TARGET:-}" "project" "urlschiquitas" ', "service": "backend"'
    # ... targets existentes ...
    add_target "${MIAPP_BACKEND_TARGET:-}" "project" "miapp" ', "service": "backend"'   # <-- nueva linea
    printf '\n]\n'
} > "${TARGETS_DIR}/projects.json"
```

### 4. Regenerar targets

```bash
make targets
```

Prometheus detecta los cambios en ~30 segundos (file_sd_configs con refresh_interval: 30s).

### 5. Verificar en Grafana

- Ir a Explore > Prometheus
- Query: `up{project="miapp"}`
- Debe mostrar valor `1`

---

## Caso especial: MinIO

MinIO usa un endpoint de metricas diferente (`/minio/v2/metrics/cluster`) y requiere autenticacion JWT.

### Generar el token JWT

Desde el proyecto **Acervo** (`/home/egar/IIEG/acervo`):

```bash
make prometheus-token ENV=prod
# o sin Makefile:
# docker run --rm --network <red> --entrypoint sh minio/mc -c \
#   "mc alias set acervo http://acervo-minio:9000 ACCESS SECRET && \
#    mc admin prometheus generate acervo"
```

Copiar el valor de `bearer_token` que se imprime.

### Configurar en huachicol

Editar `.env`:

```bash
ACERVO_MINIO_TARGET=acervo-minio:9000
ACERVO_MINIO_TOKEN=<token JWT generado>
```

Regenerar targets:

```bash
make targets
```

El script genera `prometheus/targets/minio.json` y `prometheus/targets/minio-token`.

### Notas sobre el token

- En **dev/staging** el token se genera desde el MinIO local
- En **produccion** se genera igual pero apuntando al MinIO de produccion
- Si MinIO se reinicia, el token sigue siendo valido (es un JWT firmado con las credenciales de acceso)
- Si cambian las credenciales de MinIO (`MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`), hay que regenerar el token

---

## Agregar un servidor remoto (metricas de host)

Esto agrega metricas de CPU, memoria, disco y contenedores de un servidor remoto.

Ver [docs/onboarding-agente.md](onboarding-agente.md) para la guia completa.

Resumen rapido:

1. Desplegar `agent/` en el servidor remoto
2. En huachicol, agregar la IP en `.env`:
   ```bash
   NUEVO_SERVER_IP=10.x.x.x
   ```
3. Agregar el target en `scripts/generate-targets.sh` (secciones node-exporter y cadvisor)
4. `make targets`

---

## Referencia de targets actuales

| Variable | Proyecto | Servicio |
|---|---|---|
| `URLSCHIQUITAS_BACKEND_TARGET` | urlschiquitas | backend |
| `URLSCHIQUITAS_POSTGRES_TARGET` | urlschiquitas | postgres |
| `MAPALAB_BACKEND_TARGET` | mapalab | backend |
| `MARIACHI_BACKEND_TARGET` | mariachi | backend |
| `GATEWAY_NGINX_TARGET` | gateway-hub | nginx |
| `DATAENGINE_POSTGRES_TARGET` | dataengine | postgres |
| `ACERVO_MINIO_TARGET` | acervo | minio |

| Variable | Servidor |
|---|---|
| `PORTAL_SERVER_IP` | portal |
| `MAPALAB_SERVER_IP` | mapalab |
| `MARIACHI_SERVER_IP` | mariachi |
| `GEOSERVER_SERVER_IP` | geoserver |
