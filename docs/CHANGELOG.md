# Changelog

Cambios notables de `huachicol`. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[Versionado Semantico](https://semver.org/lang/es/).

Desde **2.0.0** este repo es el monitor ligero `/ontoy`. Antes fue el stack de
observabilidad (Grafana, Prometheus, Loki, Alertmanager, cAdvisor, exporters, Alloy),
retirado en 2.0.0; su historico esta en [changelog/v1.md](./changelog/v1.md).

## [2.6.0] - 2026-08-21

### Agregado: `/api/status` publica las 24 horas de cada servicio, comprimidas

`check_history` guarda un renglón por sondeo —1 440 al día por servicio— y hasta ahora solo salía de
ahí un número, `uptime_24h`, y el historial crudo del detalle por servicio. Con eso no se puede
dibujar una barra de disponibilidad: agrupar por hora en el cliente esconde las caídas cortas, que
son justo las que nadie alcanza a ver. Una caída de cuatro minutos deja su hora al 93 % y se pinta
casi entera de verde.

`Store.uptime_tramos()` arma una rejilla de una celda por sondeo sobre la ventana de 24 horas y la
comprime a tramos consecutivos del mismo estado. La jornada completa de un servicio tranquilo cabe
en un tramo; la de gateway-hub el día de la caída del ZIP, en quince. La respuesta de diez servicios
pasó de 8 a 12 KB, con resolución de minuto en lugar de ninguna.

Los huecos —el monitor apagado, un reinicio— salen como `sin_datos` y no como una caída, que es una
distinción que antes no existía. El `detalle` del primer sondeo con motivo viaja pegado al tramo, así
que el cliente puede decir por qué se cayó sin pedir el detalle del servicio.

La resolución la manda `MONITOR_POLL_INTERVAL`: si el sondeo baja a diez minutos, la rejilla tiene
144 celdas en vez de 1 440 y el payload encoge solo.

## [2.5.0] - 2026-08-03

### Corregido: los servicios retirados de `targets.json` ya no quedan de fantasma

`service_state` tiene el slug como llave primaria y nada la limpiaba: al sacar un target del JSON
su fila sobrevivía congelada en el último estado medido y `/api/status` la seguía sirviendo, porque
devuelve `all_states()` sin cruzarlo contra la configuración. Así quedó `geoserver` tras el
renombre a sextante del 31 de julio: visible en Observabilidad como `unreachable` desde las
14:42 UTC, un minuto antes de que arrancara `sextante`. `prune()` no lo alcanzaba — solo poda
`check_history` y `events` por retención, nunca `service_state`.

El monitor purga ahora al arrancar los slugs que no están en `targets.json`, con su historial y sus
eventos, y lo anuncia en el log. Un renombre de target deja la base consistente sin intervención
manual.

## [2.4.1] - 2026-07-31

### Agregado: `VERBOSE=1` en los targets que usan `run_step`

Sincronización de `make/lib.sh` y `make/common.mk` con gateway-hub 1.42.0. `run_step` esconde la
salida de cada paso y sólo la muestra —las últimas 40 líneas— si falla, así que un `docker build`
real y uno servido entero por caché se ven igual salvo por el cronómetro. Con `VERBOSE=1` la
salida se imprime en directo, indentada bajo el paso y conservando el `ok`/`fail` y el tiempo. El
comportamiento por defecto no cambia.

## [2.4.0] - 2026-07-30

### Corregido: el target de mapalab apunta al sidecar, no al backend

Desde mapalab 1.102.0 el `/ontoy` bueno es el del sidecar `version-api`, que **fusiona** los checks
del backend (`db`, `client_errors`, `embeds`) con los suyos (`disk`, `containers`) en vez de
reemplazarlos. El target seguía apuntando a `mapalab-backend-1:8000`, que da menos información y
además quedó cerrado: gateway-hub responde 403 tanto en `/api/ontoy` como en `/mapalab/api/ontoy`.

`targets.example.json` pasa a `http://mapalab-version-api:8088/ontoy`. En multi-VM el sidecar no
publica el 8088, así que ahí el target es `http://<S2>:8081/ontoy`, por el nginx de mapalab.

## [2.3.0] - 2026-07-30

### Cambiado: Makefile homologado con el resto del ecosistema

La interfaz de comandos es ahora la misma en los nueve repos: `up` levanta desarrollo sin
reconstruir y `deploy` hace produccion completa (`git pull` + `down` + `build` + `up`). Se
retiraron todas las banderas: el entorno se detecta por el nombre de proyecto de Compose y lo que
antes era un argumento ahora es un selector interactivo. Lo transversal vive en `make/common.mk` y
`make/lib.sh`, copiados en cada repo. Convencion completa en `ecosistema/makefiles.md` del repo de
contexto.

### Cambiado: `start`/`stop` pasan a ser `up`/`down`

Era la unica divergencia de nombres que quedaba en el ecosistema y la trampa mas repetida al
desplegar este repo. `up` ya no reconstruye; para eso esta `deploy`.

### Eliminado: `version-json`

El `/ontoy` lee la version de `VERSION`, ya montado en el sidecar. Se retiraron el target, el mount
de `version.json` y la carpeta `version-api/html`.

## [2.2.0] - 2026-07-30

### Agregado: `ONTOY_UPSTREAM_URL` en el sidecar de referencia

El sidecar `version-api` reporta `disk` y `containers`, que es todo lo que hace falta cuando el
servicio no tiene checks propios. Pero mapalab y mariachi sirven su `/ontoy` desde el backend con
checks de aplicacion (`db`, `client_errors`, `embeds`, `redis`), y hasta ahora ponerles un sidecar
obligaba a elegir: o el sidecar, o esos checks.

`ONTOY_UPSTREAM_URL` quita la disyuntiva. Con la variable apuntando al `/ontoy` de la aplicacion,
el sidecar lo consulta por la red interna y **fusiona** la respuesta en la suya:

| Situacion | Resultado |
|---|---|
| El backend responde | Sus `checks` se suman a los del sidecar sin pisarlos; `version`, `released_at` y `deployed_at` se toman de ahi si el sidecar no los tiene |
| El backend responde 503 | Se lee el cuerpo igual: el contrato garantiza JSON valido tambien en 503, y ahi va el diagnostico |
| El backend no responde | Check `upstream` en `down`, y el `/ontoy` del sidecar devuelve 503 |
| El backend se declara `down` sin un check que lo explique | Se agrega un check `upstream` con ese `status`, para no reportar mejor de lo que el servicio dice estar |

El `status` sigue siendo el peor de los checks, como manda el contrato. Sin la variable el
comportamiento es identico al anterior.

Esto habilita el patron para cualquier servicio con `/ontoy` propio: el sidecar queda como unica
puerta de entrada del monitor, y el handler de la aplicacion puede cerrarse al exterior sin perder
un solo check. El primero en usarlo es mapalab 1.102.0.

#### Por que sigue valiendo la pena el sidecar

El socket de Docker equivale a root en el host, y montarlo en el contenedor que recibe trafico
publico convierte cualquier fallo de la app en control del servidor. El sidecar no acepta entrada
de usuario: su unica ruta es `/ontoy` y no lee parametros.

---

## [2.1.2] - 2026-07-30

### La plantilla de targets ahora explica el caso multi-VM

`targets.example.json` estaba escrito solo para el caso monolito, con nombres de contenedor en
todas las entradas. Eso funciona cuando el monitor comparte host con lo que vigila, pero **en
produccion cada servicio vive en su propia VM y `iieg-network` no cruza de nodo**: el DNS de docker
no resuelve nombres remotos y el servicio queda `unreachable` sin que nada este roto.

Detectado en produccion el 2026-07-30: GeoServer llevaba dias caido en el panel y **MapaLab ni
siquiera figuraba** en la lista de targets.

#### Cambiado

- Las entradas de `geoserver`, `dataengine` y `mapalab` llevan un `comment` con la URL que
  corresponde cuando el servicio vive en otra VM, y con lo que hace falta de cada lado.

#### La regla

- Servicio en el **mismo host** que el monitor: nombre de contenedor.
- Servicio en **otra VM**: **IP y puerto publicado al host**. Si el container no declara `ports:`,
  no es alcanzable aunque este en `iieg-network`.
- Comprobar antes de dar algo por caido:
  `timeout 3 bash -c 'echo > /dev/tcp/<ip>/<puerto>'`. **Refused** = falta publicar el puerto;
  **timeout** = lo bloquea el firewall. La diferencia decide entre un cambio de una linea y una
  solicitud de apertura.
- Si el nginx de un servicio bloquea `/ontoy` para cerrarlo a internet, verificar que el monitor
  siga entrando: entre VMs **si** pasa por ese nginx, a diferencia del monolito.

---

## [2.1.1] - 2026-07-29

### El README describia el stack retirado y los docs 1.x se archivaron

Solo documentacion; sin cambios en el monitor.

#### Cambiado

- **README reescrito.** Se titulaba «IIEG Monitoring Stack», listaba los ocho servicios retirados
  en 2.0.0 con sus puertos y documentaba targets del Makefile que ya no existen (`make targets`,
  `make backup`, `make agent-start`, `make backup-cron-install`). Ahora describe los dos servicios
  reales, las trece variables del `.env`, `monitor/targets.json` con su gotcha de recrear el
  contenedor, y la ventana de despliegue.
- `docs/CHANGELOG-1.x.md` → `docs/changelog/v1.md`, siguiendo el patron de acervo (un archivo por
  major bajo `docs/changelog/`).

#### Eliminado

- `docs/alert-rules.md`, `discord-alerts.md`, `configuracion-env.md` y `agregar-proyecto.md`:
  describian el stack Prometheus/Grafana/Alertmanager/Loki retirado el 2026-07-21, con requisitos
  (`/metrics`) y scripts que ya no existen. Quedaron condensados en
  `historial/2026-07-huachicol-stack-observabilidad-1x.md` del repositorio central de contexto,
  con los umbrales de las siete alertas, el enrutamiento y sus limites conocidos — util para un
  rollback al tag `v1.23.0`.
- `docs/context.md`, `onboarding-agente.md`, `ontoy-contrato.md` y `docs/pendientes/`: viven ahora
  en `repos/huachicol/` del repo central.

## [2.1.0] - 2026-07-29

### Cambiado: las alertas dicen que check esta degradado, no solo cual fallo

El monitor ya trataba `degraded` como estado no sano —tras `MONITOR_FAILURE_THRESHOLD`
sondeos alerta igual que con `down`—, pero el detalle del mensaje solo enumeraba los checks
en `down` o `unreachable`. Un servicio que se reportaba degradado producia una alerta sin
explicacion: "MapaLab: degradado" y nada mas.

Ahora el detalle distingue ambos grupos y arrastra el `detail` que cada check trae en su
`/ontoy`:

```
checks en fallo: db (connection refused) | checks degradados: client_errors (6 errores de
carga en el navegador en 15 min (predomina chunk_load_error))
```

El cambio habilita el patron de reportar sintomas de usuario como checks degradados: mapalab
1.97.0 expone `client_errors` con la cuenta de fallos de carga que reportan los navegadores,
que era justo lo que dejo de verse al retirar Prometheus y Alertmanager en 2.0.0. No requiere
cambios en `targets.json` ni en la configuracion de los servicios monitoreados.

## [2.0.0] - 2026-07-21

### Apagado del stack de observabilidad: el repo queda como monitor ligero

Fin de la migracion planificada en `docs/pendientes/migracion-monitor.md`. Se retira el stack
pesado; el monitor `/ontoy` v2 y su dashboard en Mariachi cubren estado, alertas (Discord) y
disponibilidad. El repo pasa a contener solo `version-api` (sidecar `/ontoy`) y `monitor`.

#### Eliminado

- Servicios del `docker-compose.yml`: `prometheus`, `grafana`, `alertmanager`,
  `alertmanager-discord`, `loki`, `alloy`, `node-exporter`, `cadvisor`, `nginx-auth`, con sus
  volumenes, la red `monitoring` y los puertos 9090/3000/9093/3100/9100/9091/3101.
- Configuracion del stack: `prometheus/`, `grafana/`, `loki/`, `alertmanager/`, `agent/` y
  `nginx-auth/`; los scripts de `scripts/` (backup, restore, generate-targets, etc.) y los
  targets del `Makefile` asociados; los jobs de CI de prometheus/alertmanager/loki/agente.
- Variables del stack en `.env.example`.

#### Cambiado

- `version-api` y `monitor` declaran rotacion local de logs (`json-file`, `max-size` 10m,
  `max-file` 3): unica retencion tras retirar Loki.
- `gateway-hub`: se quitan las locations `/huachicol/` y `/huachicol/public/` (proxy a
  Grafana) y su zona `limit_req`. Se conserva `/huachicol/ontoy`.

#### Datos

- Descartados los volumenes del TSDB de Prometheus, dashboards de Grafana e indice de Loki.
  Sin archivado: no se usaban.

#### Por que major

Cambio incompatible de proposito: el repo deja de desplegar el stack de observabilidad. El
punto de retorno con el stack completo es el tag `v1.23.0`.

### Ventana de despliegue en el monitor

Durante un despliegue los servicios caen y suben; para no spamear alertas, el monitor gana
endpoints `POST /api/deploy/start` y `POST /api/deploy/end`. Entre ambos **suprime** las
alertas individuales de caida/recuperacion (los eventos se registran igual, `notified=0`) y
solo envia un mensaje al iniciar y otro al finalizar (con resumen `N/total ok`). La ventana
expira sola tras `MONITOR_DEPLOY_TIMEOUT` segundos (900 por defecto) si no llega el `end`. El
`make deploy` de cada repo envuelve el deploy con esas llamadas (patron en `monitor/README.md`).
