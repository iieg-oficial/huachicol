# Changelog

Cambios notables de `huachicol`. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y
[Versionado Semantico](https://semver.org/lang/es/).

Desde **2.0.0** este repo es el monitor ligero `/ontoy`. Antes fue el stack de
observabilidad (Grafana, Prometheus, Loki, Alertmanager, cAdvisor, exporters, Alloy),
retirado en 2.0.0; su historico esta en [changelog/v1.md](./changelog/v1.md).

## [2.15.1] - 2026-08-28

### Agregado: la memoria dice cuanto es cache

`memory_used_gb` sale de `MemTotal - MemAvailable`, que es lo correcto —el page cache se libera en
cuanto una aplicacion lo pide, asi que no es memoria gastada— pero al no publicar el cache no habia
como cuadrar la cifra contra `top`, donde el mismo equipo se lee «1.9 libre, 11 en buff/cache».

Se agregan `memory_cache_gb` (Cached + Buffers) y `memory_free_gb`. La suma de usado, cache y libre no
da el total: el resto es slab no reclamable, que es justo lo que `MemAvailable` ya descuenta y una
resta a mano regalaria.

## [2.15.0] - 2026-08-28

### Agregado: historial de las metricas de maquina

`check_history` guardaba estado y latencia, nada del host: una temperatura suelta no dice si 78 grados
son normales en esa maquina o si lleva tres dias subiendo. La tabla nueva `host_history` guarda la
lectura completa del reportero de cada nodo, y `GET /api/nodos/{nodo}/historial` la devuelve.

**Se muestrea cada cinco minutos, no cada sondeo.** Con cinco nodos son 1 440 filas al dia; a
resolucion de minuto serian 7 200 para una curva que se ve igual, porque la temperatura no cambia de
forma interesante en sesenta segundos. El intervalo es `MONITOR_HOST_SAMPLE_INTERVAL`.

La poda existente se encarga de la tabla nueva con la misma retencion, asi que no hay un segundo
reloj que vigilar.

Sirve para la temperatura, que es lo que lo motivo, pero guarda todo el bloque `host`: carga, memoria
y swap quedan disponibles para graficarse sin volver a tocar el monitor.

## [2.14.0] - 2026-08-28

### Cambiado: la temperatura pasa de un numero a una lista de sensores

2.13.0 reportaba una sola cifra, la zona mas caliente, sin decir de que. Ahora se lee `/sys/class/hwmon`
—la fuente estandar— y se traduce a nombres que significan algo: **CPU** (`coretemp`, `k10temp`),
**Sistema** (`acpitz`), **Disco** (`nvme`) y **Graficos** (`amdgpu`, `nouveau`, `i915`).

De cada chip se toma la lectura del paquete cuando la declara (`Package id 0`, `Composite`, `Tctl`) y
si no, la mas alta de sus sensores: en un CPU de veinte nucleos interesa el paquete, no los trece
valores por nucleo. Las lecturas fuera de rango o en cero se descartan, que es lo que reportan los
sensores de wifi apagados.

`thermal_zone` queda como respaldo para equipos sin hwmon, y `cpu_celsius` se conserva. El check sigue
siendo informativo y usa el sensor mas caliente.

## [2.13.0] - 2026-08-28

### Agregado: la temperatura del CPU, cuando el equipo la expone

Sale de `/sys/class/thermal`, que el contenedor ya ve sin montar nada, y se toma la zona mas caliente
de las que reporten un valor creible. **En una VM normalmente no hay ninguna**, asi que el campo
simplemente no aparece: es un dato de hierro, y en produccion solo lo daran los nodos que corran
sobre metal.

Va como check informativo, con umbrales en `ONTOY_TEMP_WARN` y `ONTOY_TEMP_CRITICAL` (70 y 85 grados
por omision), asi que un equipo caliente se ve pero no marca al servicio como caido.

## [2.12.0] - 2026-08-28

### Agregado: el nodo reporta su sistema y sus puertos

`/proc/version` da el kernel sin montar nada, porque no esta aislado por namespace. El nombre del
sistema si exige montar `/etc/os-release` del anfitrion, que es un volumen de solo lectura mas. La IP
va por `ONTOY_NODE_IP` y no se mide: es un valor sensible que no se versiona, asi que vive en el
`.env` de cada nodo.

`/api/nodos` lista ademas **los puertos** que el nodo vigila, con cual responde y cual no, sacados de
los checks que ya traian `port`. Antes ese dato solo se veia como un check suelto por servicio.

### Corregido: un vecino que no resuelve dejaba el `/ontoy` fuera de tiempo

Al estrenar `ONTOY_PEER_CHECKS` con destinos que no resolvian, el endpoint pasaba de 40 ms a **5
segundos** y el monitor lo marcaba `timed out`: mapalab y sextante aparecieron caidos sin estarlo.

El timeout de las aristas baja a 0.8 s y se separa del de dependencias (`ONTOY_PEER_TIMEOUT`). Ojo
con la causa real: `socket.create_connection` acota la conexion pero **no la resolucion de nombres**,
asi que un vecino mal escrito sigue costando lo que tarde el DNS en rendirse. La arista se apunta a
un destino que el contenedor resuelva de verdad.

## [2.11.0] - 2026-08-27

### Agregado: `/api/nodos` entrega el detalle completo de cada servidor

La agrupacion por nodo recortaba los campos de cada servicio a cuatro, asi que el detalle de un nodo
no podia reusar la fila del tablero de servicios y terminaba siendo una lista pobre. Ahora cada
servicio del nodo viaja con su motivo de fallo, su desde-cuando, sus tramos de 24 horas y su resumen
de contenedores: lo mismo que `/api/status`, con lo que el frontend pinta la misma fila en los dos
lados.

Se agregan ademas dos cosas que faltaban en el nodo: **el disco** —`disk_used_percent` y
`disk_free_gb` del reportero, que estaban medidos desde siempre en el check `disk` y nadie subia al
bloque de host— y **la lista de contenedores** de todos los servicios del nodo, no solo el conteo.

El disco se toma unicamente del reportero: el de un servicio que comparte maquina diria lo mismo y
el de uno que no la comparte mentiria.

## [2.10.0] - 2026-08-27

### Agregado: el propio `version-api` de huachicol declara su nodo

Cierra la propagacion del contrato: los siete `ontoy_server.py` del ecosistema quedan identicos y
cada uno declara su nodo. huachicol es el **reportero de S1**, donde tambien viven gateway-hub,
acervo y mariachi: los tres van en `ONTOY_NODE_REPORTER=false` y la maquina se mide una sola vez.

Con eso `/api/nodos` agrupa de verdad: S1 con sus cuatro repos y once contenedores, S2 con mapalab,
S3 con sextante, S4 con dataengine y S5 con el portalito.

## [2.9.0] - 2026-08-27

### Agregado: el `/ontoy` habla de la maquina, no solo del servicio

Faltaban los cinco datos que hacen posible una vista por servidor. Ninguno pide un exporter: el
sidecar ya corre en cada nodo y solo lee archivos de texto de `/proc`.

- **`ONTOY_NODE`** etiqueta a que nodo pertenece cada servicio, que es lo que permite agrupar. El
  mapeo repo → nodo vivia en `ecosistema/topologia.md`, escrito a mano; ahora viaja en los datos.
- **`ONTOY_NODE_REPORTER`** designa un solo sidecar por nodo para hablar del host. En S1 corren
  cuatro repos y sin esto se reportaria cuatro veces la misma maquina.
- **Carga** de `/proc/loadavg`, dividida entre los nucleos: es lo unico que hace comparable a S4,
  de cuatro nucleos, con S1, de ocho.
- **RAM y swap** de `/proc/meminfo`, con `MemAvailable` y no `MemFree`, porque el cache no es
  memoria perdida.
- **Uptime** de `/proc/uptime`, para distinguir un servicio reiniciado de una maquina reiniciada.
- **`ONTOY_PEER_CHECKS`**: una arista por vecino con su latencia, que es la conectividad entre
  nodos que hasta hoy solo se probaba a mano al levantar una VM.

### Agregado: `/api/nodos` agrupa los servicios por servidor

Un servicio por nodo con su estado, sus contenedores sumados, las metricas del reportero y las
aristas hacia sus vecinos, mas las transiciones recientes. `service_state` gana `node` y `host` con
un `ALTER TABLE` idempotente, asi que la base existente no se toca.

### Corregido: un host sudando ya no tumba al servicio

`carga`, `memoria`, `swap` y las aristas quedan marcados `"informativo": true` y **no entran al
estado global**. El estado sigue siendo un Y logico, pero solo de los checks criticos.

Es el pendiente que dejo el ensayo de tamal-verde, donde un ZIP que no descargaba marco como caido
al punto de entrada del ecosistema. Salio a la luz al probar esto: el swap de la maquina de
desarrollo, al 71 %, dejaba a mariachi en `degraded` sin que nada le pasara.

## [2.8.0] - 2026-08-27

### Agregado: el sidecar tambien enriquece a quien ya expone `/ontoy`

mariachi sirve su `/ontoy` desde la propia API, con checks de aplicacion —`db`, `redis`, `abuso`,
`mapalab_notify`— pero **cero contenedores**: un proceso de FastAPI no ve el socket de Docker y
nunca los reporto. El campo estaba vacio desde que existe el contrato v2.

`compose.ontoy.yaml` gana `ONTOY_UPSTREAM_URL`. Con ella el sidecar consulta el `/ontoy` del propio
servicio, se queda con sus checks y les agrega los suyos: disco, puertos y los contenedores del
proyecto. mariachi pasa de cuatro checks a siete y de cero contenedores a cinco, sin tocar una linea
de su API.

El target de mariachi apunta ahora al sidecar y no a `mariachi-api:8000`. Es el mismo endpoint con
mas datos: quien consulte directo a la API sigue recibiendo lo de siempre.

## [2.7.0] - 2026-08-26

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

## [2.6.0] - 2026-08-26

### Agregado: un `/ontoy` de encargo para servicios que no lo exponen

El portalito ocupa `location /` del gateway y **no reporta `/ontoy`**, así que era el único servicio
del ecosistema que nadie vigilaba. Su repo tiene convenciones propias y no se le meten las nuestras,
que es justo lo que exigiría agregarle un `version-api` a su compose.

`compose.ontoy.yaml` levanta el mismo `version-api` de este repo como **stack aparte**, en el host
del servicio vigilado y sin tocar su repositorio. Todo lo que lo distingue sale del `.env`:
`ONTOY_COMPOSE_PROJECT` filtra los contenedores por el label `com.docker.compose.project`,
`ONTOY_PORT_CHECKS` vigila sus upstreams y `ONTOY_NETWORK` lo mete a la red del stack observado para
poder alcanzarlos. Con el portalito quedan sus siete contenedores, `portal-nginx:80` y
`portal-api:8000`.

### Agregado: la versión puede salir del `pyproject.toml` o del `package.json`

`version-api` solo sabía leer un archivo `VERSION`, que es una convención nuestra y no de todos.
Ahora `ONTOY_VERSION_FILE` acepta también `pyproject.toml` y `package.json`, y los parsea según su
nombre —de ahí que el volumen deba conservarlo—, así que un repo ajeno reporta su versión sin
agregarle un archivo.

`ONTOY_CHANGELOG_FILE` completa `released_at`, que el contrato v2 define desde el principio y hasta
hoy nadie llenaba: sale de la primera entrada `## [x.y.z] - YYYY-MM-DD` del CHANGELOG.

Con el portalito eso deja a la vista un desfase suyo: su `pyproject.toml` declara **1.8.0** y su
CHANGELOG va en **1.9.1**, del 5 de agosto. El endpoint reporta lo que el repo dice, no lo que
debería decir; corregirlo es un issue en su repositorio.
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
