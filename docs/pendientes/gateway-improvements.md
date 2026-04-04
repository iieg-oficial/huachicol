# Pendiente: Mejoras al Gateway-Hub

Estas mejoras aplican al proyecto `/home/egar/IIEG/gateway-hub`, no a huachicol.

## 1. Rate limiting diferenciado
El gateway usa 3 rate limiters identicos (10 req/s, burst 20). Recomendacion:
- **General (/):** 20 req/s, burst 40 — trafico web normal
- **API (/api/):** 30 req/s, burst 50 — clientes programaticos necesitan mas
- **GeoServer OWS/WFS/WCS:** 5 req/s, burst 10 — queries pesadas a la DB, proteger recursos
- **GeoServer descargas:** 2 req/s, burst 5 — archivos grandes

Archivo a modificar: `nginx/nginx.conf` (limit_req_zone) y `nginx/templates/gateway.conf.template` (limit_req por location).

## 2. Log rotation para NGINX
Los logs de NGINX van a un volumen Docker sin rotacion. Opciones:
- **Opcion A (recomendada):** Agregar `logging.driver: json-file` con `max-size: 50m` y `max-file: 5` en docker-compose.yml del gateway
- **Opcion B:** Montar logrotate dentro del contenedor con un cron sidecar
- **Opcion C:** Confiar en Promtail para leer los logs y no persistirlos largo tiempo en el volumen

Archivo a modificar: `docker-compose.yml` del gateway-hub.

## 3. Promtail deprecado
Promtail esta en EOL (marzo 2026). Grafana recomienda migrar a Grafana Alloy.
Aplica tanto al gateway como a los agentes de huachicol.
Evaluar migracion cuando se haga un upgrade mayor del stack.
