# Contrato `/ontoy` v2

Endpoint de identidad y salud que expone cada servicio del ecosistema IIEG. Lo consume
`huachicol-monitor` para el estado del ecosistema, y Mariachi para la vista de plataformas.

> v1 solo devolvia `version`, `service` y `released_at`. v2 **agrega** campos sin quitar
> ninguno: cualquier consumidor de v1 sigue funcionando sin cambios.

---

## Respuesta

```json
{
  "service": "huachicol",
  "version": "1.23.0",
  "released_at": "2026-07-20",
  "deployed_at": "2026-07-20T21:21:47Z",
  "status": "ok",
  "checks": {
    "disk":       { "status": "ok", "used_percent": 51.4, "free_gb": 408.1 },
    "containers": { "status": "ok", "total": 10, "running": 10 }
  },
  "containers": [
    { "name": "prometheus", "state": "running", "health": "healthy",
      "image": "prom/prometheus:v3.2.1", "project": "huachicol" }
  ]
}
```

### Campos

| Campo | Tipo | Obligatorio | Descripcion |
|---|---|---|---|
| `service` | string | si | Identificador del servicio (`huachicol`, `mapalab`, …) |
| `version` | string | si | Version del repo desplegada |
| `released_at` | date | no | Fecha del release segun el CHANGELOG |
| `deployed_at` | datetime ISO-8601 UTC | no | **Cuando se desplego realmente** este artefacto |
| `status` | enum | si (v2) | `ok` \| `degraded` \| `down` |
| `checks` | objeto | no | Resultado por verificacion; cada valor lleva su propio `status` |
| `containers` | array | no | Contenedores del proyecto en ese host |

`released_at` y `deployed_at` no son lo mismo: se puede redesplegar sin cambiar de version.
Para "ultima actualizacion" en un panel, usar `deployed_at`.

### Codigos HTTP

| Situacion | Codigo |
|---|---|
| `status` = `ok` o `degraded` | `200` |
| `status` = `down` | `503` |

El 503 permite que cualquier monitor detecte el fallo sin parsear el cuerpo. El cuerpo
**siempre** es JSON valido, incluso con 503, para no perder el diagnostico.

### Semantica de `status`

- **`ok`** — el servicio y sus dependencias responden.
- **`degraded`** — funciona pero algo esta mal (disco al 85%, un contenedor no esencial
  detenido). Requiere atencion, no es urgencia.
- **`down`** — el servicio no puede cumplir su funcion (base de datos caida, disco al 95%).

`status` es **el peor** de los `checks`. Con un check en `down`, el servicio esta `down`.

---

## Implementacion de referencia

`version-api/ontoy_server.py` en este repo. Python estandar, sin dependencias externas.
Copiarlo tal cual y configurar por variables de entorno:

| Variable | Default | Para que sirve |
|---|---|---|
| `ONTOY_SERVICE` | `huachicol` | Nombre del servicio |
| `ONTOY_COMPOSE_PROJECT` | vacio | Filtra contenedores por proyecto compose. Vacio = todos |
| `ONTOY_DISK_PATH` | `/` | Ruta a medir. Montar el disco del host y apuntar aqui |
| `ONTOY_DISK_WARN_PERCENT` | `85` | Umbral de `degraded` |
| `ONTOY_DISK_CRITICAL_PERCENT` | `95` | Umbral de `down` |
| `ONTOY_DEPENDENCIES` | vacio | Checks HTTP extra: `nombre=url,otro=url` |
| `ONTOY_PORT_CHECKS` | vacio | Checks TCP de puertos: `nombre=host:puerto,otro=host:puerto`. Cada uno conecta via socket; `ok` si conecta, `down` si no. Util para verificar upstreams/puertos habilitados (ej. el gateway sondea a sus backends) |

### Montajes necesarios

```yaml
version-api:
  environment:
    ONTOY_SERVICE: miservicio
    ONTOY_COMPOSE_PROJECT: miservicio
    ONTOY_DISK_PATH: /host-root
  volumes:
    - ./VERSION:/app/VERSION:ro
    - ./version-api/html/version.json:/app/version.json:ro
    - /var/run/docker.sock:/var/run/docker.sock:ro   # solo si se reportan contenedores
    - /:/host-root:ro                                # solo para el check de disco
```

### Por que el sidecar y no la aplicacion

El socket de Docker equivale a root en el host. Montarlo en un contenedor que recibe
trafico publico (`mapalab-backend`, `mariachi-api`) significa que comprometer esa app da
control del servidor. El sidecar `version-api` no recibe entrada de usuario: su unica
ruta es `/ontoy` y no acepta parametros. **Siempre montar el socket ahi, nunca en la app.**

Se monta `:ro`, aunque conviene saber que el modo lectura del socket no impide operaciones
de escritura contra la API de Docker: la proteccion real es que el proceso sea minimo.

---

## Servicios sin sidecar

`mapalab` y `mariachi` sirven `/ontoy` desde su propio backend (FastAPI). Para v2 basta
con agregar `status` y `checks` al handler existente:

```python
@app.get("/ontoy")
async def ontoy():
    checks = {"db": await _check_db()}
    status = _worst(c["status"] for c in checks.values())
    payload = {
        "service": "mapalab",
        "version": APP_VERSION,
        "released_at": RELEASED_AT,
        "deployed_at": DEPLOYED_AT,
        "status": status,
        "checks": checks,
    }
    return JSONResponse(payload, status_code=503 if status == "down" else 200)
```

No hace falta reportar contenedores desde la app: el sidecar del mismo host ya los cubre.

---

## Estado de adopcion

| Servicio | v2 | Como lo sirve | Checks |
|---|---|---|---|
| huachicol | **si** | sidecar `version-api` | disk, containers |
| geoserver | **si** | sidecar `version-api` | disk, containers |
| acervo | **si** | sidecar `version-api` | disk, containers |
| dataengine | **si** | sidecar en `jobs/` | disk (sin socket: tiene credenciales de BD) |
| mapalab | **si** | backend FastAPI | db |
| mariachi | **si** | backend FastAPI | db, redis |
| gateway-hub | **si** | sidecar `version-api` | disk, containers, 5 puertos de upstreams |
| sieej | **si** | estatico servido por el gateway | ninguno (sin runtime; `status` fijo `ok`) |

Todo el ecosistema esta en v2. Para migrar un repo nuevo: copiar `ontoy_server.py`
(sidecar) o agregar `status`+`checks` al handler (backend), y verificar con
`curl -s http://<host>:8088/ontoy | jq`.

---

## Checks recomendados por servicio

| Servicio | Checks utiles |
|---|---|
| huachicol | disco, contenedores |
| dataengine | disco, conexion a Postgres, conexiones activas vs `max_connections` |
| acervo | disco (critico: guarda archivos), contenedores |
| geoserver | disco, responde el catalogo OGC |
| mapalab | conexion a Postgres, alcance de GeoServer |
| mariachi | conexion a Postgres, Redis |
| gateway-hub | disco (cache de GeoServer 2 GB), upstreams alcanzables |
