from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from urllib.parse import quote
import json, os, urllib.error, urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
PROMETHEUS_EXTERNAL_URL = os.environ.get("PROMETHEUS_EXTERNAL_URL", "").rstrip("/")
GRAFANA_EXTERNAL_URL = os.environ.get("GRAFANA_EXTERNAL_URL", "").rstrip("/")

COLORS = {
    "critical": 0xED4245,
    "warning": 0xFEE75C,
    "resolved": 0x57F287,
    "unknown": 0x99AAB5,
}

SEVERITY_BADGE = {
    "critical": "\U0001f534 crítico",
    "warning": "\U0001f7e1 advertencia",
    "info": "\U0001f535 info",
}

SEVERITY_TITLE_ICON = {
    "critical": "\U0001f6a8",
    "warning": "⚠️",
    "info": "ℹ️",
}

ALERT_TITLES = {
    "ServiceDown": "Servicio caído",
    "HighLatency": "Latencia alta",
    "HighErrorRate": "Tasa de errores alta",
    "HighMemoryUsage": "Uso de memoria alto",
    "DiskSpaceLow": "Espacio en disco bajo",
    "PostgreSQLDown": "PostgreSQL caído",
    "TooManyConnections": "Demasiadas conexiones a base de datos",
    "LokiDown": "Loki caído",
    "GrafanaDown": "Grafana caído",
    "AlertmanagerDown": "Alertmanager caído",
    "PrometheusStorageHigh": "Almacenamiento de Prometheus elevado",
    "PrometheusTargetScrapeFailure": "Fallos de scrape en Prometheus",
    "LokiHighIngestionRate": "Ingesta de logs alta en Loki",
}


def _target(labels: dict) -> str:
    for key in ("service", "job", "project", "instance", "container", "name"):
        value = labels.get(key)
        if value:
            return value
    return ""


def _links(labels: dict) -> str:
    parts = []
    if PROMETHEUS_EXTERNAL_URL:
        alertname = labels.get("alertname")
        if alertname:
            query = quote(f'ALERTS{{alertname="{alertname}"}}')
            parts.append(f"[Prometheus]({PROMETHEUS_EXTERNAL_URL}/graph?g0.expr={query}&g0.tab=1)")
        else:
            parts.append(f"[Prometheus]({PROMETHEUS_EXTERNAL_URL}/alerts)")
    if GRAFANA_EXTERNAL_URL:
        parts.append(f"[Grafana]({GRAFANA_EXTERNAL_URL})")
    return " · ".join(parts)


def build_embed(alert: dict) -> dict:
    status = alert.get("status", "unknown")
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    severity = labels.get("severity", "unknown")
    alertname = labels.get("alertname", "N/A")
    translated = ALERT_TITLES.get(alertname, alertname)
    target = _target(labels)

    if status == "resolved":
        color = COLORS["resolved"]
        icon = "✅"
        state_value = "✅ Resuelta"
    else:
        color = COLORS.get(severity, COLORS["unknown"])
        icon = SEVERITY_TITLE_ICON.get(severity, "❓")
        state_value = "\U0001f525 Activa"

    title = f"{icon} {translated}: {target}" if target else f"{icon} {translated}"

    description = annotations.get("summary") or annotations.get("description") or ""
    if description and annotations.get("summary") and annotations.get("description") \
            and annotations["summary"] != annotations["description"]:
        description = f"{annotations['summary']}\n\n{annotations['description']}"

    fields = []

    primary_label = labels.get("service") or labels.get("job")
    if primary_label:
        fields.append({"name": "Servicio", "value": f"`{primary_label}`", "inline": True})

    fields.append({"name": "Severidad", "value": f"`{SEVERITY_BADGE.get(severity, severity)}`", "inline": True})
    fields.append({"name": "Estado", "value": f"`{state_value}`", "inline": True})

    if labels.get("project"):
        fields.append({"name": "Proyecto", "value": f"`{labels['project']}`", "inline": True})

    if labels.get("instance"):
        fields.append({"name": "Instancia", "value": f"`{labels['instance']}`", "inline": True})

    if labels.get("server"):
        fields.append({"name": "Servidor", "value": f"`{labels['server']}`", "inline": True})

    starts_at = alert.get("startsAt", "")
    if status == "resolved":
        ends_at = alert.get("endsAt", "")
        if ends_at and not ends_at.startswith("0001"):
            try:
                ts = int(datetime.fromisoformat(ends_at.replace("Z", "+00:00")).timestamp())
                fields.append({"name": "Resuelta", "value": f"<t:{ts}:R>", "inline": True})
            except (ValueError, OSError):
                pass
    elif starts_at and not starts_at.startswith("0001"):
        try:
            ts = int(datetime.fromisoformat(starts_at.replace("Z", "+00:00")).timestamp())
            fields.append({"name": "Inicio", "value": f"<t:{ts}:R>", "inline": True})
        except (ValueError, OSError):
            pass

    links = _links(labels)
    if links:
        fields.append({"name": "Enlaces", "value": links, "inline": False})

    embed = {
        "title": title,
        "color": color,
        "fields": fields,
        "footer": {"text": "Huachicol"},
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }

    if description:
        embed["description"] = description

    return embed


def format_embeds(body: dict) -> list[dict]:
    return [build_embed(a) for a in body.get("alerts", [])][:10]


def send_to_discord(embeds: list[dict]) -> bool:
    if not DISCORD_URL:
        print("DISCORD_WEBHOOK_URL no configurada")
        return False
    payload = json.dumps({"embeds": embeds}).encode()
    try:
        req = urllib.request.Request(
            DISCORD_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AlertmanagerDiscord/1.0",
            },
            method="POST",
        )
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError as e:
        print(f"Discord respondio {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"Error enviando a Discord: {e}")
        return False


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            for a in body.get("alerts", []):
                print(f"[alert] {a.get('status')} | {a['labels'].get('alertname')} | severity={a['labels'].get('severity')}")

            embeds = format_embeds(body)
            success = send_to_discord(embeds)

            self.send_response(200 if success else 502)
            self.end_headers()
        except Exception as e:
            print(f"Error procesando request: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[webhook] {fmt % args}")


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9094), Handler).serve_forever()
