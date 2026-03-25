from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, urllib.error, urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

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
                "description": "Esta es una alerta de prueba para verificar la integración con Discord.",
            },
        },
        {
            "status": "resolved",
            "labels": {
                "alertname": "TestAlertResolved",
                "service": "test-service",
                "severity": "critical",
            },
            "annotations": {
                "description": "Esta alerta resuelta es parte de la prueba de integración.",
            },
        },
    ]
}


def format_alerts(body: dict) -> str:
    lines = []
    for alert in body.get("alerts", []):
        status = alert.get("status", "unknown")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        emoji = "\U0001f534" if status == "firing" else "\U0001f7e2"
        lines.append(
            f'{emoji} **{labels.get("alertname", "N/A")}** ({status})\n'
            f'Servicio: {labels.get("service", "N/A")}\n'
            f'Severidad: {labels.get("severity", "N/A")}\n'
            f'{annotations.get("description", "")}'
        )
    return "\n---\n".join(lines) if lines else "Sin alertas"


def send_to_discord(content: str) -> bool:
    if not DISCORD_URL:
        print("DISCORD_WEBHOOK_URL no configurada")
        return False
    payload = json.dumps({"content": content[:2000]}).encode()
    try:
        req = urllib.request.Request(
            DISCORD_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
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

            content = format_alerts(body)
            success = send_to_discord(content)

            self.send_response(200 if success else 502)
            self.end_headers()
        except Exception as e:
            print(f"Error procesando request: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[webhook] {fmt % args}")


HTTPServer(("0.0.0.0", 9094), Handler).serve_forever()
