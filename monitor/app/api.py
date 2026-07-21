import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.alerting import humanize_duration
from app.config import Config
from app.store import Store

SERVICE_VERSION = "1.0.0"


def _state_to_public(state: dict[str, Any], store: Store) -> dict[str, Any]:
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
        "uptime_24h": store.uptime_percent(state["slug"], hours=24),
        "alerted": state["alerted"],
    }


class MonitorApi:
    def __init__(self, config: Config, store: Store) -> None:
        self._config = config
        self._store = store
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> None:
        config, store = self._config, self._store

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
                    payload = [_state_to_public(s, store) for s in states]
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
                    payload = _state_to_public(state, store)
                    payload["history"] = store.history(slug, limit=min(limit, 500))
                    self._json(200, payload)
                    return

                if path == "/api/events":
                    limit = int((query.get("limit") or ["50"])[0])
                    self._json(200, {"events": store.recent_events(min(limit, 200))})
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
