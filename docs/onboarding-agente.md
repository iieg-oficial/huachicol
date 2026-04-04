# Desplegar agente de monitoreo en un servidor nuevo

Solo necesario en **produccion** donde cada servicio corre en su propio servidor.
En dev/staging todo esta en la misma maquina y no se necesitan agentes.

## Requisitos
- Docker y Docker Compose instalados en el servidor remoto
- Conectividad de red al servidor de monitoreo (puerto 9003 para Loki)

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

### 3. Iniciar
```bash
docker compose up -d
```

### 4. Registrar en huachicol

En el servidor de monitoreo, editar `.env` y poner la IP:
```bash
# Ejemplo para el servidor portal
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
- **Node exporter no responde:** verificar firewall (puerto 9100)
- **Logs no llegan a Loki:** verificar `LOKI_URL` y puerto 9003
- **cAdvisor no inicia:** requiere modo privilegiado y acceso al socket de Docker
