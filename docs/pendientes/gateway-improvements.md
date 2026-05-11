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

## 3. Promtail deprecado — migracion a Grafana Alloy
Promtail entro en EOL en marzo 2026. La migracion a Grafana Alloy aplica tanto al gateway como a los agentes de huachicol.

- **Huachicol (agentes):** plan detallado en `docs/pendientes/alloy-migration.md` (fases 2 y 3 documentadas; fase 1 en ejecucion / changelog).
- **Gateway-hub:** pendiente migrar el Promtail del gateway de forma equivalente. Verificar version estable mas reciente de Alloy antes de planear (al 2026-05-11: `v1.16.1`).
