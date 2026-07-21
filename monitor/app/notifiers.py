import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.alerting import (
    KIND_DEPLOYED,
    KIND_DOWN,
    KIND_RECOVERED,
    KIND_REMINDER,
    Event,
    humanize_duration,
)
from app.config import Config

COLOR_DOWN = 0xED4245
COLOR_DEGRADED = 0xFEE75C
COLOR_RECOVERED = 0x57F287
COLOR_INFO = 0x5865F2

STATUS_LABEL = {
    "ok": "operativo",
    "degraded": "degradado",
    "down": "caido",
    "unreachable": "no responde",
}

KIND_ICON = {
    KIND_RECOVERED: "✅",
    KIND_DEPLOYED: "\U0001f680",
    KIND_REMINDER: "\U0001f514",
}

STATUS_ICON = {
    "degraded": "\U0001f7e1",
    "down": "\U0001f534",
    "unreachable": "\U0001f534",
}

MAX_EMBEDS = 10
MAX_TELEGRAM_CHARS = 3800


def _headline(event: Event) -> str:
    icon = KIND_ICON.get(event.kind) or STATUS_ICON.get(event.status, "ℹ️")
    if event.kind == KIND_RECOVERED:
        return f"{icon} {event.label}: recuperado"
    if event.kind == KIND_DEPLOYED:
        return f"{icon} {event.label}: desplegada v{event.version}"
    if event.kind == KIND_REMINDER:
        return f"{icon} {event.label}: sigue {STATUS_LABEL.get(event.status, event.status)}"
    return f"{icon} {event.label}: {STATUS_LABEL.get(event.status, event.status)}"


def _body_lines(event: Event) -> list[str]:
    lines = []
    if event.kind == KIND_DEPLOYED:
        lines.append(f"Version {event.previous_version} → {event.version}")
        return lines
    if event.kind == KIND_RECOVERED:
        lines.append(f"Estuvo afectado {humanize_duration(event.since)}")
        if event.version:
            lines.append(f"Version: {event.version}")
        return lines
    lines.append(f"Desde {humanize_duration(event.since)}")
    if event.detail:
        lines.append(event.detail)
    if event.version:
        lines.append(f"Version: {event.version}")
    return lines


class Notifier:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._last_sent = 0.0

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_sent
        remaining = self._config.notify_min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_sent = time.monotonic()

    def notify(self, events: list[Event]) -> bool:
        if not events:
            return True

        canales = []
        if self._config.discord_webhook_url:
            canales.append(self._send_discord)
        if self._config.telegram_bot_token and self._config.telegram_chat_id:
            canales.append(self._send_telegram)

        if not canales:
            print("[notify] sin canales configurados, evento no entregado", flush=True)
            return False

        delivered = True
        for enviar in canales:
            delivered = enviar(events) and delivered
        return delivered

    def _send_discord(self, events: list[Event]) -> bool:
        embeds = []
        for event in events[:MAX_EMBEDS]:
            if event.kind == KIND_RECOVERED:
                color = COLOR_RECOVERED
            elif event.kind == KIND_DEPLOYED:
                color = COLOR_INFO
            elif event.status == "degraded":
                color = COLOR_DEGRADED
            else:
                color = COLOR_DOWN
            embeds.append({
                "title": _headline(event),
                "description": "\n".join(_body_lines(event)),
                "color": color,
                "footer": {"text": f"huachicol-monitor · {self._config.environment}"},
            })

        payload: dict[str, Any] = {"embeds": embeds}
        overflow = len(events) - MAX_EMBEDS
        if overflow > 0:
            payload["content"] = f"… y {overflow} evento(s) mas en este ciclo"

        return self._post_json(self._config.discord_webhook_url, payload, "discord")

    def _send_telegram(self, events: list[Event]) -> bool:
        blocks = []
        for event in events:
            body = "\n".join(f"  {line}" for line in _body_lines(event))
            blocks.append(f"{_headline(event)}\n{body}")

        text = "\n\n".join(blocks)
        if len(text) > MAX_TELEGRAM_CHARS:
            text = text[:MAX_TELEGRAM_CHARS] + "\n\n… truncado"

        url = f"https://api.telegram.org/bot{self._config.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": self._config.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        return self._post_json(url, payload, "telegram")

    def _post_json(self, url: str, payload: dict[str, Any], channel: str) -> bool:
        self._throttle()
        data = json.dumps(payload, ensure_ascii=False).encode()
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "huachicol-monitor/1.0",
            },
            method="POST",
        )
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    if 200 <= response.status < 300:
                        return True
                    print(f"[notify] {channel} respondio {response.status}", flush=True)
                    return False
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    retry_after = self._retry_after(exc)
                    print(
                        f"[notify] {channel} rate limit, reintento en {retry_after}s",
                        flush=True,
                    )
                    time.sleep(retry_after)
                    continue
                print(f"[notify] {channel} HTTP {exc.code}: {exc.read()[:200]}", flush=True)
                return False
            except Exception as exc:
                print(f"[notify] {channel} error: {exc}", flush=True)
                if attempt == 2:
                    return False
                time.sleep(2 * (attempt + 1))
        return False

    @staticmethod
    def _retry_after(exc: urllib.error.HTTPError) -> float:
        header = exc.headers.get("Retry-After") if exc.headers else None
        if header:
            try:
                return min(float(header), 30.0)
            except ValueError:
                pass
        try:
            payload = json.loads(exc.read())
            if isinstance(payload, dict):
                value = payload.get("retry_after") or payload.get("parameters", {}).get(
                    "retry_after"
                )
                if value:
                    return min(float(value), 30.0)
        except Exception:
            pass
        return 5.0
