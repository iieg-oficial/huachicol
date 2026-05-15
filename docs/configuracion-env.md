# Configuracion de variables de entorno

Guia para obtener y configurar cada variable del `.env` de Huachicol, orientada al despliegue en GCP (produccion).

---

## Grafana

| Variable | Como obtenerla |
|---|---|
| `GRAFANA_USER` | Definir manualmente (ej: `admin`) |
| `GRAFANA_PASSWORD` | Definir manualmente, usar contrasena fuerte |
| `GRAFANA_ROOT_URL` | URL publica con subpath: `https://TU_DOMINIO/huachicol/` |
| `GRAFANA_ALLOW_SIGN_UP` | `false` |
| `GRAFANA_PLUGINS` | Dejar vacio o lista de plugins separados por coma |

---

## Discord

| Variable | Como obtenerla |
|---|---|
| `DISCORD_WEBHOOK_URL` | Discord > Tu servidor > Configuracion del canal > Integraciones > Webhooks > Crear webhook > Copiar URL |

---

## Auth basica (temporal hasta Authentik)

| Variable | Como obtenerla |
|---|---|
| `MONITORING_AUTH_USER` | Definir manualmente |
| `MONITORING_AUTH_PASSWORD` | Definir manualmente, usar contrasena fuerte |

---

## IPs de servidores remotos (solo produccion)

Obtener la IP interna de cada VM en GCP:

```bash
gcloud compute instances describe NOMBRE_VM --zone=TU_ZONA --format='get(networkInterfaces[0].networkIP)'
```

| Variable | Comando |
|---|---|
| `PORTAL_SERVER_IP` | Reemplazar `NOMBRE_VM` con el nombre de la VM del portal |
| `MAPALAB_SERVER_IP` | Reemplazar con la VM de mapalab |
| `MARIACHI_SERVER_IP` | Reemplazar con la VM de mariachi |
| `GEOSERVER_SERVER_IP` | Reemplazar con la VM de geoserver |

> Usar `networkIP` (IP interna) si las VMs estan en la misma VPC. Si no, usar `accessConfigs[0].natIP` para la IP externa.

> En entornos uniserver (dev/staging) dejar vacias — el node-exporter y cadvisor del stack central ya cubren todo.

---

## Targets de proyectos

El formato es `HOST:PUERTO`. El host es la IP del servidor donde corre el proyecto, y el puerto depende de como este configurado cada proyecto en su propio `.env`.

| Variable | Descripcion |
|---|---|
| `MAPALAB_BACKEND_TARGET` | Backend de mapalab |
| `MARIACHI_BACKEND_TARGET` | Backend de mariachi |
| `GATEWAY_NGINX_TARGET` | Metricas de nginx del gateway |
| `DATAENGINE_POSTGRES_TARGET` | postgres-exporter de dataengine |
| `ACERVO_METRICS_TARGET` | Endpoint de metricas de SeaweedFS |

> En entornos uniserver dejar vacias las variables de proyectos que no esten corriendo.

---

## Backups a Acervo (S3)

Las variables conservan el prefijo `MINIO_` por compatibilidad historica con `scripts/backup.sh` (usa `mc`, cliente S3-compatible).

| Variable | Como obtenerla |
|---|---|
| `MINIO_ENDPOINT` | URL interna de Acervo (ej: `http://IP_ACERVO:8333`) |
| `MINIO_BUCKET_USER` | Access key del usuario `huachicol-user` en `acervo/config/identities.json` |
| `MINIO_BUCKET_PASSWORD` | Secret key del mismo usuario |

> Las credenciales son del usuario `huachicol-user`, con acceso limitado al bucket `huachicol`. NO usar credenciales de administrador. Para generar/rotar, editar `acervo/config/identities.json` y reiniciar `acervo-seaweedfs`.

---

## Puertos

Dejar en sus defaults a menos que haya conflicto con otros servicios en el mismo servidor:

```
GRAFANA_PORT=3000
PROMETHEUS_PORT=9090
ALERTMANAGER_PORT=9002
LOKI_PORT=9003
NODE_EXPORTER_PORT=9010
CADVISOR_PORT=9011
PROMETHEUS_AUTH_PORT=9091
LOKI_AUTH_PORT=3101
```
