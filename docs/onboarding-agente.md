# Desplegar agente de monitoreo en un servidor nuevo

Solo necesario en **produccion** donde cada servicio corre en su propio servidor.
En dev/staging todo esta en la misma maquina y no se necesitan agentes.

## Requisitos
- Docker y Docker Compose instalados en el servidor remoto
- Conectividad de red:
  - Salida: al servidor de monitoring (puerto 9003 para Loki push)
  - Entrada: que `monitoring` pueda alcanzar `:12345` (Alloy) y `:8080` (cAdvisor) en el server remoto. Solicitar apertura de puertos al equipo de administracion GCP.

## Pasos

### 1. Copiar la carpeta agent/ al servidor
```bash
scp -r agent/ usuario@servidor:/opt/monitoring-agent/
```

### 2. Configurar .env
```bash
cd /opt/monitoring-agent
cp .env.example .env
nano .env
```

Valores:
- `SERVER_NAME` — identificador del servidor (`portal`, `mapalab`, `mariachi`, `geoserver`)
- `LOKI_URL` — URL del Loki central (`http://<MONITORING_SERVER_IP>:9003`)
- `ALLOY_PORT` — puerto del HTTP server de Alloy (default `12345`)
- `CADVISOR_PORT` — puerto de cAdvisor (default `8080`)
- `POSTGRES_DSN` y `POSTGRES_EXPORTER_PORT` — solo si el server corre PostgreSQL

### 3. Iniciar
```bash
docker compose --profile all up -d
```

Si el server tiene PostgreSQL, agregar el profile `postgres`:
```bash
docker compose --profile all --profile postgres up -d
```

### 4. Registrar en huachicol

En el servidor de monitoring, editar `.env` y poner la IP:
```bash
PORTAL_SERVER_IP=10.x.x.x
```

Regenerar targets:
```bash
make targets
```

Prometheus detecta el nuevo servidor en ~30s.

### 5. Verificar en Grafana
Dashboard "IIEG - Vista General" > el servidor aparece en CPU, Memoria y Disco.

## Troubleshooting
- **Alloy no responde en :12345:** verificar firewall y que el container este corriendo (`docker ps | grep huachicol-alloy`).
- **Metricas de host no aparecen en Prometheus:** ver que `__metrics_path__` apunte a `/api/v0/component/prometheus.exporter.unix.host/metrics` en el JSON generado.
- **Logs no llegan a Loki:** verificar `LOKI_URL` y conectividad al puerto 9003. Revisar `docker logs huachicol-alloy`.
- **cAdvisor no inicia:** requiere modo privilegiado y acceso al socket de Docker.
