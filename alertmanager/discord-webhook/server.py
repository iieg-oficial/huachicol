from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
import json, os, urllib.error, urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

COLORS = {
    "firing": {
        "critical": 0xED4245,
        "warning": 0xFEE75C,
    },
    "resolved": 0x57F287,
}

TEST_PAYLOAD = {
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "TestAlert",
                "service": "test-service",
                "severity": "warning",
            },
            "annotations": {
                "summary": "Alerta de prueba",
                "description": "Esta es una alerta de prueba para verificar la integración con Discord.",
            },
            "startsAt": datetime.now(timezone.utc).isoformat(),
        },
        {
            "status": "resolved",
            "labels": {
                "alertname": "TestAlertResolved",
                "service": "test-service",
                "severity": "critical",
            },
            "annotations": {
                "summary": "Alerta resuelta de prueba",
                "description": "Esta alerta resuelta es parte de la prueba de integración.",
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

    if status == "resolved":
        color = COLORS["resolved"]
        title = f"\u2705 {labels.get('alertname', 'N/A')} — Resuelta"
    else:
        color = COLORS["firing"].get(severity, 0x99AAB5)
        icon = "\U0001f6a8" if severity == "critical" else "\u26a0\ufe0f"
        title = f"{icon} {labels.get('alertname', 'N/A')} — {severity.upper()}"

    fields = []

    if annotations.get("description"):
        fields.append({"name": "Descripcion", "value": annotations["description"], "inline": False})

    if labels.get("service"):
        fields.append({"name": "Servicio", "value": labels["service"], "inline": True})

    if labels.get("project"):
        fields.append({"name": "Proyecto", "value": labels["project"], "inline": True})

    if labels.get("instance"):
        fields.append({"name": "Instancia", "value": labels["instance"], "inline": True})

    embed = {
        "title": title,
        "color": color,
        "fields": fields,
    }

    starts_at = alert.get("startsAt", "")
    if starts_at and not starts_at.startswith("0001"):
        embed["timestamp"] = starts_at

    if status == "resolved":
        ends_at = alert.get("endsAt", "")
        if ends_at and not ends_at.startswith("0001"):
            fields.append({"name": "Resuelta a las", "value": f"<t:{int(datetime.fromisoformat(ends_at).timestamp())}:T>", "inline": True})

    return embed


def format_embeds(body: dict) -> list[dict]:
    embeds = []
    for alert in body.get("alerts", []):
        embeds.append(build_embed(alert))
    return embeds[:10]


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
