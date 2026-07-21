from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import Config
from app.probes import STATUS_OK, ProbeResult

KIND_DOWN = "down"
KIND_RECOVERED = "recovered"
KIND_DEPLOYED = "deployed"
KIND_REMINDER = "reminder"


@dataclass
class Event:
    slug: str
    label: str
    kind: str
    status: str
    from_status: str | None
    detail: str | None
    since: str | None
    version: str | None = None
    previous_version: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def humanize_duration(since: str | None) -> str:
    started = _parse_iso(since)
    if not started:
        return "hace un momento"
    delta = _now() - started
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"hace {seconds}s"
    if seconds < 3600:
        return f"hace {seconds // 60} min"
    if seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"hace {hours}h {minutes}min" if minutes else f"hace {hours}h"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    return f"hace {days}d {hours}h" if hours else f"hace {days}d"


def evaluate(
    result: ProbeResult,
    previous: dict[str, Any] | None,
    config: Config,
) -> tuple[dict[str, Any], Event | None]:
    now = _now()
    healthy = result.status == STATUS_OK

    previous_status = previous["status"] if previous else None
    previous_version = previous["version"] if previous else None
    was_alerted = bool(previous["alerted"]) if previous else False
    failures = int(previous["consecutive_failures"]) if previous else 0
    successes = int(previous["consecutive_successes"]) if previous else 0
    since = previous["since"] if previous else _iso(now)
    alerted_at = previous["alerted_at"] if previous else None

    if healthy:
        successes += 1
        failures = 0
    else:
        failures += 1
        successes = 0

    if previous_status != result.status:
        since = _iso(now)

    event: Event | None = None

    if not healthy and not was_alerted and failures >= config.failure_threshold:
        event = Event(
            slug=result.slug,
            label=result.label,
            kind=KIND_DOWN,
            status=result.status,
            from_status=previous_status,
            detail=result.detail,
            since=since,
            version=result.version,
        )
        was_alerted = True
        alerted_at = _iso(now)

    elif healthy and was_alerted and successes >= config.recovery_threshold:
        event = Event(
            slug=result.slug,
            label=result.label,
            kind=KIND_RECOVERED,
            status=result.status,
            from_status=previous_status,
            detail=None,
            since=since,
            version=result.version,
        )
        was_alerted = False
        alerted_at = None

    elif not healthy and was_alerted and config.reminder_hours > 0:
        last_notified = _parse_iso(alerted_at)
        if last_notified and now - last_notified >= timedelta(hours=config.reminder_hours):
            event = Event(
                slug=result.slug,
                label=result.label,
                kind=KIND_REMINDER,
                status=result.status,
                from_status=previous_status,
                detail=result.detail,
                since=since,
                version=result.version,
            )
            alerted_at = _iso(now)

    if (
        event is None
        and healthy
        and previous_version
        and result.version
        and result.version != previous_version
    ):
        event = Event(
            slug=result.slug,
            label=result.label,
            kind=KIND_DEPLOYED,
            status=result.status,
            from_status=previous_status,
            detail=None,
            since=since,
            version=result.version,
            previous_version=previous_version,
        )

    state = {
        "slug": result.slug,
        "label": result.label,
        "status": result.status,
        "version": result.version,
        "deployed_at": result.deployed_at,
        "detail": result.detail,
        "checks": result.checks,
        "containers": result.containers,
        "latency_ms": result.latency_ms,
        "consecutive_failures": failures,
        "consecutive_successes": successes,
        "since": since,
        "alerted": was_alerted,
        "alerted_at": alerted_at,
    }
    return state, event
