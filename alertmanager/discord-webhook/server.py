from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, urllib.request

DISCORD_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

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

        content = "\n---\n".join(lines) if lines else "Sin alertas"
        payload = json.dumps({"content": content[:2000]}).encode()

        req = urllib.request.Request(
            DISCORD_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"Error enviando a Discord: {e}")

        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        print(f"[webhook] {fmt % args}")

HTTPServer(("0.0.0.0", 9094), Handler).serve_forever()
