import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.alerting import humanize_duration
from app.config import Config
from app.notifiers import Notifier
from app.store import Store

SERVICE_VERSION = "1.0.0"


def _state_to_public(
    state: dict[str, Any], store: Store, resolucion_seg: int = 60
) -> dict[str, Any]:
    return {
        "slug": state["slug"],
        "label": state["label"],
        "status": state["status"],
        "healthy": state["status"] == "ok",
        "version": state["version"],
        "deployed_at": state["deployed_at"],
        "detail": state["detail"],
        "since": state["since"],
        "since_human": humanize_duration(state["since"]),
        "last_checked": state["last_checked"],
        "latency_ms": state["latency_ms"],
        "checks": state["checks"],
        "containers": state["containers"],
        "container_summary": {
            "total": len(state["containers"]),
            "running": sum(
                1 for c in state["containers"] if c.get("state") == "running"
            ),
            "unhealthy": sum(
                1 for c in state["containers"] if c.get("health") == "unhealthy"
            ),
        },
        "node": state.get("node"),
        "host": state.get("host") or {},
        "uptime_24h": store.uptime_percent(state["slug"], hours=24),
        "uptime_tramos": store.uptime_tramos(
            state["slug"], hours=24, resolucion_seg=resolucion_seg
        ),
        "alerted": state["alerted"],
    }


def _agrupar_por_nodo(servicios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodos: dict[str, dict[str, Any]] = {}
    for servicio in servicios:
        clave = servicio.get("node") or "sin-nodo"
        nodo = nodos.setdefault(clave, {
            "node": clave,
            "servicios": [],
            "host": {},
            "peers": {},
            "containers": {"total": 0, "running": 0},
            "contenedores": [],
            "puertos": [],
        })
        nodo["servicios"].append({
            "slug": servicio["slug"],
            "label": servicio["label"],
            "status": servicio["status"],
            "version": servicio["version"],
            "detail": servicio.get("detail"),
            "since_human": servicio.get("since_human"),
            "uptime_24h": servicio["uptime_24h"],
            "uptime_tramos": servicio.get("uptime_tramos"),
            "container_summary": servicio.get("container_summary"),
        })

        checks = servicio.get("checks") or {}
        if servicio.get("host"):
            nodo["host"] = dict(servicio["host"])
            disco = checks.get("disk")
            if isinstance(disco, dict):
                nodo["host"]["disk_used_percent"] = disco.get("used_percent")
                nodo["host"]["disk_free_gb"] = disco.get("free_gb")

        resumen = servicio.get("container_summary") or {}
        nodo["containers"]["total"] += resumen.get("total", 0)
        nodo["containers"]["running"] += resumen.get("running", 0)
        nodo["contenedores"].extend(servicio.get("containers") or [])

        for nombre, check in checks.items():
            if nombre.startswith("peer_"):
                nodo["peers"][nombre[5:]] = check
            elif isinstance(check, dict) and check.get("port") is not None:
                nodo["puertos"].append({
                    "nombre": nombre,
                    "puerto": check["port"],
                    "status": check.get("status"),
                    "servicio": servicio["slug"],
                })

    for nodo in nodos.values():
        estados = [s["status"] for s in nodo["servicios"]]
        nodo["status"] = (
            "down" if any(e in ("down", "unreachable") for e in estados)
            else "degraded" if "degraded" in estados
            else "ok"
        )
        nodo["servicios"].sort(key=lambda s: s["slug"])
        nodo["contenedores"].sort(key=lambda c: c.get("name") or "")
        nodo["puertos"].sort(key=lambda p: p["puerto"])

    return sorted(nodos.values(), key=lambda n: n["node"])


class MonitorApi:
    def __init__(self, config: Config, store: Store, notifier: Notifier) -> None:
        self._config = config
        self._store = store
        self._notifier = notifier
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> None:
        config, store, notifier = self._config, self._store, self._notifier

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                path = parsed.path.rstrip("/")
                query = parse_qs(parsed.query)

                if path in ("", "/healthz"):
                    self._json(200, {"status": "ok"})
                    return

                if path == "/ontoy":
                    self._json(200, {
                        "service": "huachicol-monitor",
                        "version": SERVICE_VERSION,
                        "status": "ok",
                    })
                    return

                if path == "/api/status":
                    states = store.all_states()
                    payload = [
                        _state_to_public(s, store, config.poll_interval)
                        for s in states
                    ]
                    self._json(200, {
                        "environment": config.environment,
                        "poll_interval": config.poll_interval,
                        "services": payload,
                        "summary": {
                            "total": len(payload),
                            "ok": sum(1 for s in payload if s["status"] == "ok"),
                            "degraded": sum(1 for s in payload if s["status"] == "degraded"),
                            "down": sum(
                                1 for s in payload
                                if s["status"] in ("down", "unreachable")
                            ),
                        },
                    })
                    return

                if path.startswith("/api/status/"):
                    slug = path.rsplit("/", 1)[-1]
                    state = store.get_state(slug)
                    if not state:
                        self._json(404, {"error": "servicio no encontrado"})
                        return
                    state["checks"] = json.loads(state["checks"]) if state["checks"] else {}
                    state["containers"] = (
                        json.loads(state["containers"]) if state["containers"] else []
                    )
                    limit = int((query.get("limit") or ["100"])[0])
                    payload = _state_to_public(state, store, config.poll_interval)
                    payload["history"] = store.history(slug, limit=min(limit, 500))
                    self._json(200, payload)
                    return

                if path == "/api/nodos":
                    states = store.all_states()
                    servicios = [
                        _state_to_public(s, store, config.poll_interval) for s in states
                    ]
                    nodos = _agrupar_por_nodo(servicios)
                    limite = int((query.get("eventos") or ["20"])[0])
                    self._json(200, {
                        "environment": config.environment,
                        "nodos": nodos,
                        "eventos": store.recent_events(min(limite, 100)),
                    })
                    return

                if path == "/api/events":
                    limit = int((query.get("limit") or ["50"])[0])
                    self._json(200, {"events": store.recent_events(min(limit, 200))})
                    return

                self._json(404, {"error": "not found"})

            def do_POST(self) -> None:
                path = urlparse(self.path).path.rstrip("/")

                if path == "/api/deploy/start":
                    until = store.start_deploy(config.deploy_timeout)
                    notifier.notify_deploy("start")
                    print(f"[deploy] ventana iniciada hasta {until}", flush=True)
                    self._json(200, {"deploy": "started", "until": until})
                    return

                if path == "/api/deploy/end":
                    store.end_deploy()
                    states = store.all_states()
                    total = len(states)
                    ok = sum(1 for s in states if s["status"] == "ok")
                    caidos = [
                        s["slug"] for s in states
                        if s["status"] in ("down", "unreachable")
                    ]
                    resumen = f"{ok}/{total} servicios ok."
                    if caidos:
                        resumen += " Con problemas: " + ", ".join(caidos) + "."
                    notifier.notify_deploy("end", resumen)
                    print("[deploy] ventana finalizada", flush=True)
                    self._json(200, {"deploy": "ended", "ok": ok, "total": total})
                    return

                self._json(404, {"error": "not found"})

            def _json(self, status: int, payload: Any) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args) -> None:
                return

        self._server = ThreadingHTTPServer(("0.0.0.0", self._config.api_port), Handler)
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        print(f"[api] escuchando en :{self._config.api_port}", flush=True)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
