from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
import json, os, urllib.error, urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

COLORS = {
    "critical": 0xED4245,
    "warning": 0xFEE75C,
    "resolved": 0x57F287,
}

SEVERITY_ICONS = {
    "critical": "\U0001f6a8",
    "warning": "\u26a0\ufe0f",
}

ALERT_TITLES = {
    "ServiceDown": "Servicio caido",
    "HighLatency": "Latencia alta",
    "HighErrorRate": "Tasa de errores alta",
    "HighMemoryUsage": "Uso de memoria alto",
    "DiskSpaceLow": "Espacio en disco bajo",
    "PostgreSQLDown": "PostgreSQL caido",
    "TooManyConnections": "Demasiadas conexiones",
}

TEST_PAYLOAD = {
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "TestAlert",
                "service": "test-service",
                "project": "test-project",
                "instance": "localhost:9090",
                "severity": "warning",
            },
            "annotations": {
                "summary": "Alerta de prueba",
                "description": "Esta es una alerta de prueba para verificar la integracion con Discord.",
            },
            "startsAt": datetime.now(timezone.utc).isoformat(),
        },
        {
            "status": "resolved",
            "labels": {
                "alertname": "TestAlertResolved",
                "service": "test-service",
                "project": "test-project",
                "instance": "localhost:9090",
                "severity": "critical",
            },
            "annotations": {
                "summary": "Alerta resuelta de prueba",
                "description": "Esta alerta resuelta es parte de la prueba de integracion.",
            },
            "startsAt": datetime.now(timezone.utc).isoformat(),
            "endsAt": datetime.now(timezone.utc).isoformat(),
        },
    ]
}


def build_embed(alert: dict) -> dict:
    status = alert.get("status", "unknown")
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    severity = labels.get("severity", "unknown")
    alertname = labels.get("alertname", "N/A")

    translated = ALERT_TITLES.get(alertname, alertname)

    if status == "resolved":
        color = COLORS["resolved"]
        title = f"\u2705 {translated}"
        description = f"**{alertname}** se ha resuelto."
    else:
        color = COLORS.get(severity, 0x99AAB5)
        icon = SEVERITY_ICONS.get(severity, "\u2753")
        title = f"{icon} {translated}"
        sev_label = "CRITICO" if severity == "critical" else "ADVERTENCIA"
        description = f"**{alertname}** — {sev_label}"

    fields = []

    if annotations.get("description"):
        fields.append({"name": "Detalle", "value": annotations["description"], "inline": False})

    if labels.get("service"):
        fields.append({"name": "Servicio", "value": f"`{labels['service']}`", "inline": True})

    if labels.get("project"):
        fields.append({"name": "Proyecto", "value": f"`{labels['project']}`", "inline": True})

    if labels.get("instance"):
        fields.append({"name": "Instancia", "value": f"`{labels['instance']}`", "inline": True})

    if labels.get("server"):
        fields.append({"name": "Servidor", "value": f"`{labels['server']}`", "inline": True})

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields,
    }

    starts_at = alert.get("startsAt", "")
    if starts_at and not starts_at.startswith("0001"):
        embed["timestamp"] = starts_at

    if status == "resolved":
        ends_at = alert.get("endsAt", "")
        if ends_at and not ends_at.startswith("0001"):
            try:
                ts = int(datetime.fromisoformat(ends_at).timestamp())
                fields.append({"name": "Resuelta", "value": f"<t:{ts}:R>", "inline": True})
            except (ValueError, OSError):
                pass

    embed["footer"] = {"text": "IIEG Monitoring"}

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
            if self.path == "/test":
                body = TEST_PAYLOAD
            else:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))

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


HTTPServer(("0.0.0.0", 9094), Handler).serve_forever()
