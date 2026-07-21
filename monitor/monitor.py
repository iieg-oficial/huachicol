import signal
import sys
import threading
import time
from typing import Any

from app.alerting import Event, evaluate
from app.api import MonitorApi
from app.config import Config, load_config
from app.notifiers import Notifier
from app.probes import probe_all
from app.store import Store

_shutdown = threading.Event()


def _handle_signal(signum: int, _frame: Any) -> None:
    print(f"[monitor] senal {signum} recibida, cerrando", flush=True)
    _shutdown.set()


def run_cycle(config: Config, store: Store, notifier: Notifier) -> list[Event]:
    results = probe_all(config.targets)
    events: list[Event] = []

    for result in results:
        previous = store.get_state(result.slug)
        state, event = evaluate(result, previous, config)

        store.save_state(
            slug=state["slug"],
            label=state["label"],
            status=state["status"],
            version=state["version"],
            deployed_at=state["deployed_at"],
            detail=state["detail"],
            checks=state["checks"],
            containers=state["containers"],
            latency_ms=state["latency_ms"],
            consecutive_failures=state["consecutive_failures"],
            consecutive_successes=state["consecutive_successes"],
            since=state["since"],
            alerted=state["alerted"],
            alerted_at=state["alerted_at"],
        )
        store.record_check(
            result.slug, result.status, result.latency_ms, result.detail
        )

        if event:
            events.append(event)

    if events:
        delivered = notifier.notify(events)
        for event in events:
            store.record_event(
                slug=event.slug,
                kind=event.kind,
                from_status=event.from_status,
                to_status=event.status,
                detail=event.detail,
                notified=delivered,
            )
        estado = "enviadas" if delivered else "FALLO el envio de"
        print(f"[monitor] {len(events)} notificacion(es) {estado}", flush=True)

    failing = [r for r in results if r.status != "ok"]
    print(
        f"[monitor] ciclo: {len(results)} servicios, {len(failing)} con problemas",
        flush=True,
    )
    return events


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        config = load_config()
    except Exception as exc:
        print(f"[monitor] error de configuracion: {exc}", flush=True)
        return 1

    store = Store(config.db_path)
    notifier = Notifier(config)
    api = MonitorApi(config, store)
    api.start()

    canales = []
    if config.discord_webhook_url:
        canales.append("discord")
    if config.telegram_bot_token and config.telegram_chat_id:
        canales.append("telegram")
    print(
        f"[monitor] {len(config.targets)} targets, cada {config.poll_interval}s, "
        f"umbral {config.failure_threshold} fallos, notificando por "
        f"{', '.join(canales) if canales else 'ningun canal'}",
        flush=True,
    )

    last_prune = 0.0
    while not _shutdown.is_set():
        started = time.monotonic()
        try:
            run_cycle(config, store, notifier)
        except Exception as exc:
            print(f"[monitor] error en el ciclo: {exc}", flush=True)

        if time.monotonic() - last_prune > 86400:
            removed = store.prune(config.history_retention_days)
            if removed:
                print(f"[monitor] purgados {removed} registros antiguos", flush=True)
            last_prune = time.monotonic()

        elapsed = time.monotonic() - started
        _shutdown.wait(max(1.0, config.poll_interval - elapsed))

    api.stop()
    store.close()
    print("[monitor] detenido", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
