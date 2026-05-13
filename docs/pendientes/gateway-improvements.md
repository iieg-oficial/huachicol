# Pendiente: Mejoras al Gateway-Hub

Estas mejoras aplican al proyecto `/home/egar/IIEG/gateway-hub`, no a huachicol.

## 1. Rate limiting diferenciado — IMPLEMENTADO (2026-04-14)
El gateway ahora usa 4 zonas diferenciadas:
- **General (/):** 10 req/s, burst 20 — trafico web general
- **API (/api/):** 10 req/s, burst 20 — endpoints de API
- **Static (/mapalab/assets/):** 50 req/s, burst 200 — assets de SPA con cache gateway
- **MapaLab (/):** 10 req/s, burst 150 — navegacion SPA
- **GeoServer OWS/WFS/WCS:** 10 req/s, burst 10 — servicios OGC con cache
- Respuesta al exceso: HTTP 429 con pagina amigable (countdown 10s)
- Cache de assets MapaLab en gateway (500MB, 7 dias, stale serving)
- Stress test validado: 100 usuarios simultaneos, 0% errores, p95 92ms

Ver `gateway-hub/docs/rendimiento.md` para configuracion completa y resultados.

## 2. Log rotation para NGINX
Los logs de NGINX van a un volumen Docker sin rotacion. Opciones:
- **Opcion A (recomendada):** Agregar `logging.driver: json-file` con `max-size: 50m` y `max-file: 5` en docker-compose.yml del gateway
- **Opcion B:** Montar logrotate dentro del contenedor con un cron sidecar
- **Opcion C:** Confiar en Promtail para leer los logs y no persistirlos largo tiempo en el volumen

Archivo a modificar: `docker-compose.yml` del gateway-hub.

## 3. Rate limit muy estricto para /huachicol/ (Grafana 429)
Bloque actual en `gateway-hub/nginx/templates/gateway.conf.template:276-281`:
```nginx
location ^~ /huachicol/ {
    limit_req zone=general burst=20 nodelay;
    proxy_pass http://huachicol;
    ...
}
```
La zona `general` da `rate=10r/s, burst=20`. Es muy poco para Grafana, que en la carga inicial de un dashboard hace 50+ requests en paralelo (assets JS/CSS/fonts hasheados, plugin settings, datasource queries, variable resolution, avatar, WS live). El navegador recibe 429 y el dashboard ni siquiera carga el bundle principal (errores `Loading chunk X failed`).

**Mitigaciones aplicadas en huachicol (parciales, reducen carga del backend pero no eliminan el 429):**
- `GF_PLUGINS_DISABLE_PLUGINS` para los 4 plugins de drilldown que Grafana 12 precarga (`grafana-exploretraces-app`, `grafana-lokiexplore-app`, `grafana-metricsdrilldown-app`, `grafana-pyroscope-app`).
- `GF_FEATURE_TOGGLES_DISABLE=preinstallAutoUpdate,dashgpt`.
- Dashboard `containers.json` con `refresh: 1m`, `topk(20, ...)` y `maxLines: 100`.

**Fix recomendado en gateway-hub:**
- Zona dedicada `huachicol` con `rate=30r/s, burst=200, nodelay` (o similar).
- Idealmente, exentar `^/huachicol/public/` (assets estaticos con hash inmutables) del rate limit y agregar `proxy_cache` con TTL largo.

Ejemplo:
```nginx
limit_req_zone $binary_remote_addr zone=huachicol:10m rate=30r/s;

location ^~ /huachicol/public/ {
    proxy_pass http://huachicol;
    include /etc/nginx/includes/proxy-params.inc;
    proxy_cache static_cache;
    proxy_cache_valid 200 7d;
    add_header Cache-Control "public, immutable, max-age=604800";
}

location ^~ /huachicol/ {
    limit_req zone=huachicol burst=200 nodelay;
    proxy_pass http://huachicol;
    include /etc/nginx/includes/proxy-params.inc;
    proxy_set_header Accept-Encoding "";
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
}
```
Aplica al repo `gateway-hub`, no a huachicol.

## 4. nginx-exporter solo expone stub_status
El `nginx-exporter` del gateway hoy es del tipo basico (lee `/stub_status`). Solo expone:
- `nginx_http_requests_total` (contador acumulado, sin labels)
- `nginx_connections_{active,reading,writing,waiting,accepted,handled}`
- `nginx_up`

No hay desglose por status code, URI, upstream ni latencia, lo que limita el dashboard `Contenedores - Vista Detallada` (panels de trafico HTTP solo muestran totales y estados de conexion).

**Opciones para drill-down:**
- **A.** Migrar a `nginx-prometheus-exporter` con modulo `vts` parcheado en NGINX (`nginx_vts_*` series con labels por server/upstream/status).
- **B.** Aprovechar el `json_logs` ya configurado en `/IIEG/gateway-hub/nginx/nginx.conf` y consultarlo desde Loki/LogQL para construir paneles por URI y status. Requiere confirmar que Promtail (o futuro Alloy) este enviando los access logs del gateway a Loki.
- **C.** Combinar B con `loki.process` + `stage.metrics` para exponer las series como Prometheus desde Alloy (cardinality controlada).

Opcion B es la mas barata; A da metricas mas confiables.

## 5. Promtail deprecado — migracion a Grafana Alloy
Promtail entro en EOL en marzo 2026. La migracion a Grafana Alloy aplica tanto al gateway como a los agentes de huachicol.

- **Huachicol (agentes):** plan detallado en `docs/pendientes/alloy-migration.md` (fases 2 y 3 documentadas; fase 1 en ejecucion / changelog).
- **Gateway-hub:** pendiente migrar el Promtail del gateway de forma equivalente. Verificar version estable mas reciente de Alloy antes de planear (al 2026-05-11: `v1.16.1`).
