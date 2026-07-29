import json
import socket
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from app.config import Target

STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"
STATUS_UNREACHABLE = "unreachable"

VALID_STATUSES = {STATUS_OK, STATUS_DEGRADED, STATUS_DOWN}
FAILING_STATUSES = {STATUS_DOWN, STATUS_UNREACHABLE}


@dataclass
class ProbeResult:
    slug: str
    label: str
    status: str
    version: str | None = None
    deployed_at: str | None = None
    detail: str | None = None
    latency_ms: int | None = None
    checks: dict[str, Any] = field(default_factory=dict)
    containers: list[dict[str, Any]] = field(default_factory=list)

    @property
    def is_failing(self) -> bool:
        return self.status in FAILING_STATUSES


def _label_check(name: str, check: dict[str, Any]) -> str:
    detail = check.get("detail")
    return f"{name} ({detail})" if detail else name


def _describe_checks(checks: dict[str, Any]) -> str | None:
    failing: list[str] = []
    degraded: list[str] = []
    for name in sorted(checks):
        check = checks[name]
        if not isinstance(check, dict):
            continue
        status = check.get("status")
        if status in FAILING_STATUSES:
            failing.append(_label_check(name, check))
        elif status == STATUS_DEGRADED:
            degraded.append(_label_check(name, check))

    partes = []
    if failing:
        partes.append(f"checks en fallo: {', '.join(failing)}")
    if degraded:
        partes.append(f"checks degradados: {', '.join(degraded)}")
    return " | ".join(partes) if partes else None


def _parse_payload(target: Target, payload: dict[str, Any], latency_ms: int) -> ProbeResult:
    status = str(payload.get("status") or STATUS_OK)
    if status not in VALID_STATUSES:
        status = STATUS_OK

    checks = payload.get("checks") or {}
    if not isinstance(checks, dict):
        checks = {}

    containers = payload.get("containers") or []
    if not isinstance(containers, list):
        containers = []

    detail = _describe_checks(checks)

    return ProbeResult(
        slug=target.slug,
        label=target.label,
        status=status,
        version=payload.get("version"),
        deployed_at=payload.get("deployed_at"),
        detail=detail,
        latency_ms=latency_ms,
        checks=checks,
        containers=containers,
    )


def probe(target: Target) -> ProbeResult:
    started = time.monotonic()
    request = urllib.request.Request(
        target.url,
        method="GET",
        headers={"User-Agent": "huachicol-monitor/1.0", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=target.timeout) as response:
            body = response.read()
            latency_ms = int((time.monotonic() - started) * 1000)
            payload = json.loads(body)
            return _parse_payload(target, payload, latency_ms)

    except urllib.error.HTTPError as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            payload = json.loads(exc.read())
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get("status"):
            result = _parse_payload(target, payload, latency_ms)
            result.detail = result.detail or f"HTTP {exc.code}"
            return result
        return ProbeResult(
            slug=target.slug,
            label=target.label,
            status=STATUS_DOWN,
            detail=f"HTTP {exc.code}",
            latency_ms=latency_ms,
        )

    except (urllib.error.URLError, socket.timeout, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        return ProbeResult(
            slug=target.slug,
            label=target.label,
            status=STATUS_UNREACHABLE,
            detail=str(reason)[:160],
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    except json.JSONDecodeError:
        return ProbeResult(
            slug=target.slug,
            label=target.label,
            status=STATUS_DOWN,
            detail="respuesta no es JSON valido",
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    except Exception as exc:
        return ProbeResult(
            slug=target.slug,
            label=target.label,
            status=STATUS_UNREACHABLE,
            detail=str(exc)[:160],
            latency_ms=int((time.monotonic() - started) * 1000),
        )


def probe_all(targets: list[Target], max_workers: int = 8) -> list[ProbeResult]:
    if not targets:
        return []
    workers = min(max_workers, len(targets))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return list(executor.map(probe, targets))
