# Pendiente: Migrar autenticacion a Authentik

## Estado actual
Prometheus y Loki estan protegidos con basic auth via un sidecar nginx (`nginx-auth`).
Es una solucion temporal. No tiene SSO, MFA, ni gestion centralizada de usuarios.

## Objetivo
Reemplazar basic auth por Authentik como IdP centralizado para todos los servicios del IIEG.

## Servicios a proteger con Authentik
- Prometheus (puerto 9090) — metricas
- Loki (puerto 3100) — logs
- Grafana (puerto 3000) — ya tiene auth propia, integrar con Authentik via OIDC
- Alertmanager (puerto 9093) — gestion de alertas
- Cualquier servicio futuro del IIEG

## Que es Authentik
Identity Provider (IdP) open-source que soporta:
- OIDC/OAuth2, SAML, LDAP
- MFA (TOTP, WebAuthn)
- SSO para multiples aplicaciones
- UI de administracion
- Flows personalizables

## Arquitectura propuesta
```
[Usuario] -> [Authentik] -> [Proxy outpost] -> [Prometheus/Loki/etc]
```
Authentik actua como forward-auth provider. Cada servicio se protege con un proxy outpost que valida tokens.

## Servicios Docker requeridos
- `authentik-server` (imagen: ghcr.io/goauthentik/server)
- `authentik-worker` (imagen: ghcr.io/goauthentik/server, command: worker)
- `authentik-db` (PostgreSQL)
- `authentik-redis` (Redis)

Requiere ~1.5GB RAM adicional.

## Pasos de implementacion
1. Agregar los 4 servicios al docker-compose.yml (o compose separado)
2. Configurar Authentik: crear aplicacion, provider OIDC para cada servicio
3. Crear proxy outpost en Authentik para Prometheus y Loki
4. Configurar Grafana para usar Authentik como proveedor OIDC
5. **Eliminar el servicio `nginx-auth`** y las variables `MONITORING_AUTH_USER`, `MONITORING_AUTH_PASSWORD`
6. Eliminar archivos `nginx-auth/nginx.conf` y `nginx-auth/entrypoint.sh`
7. Actualizar .env.example con variables de Authentik (secret key, postgres, redis)

## Variables de entorno necesarias
```
AUTHENTIK_SECRET_KEY=
AUTHENTIK_DB_PASSWORD=
AUTHENTIK_BOOTSTRAP_PASSWORD=
AUTHENTIK_BOOTSTRAP_EMAIL=
```

## Que quitar cuando se implemente
- Servicio `nginx-auth` de docker-compose.yml
- Directorio `nginx-auth/`
- Variables `MONITORING_AUTH_USER` y `MONITORING_AUTH_PASSWORD` de .env
- Puertos `PROMETHEUS_AUTH_PORT` y `LOKI_AUTH_PORT` de .env
