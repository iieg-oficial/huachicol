import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TIMEOUT = 5.0


@dataclass(frozen=True)
class Target:
    slug: str
    label: str
    url: str
    timeout: float = DEFAULT_TIMEOUT
    critical: bool = True


@dataclass(frozen=True)
class Config:
    targets: list[Target]
    poll_interval: int = 60
    failure_threshold: int = 3
    recovery_threshold: int = 1
    history_retention_days: int = 30
    db_path: Path = Path("/data/monitor.db")
    api_port: int = 8090
    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    notify_min_interval: float = 2.0
    reminder_hours: int = 0
    environment: str = "production"
    deadman_url: str = ""
    extra: dict = field(default_factory=dict)


def _as_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _as_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_targets(path: Path) -> list[Target]:
    if not path.exists():
        raise FileNotFoundError(f"no se encontro el archivo de targets: {path}")

    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        raise ValueError("targets.json debe ser una lista de objetos")

    targets = []
    seen = set()
    for item in raw:
        slug = str(item.get("slug", "")).strip()
        url = str(item.get("url", "")).strip()
        if not slug or not url:
            continue
        if slug in seen:
            raise ValueError(f"slug duplicado en targets.json: {slug}")
        seen.add(slug)
        targets.append(Target(
            slug=slug,
            label=str(item.get("label") or slug),
            url=url,
            timeout=float(item.get("timeout") or DEFAULT_TIMEOUT),
            critical=bool(item.get("critical", True)),
        ))
    if not targets:
        raise ValueError("targets.json no contiene ningun target valido")
    return targets


def load_config() -> Config:
    targets_path = Path(os.environ.get("MONITOR_TARGETS_FILE", "/app/targets.json"))
    return Config(
        targets=load_targets(targets_path),
        poll_interval=_as_int("MONITOR_POLL_INTERVAL", 60),
        failure_threshold=_as_int("MONITOR_FAILURE_THRESHOLD", 3),
        recovery_threshold=_as_int("MONITOR_RECOVERY_THRESHOLD", 1),
        history_retention_days=_as_int("MONITOR_HISTORY_RETENTION_DAYS", 30),
        db_path=Path(os.environ.get("MONITOR_DB_PATH", "/data/monitor.db")),
        api_port=_as_int("MONITOR_API_PORT", 8090),
        discord_webhook_url=os.environ.get("DISCORD_WEBHOOK_URL", "").strip(),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
        notify_min_interval=_as_float("MONITOR_NOTIFY_MIN_INTERVAL", 2.0),
        reminder_hours=_as_int("MONITOR_REMINDER_HOURS", 0),
        environment=os.environ.get("MONITOR_ENVIRONMENT", "production").strip(),
        deadman_url=os.environ.get("MONITOR_DEADMAN_URL", "").strip(),
    )
