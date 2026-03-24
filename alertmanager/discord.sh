#!/bin/sh

BODY=$(cat)

ALERTS=$(echo "$BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
msgs = []
for alert in data.get('alerts', []):
    status = alert.get('status', 'unknown')
    name = alert['labels'].get('alertname', 'N/A')
    severity = alert['labels'].get('severity', 'N/A')
    service = alert['labels'].get('service', 'N/A')
    desc = alert['annotations'].get('description', 'Sin descripcion')
    emoji = '🔴' if status == 'firing' else '🟢'
    msgs.append(f'{emoji} **{name}** ({status})\nServicio: {service}\nSeveridad: {severity}\n{desc}')
print('\n---\n'.join(msgs) if msgs else 'Sin alertas')
")

curl -s -X POST "$DISCORD_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "{\"content\": $(echo "$ALERTS" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))")}"
