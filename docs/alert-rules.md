# Reglas de Alerta

## service_alerts

### ServiceDown
- **Severidad:** critical
- **Condicion:** `up == 0`
- **Espera:** 1 minuto
- **Que significa:** Un target de Prometheus dejo de responder. Aplica a todos los jobs: prometheus, grafana, loki, mapalab-backend, mariachi-backend, gateway-nginx, dataengine-postgres, acervo-seaweedfs, node-exporter, cadvisor.
- **Accion:** Verificar que el servicio este corriendo (`docker ps`) y que el puerto sea accesible.

### HighLatency
- **Severidad:** warning
- **Condicion:** Latencia promedio de requests HTTP > 1 segundo durante 5 minutos
- **Espera:** 5 minutos
- **Que significa:** El servicio esta respondiendo lento. Puede ser carga alta, queries lentos o recursos insuficientes.
- **Requiere:** Que el servicio exponga la metrica `http_request_duration_seconds` (histogram).
- **Servicios que aplican:** ninguno actualmente. mapalab-backend y mariachi-backend exponen `/metrics` con counters de negocio (`mapalab_*_total`, `mariachi_*_total`) pero no `http_request_duration_seconds`/`http_requests_total`. Para activar esta alerta hay que instrumentar middlewares HTTP en sus apps FastAPI.

### HighErrorRate
- **Severidad:** critical
- **Condicion:** Mas del 5% de requests HTTP responden con 5xx durante 2 minutos
- **Espera:** 2 minutos
- **Que significa:** El servicio esta fallando frecuentemente. Revisar logs del servicio afectado.
- **Requiere:** Que el servicio exponga `http_requests_total` con label `status_code`.
- **Servicios que aplican:** ninguno actualmente. mapalab-backend y mariachi-backend exponen `/metrics` con counters de negocio (`mapalab_*_total`, `mariachi_*_total`) pero no `http_request_duration_seconds`/`http_requests_total`. Para activar esta alerta hay que instrumentar middlewares HTTP en sus apps FastAPI.

### HighMemoryUsage
- **Severidad:** warning
- **Condicion:** Uso de memoria del servidor > 90%
- **Espera:** 5 minutos
- **Que significa:** El servidor se esta quedando sin memoria. Puede causar que el OOM killer mate procesos.
- **Requiere:** node-exporter activo.
- **Accion:** Identificar procesos con alto consumo (`top`, `htop`). Considerar reiniciar servicios o escalar.

### DiskSpaceLow
- **Severidad:** warning
- **Condicion:** Espacio disponible en `/` es menor al 10%
- **Espera:** 5 minutos
- **Que significa:** El disco se esta llenando. Puede causar que servicios dejen de escribir logs o datos.
- **Requiere:** node-exporter activo.
- **Accion:** Limpiar logs antiguos, imagenes Docker sin usar (`docker system prune`), datos temporales.

## database_alerts

### PostgreSQLDown
- **Severidad:** critical
- **Condicion:** `pg_up == 0`
- **Espera:** 1 minuto
- **Que significa:** PostgreSQL no responde. Todas las aplicaciones que dependen de la BD estan afectadas.
- **Requiere:** postgres-exporter activo (target `dataengine-postgres`).
- **Accion:** Verificar estado del contenedor de PostgreSQL y sus logs.

### TooManyConnections
- **Severidad:** warning
- **Condicion:** Conexiones activas > 80% del maximo configurado
- **Espera:** 5 minutos
- **Que significa:** La BD se esta quedando sin conexiones disponibles. Nuevas conexiones seran rechazadas al llegar al 100%.
- **Requiere:** postgres-exporter activo.
- **Accion:** Identificar conexiones idle (`pg_stat_activity`), revisar connection pools de las aplicaciones.

## Targets monitoreados

| Job | Target | Proyecto |
|-----|--------|----------|
| prometheus | localhost:9090 | - |
| grafana | grafana:3000 | - |
| loki | loki:3100 | - |
| mapalab-backend | mapalab-backend:8000 | mapalab (si expone /metrics) |
| mariachi-backend | mariachi-api:8000 | mariachi (si expone /metrics) |
| gateway-nginx | nginx-exporter:9113 | gateway-hub |
| dataengine-postgres | desde DATAENGINE_POSTGRES_TARGET | dataengine |
| acervo-seaweedfs | desde ACERVO_METRICS_TARGET | acervo |
| node-exporter | file_sd (targets/node-exporter.json) | infra |
| cadvisor | file_sd (targets/cadvisor.json) | infra |
