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
    add_target "${MAPALAB_BACKEND_TARGET:-}" "project" "mapalab" ', "service": "backend"'
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

## Caso especial: Acervo (SeaweedFS)

SeaweedFS expone metricas en `/metrics` sin autenticacion, en el puerto configurado con `-metricsPort`.

### Configurar en huachicol

Editar `.env`:

```bash
ACERVO_METRICS_TARGET=acervo-seaweedfs:9091
```

En **production** apuntar al host:puerto del servidor donde corra Acervo (puede ser una IP interna).

Regenerar targets:

```bash
make targets
```

El script genera `prometheus/targets/acervo-seaweedfs.json`.

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
| `MAPALAB_BACKEND_TARGET` | mapalab | backend |
| `MARIACHI_BACKEND_TARGET` | mariachi | backend |
| `GATEWAY_NGINX_TARGET` | gateway-hub | nginx |
| `DATAENGINE_POSTGRES_TARGET` | dataengine | postgres |
| `ACERVO_METRICS_TARGET` | acervo | seaweedfs |

| Variable | Servidor |
|---|---|
| `PORTAL_SERVER_IP` | portal |
| `MAPALAB_SERVER_IP` | mapalab |
| `MARIACHI_SERVER_IP` | mariachi |
| `GEOSERVER_SERVER_IP` | geoserver |
