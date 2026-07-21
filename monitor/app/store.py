import json
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS service_state (
    slug TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    status TEXT NOT NULL,
    version TEXT,
    deployed_at TEXT,
    detail TEXT,
    checks TEXT,
    containers TEXT,
    latency_ms INTEGER,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    consecutive_successes INTEGER NOT NULL DEFAULT 0,
    since TEXT NOT NULL,
    last_checked TEXT NOT NULL,
    alerted INTEGER NOT NULL DEFAULT 0,
    alerted_at TEXT
);

CREATE TABLE IF NOT EXISTS check_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER,
    detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_history_slug_time ON check_history (slug, checked_at);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    kind TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    detail TEXT,
    notified INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_time ON events (occurred_at);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Store:
    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def get_state(self, slug: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM service_state WHERE slug = ?", (slug,)
            ).fetchone()
        return dict(row) if row else None

    def all_states(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM service_state ORDER BY slug"
            ).fetchall()
        states = []
        for row in rows:
            state = dict(row)
            state["checks"] = json.loads(state["checks"]) if state["checks"] else {}
            state["containers"] = json.loads(state["containers"]) if state["containers"] else []
            state["alerted"] = bool(state["alerted"])
            states.append(state)
        return states

    def save_state(
        self,
        slug: str,
        label: str,
        status: str,
        version: str | None,
        deployed_at: str | None,
        detail: str | None,
        checks: dict[str, Any],
        containers: list[dict[str, Any]],
        latency_ms: int | None,
        consecutive_failures: int,
        consecutive_successes: int,
        since: str,
        alerted: bool,
        alerted_at: str | None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO service_state (
                    slug, label, status, version, deployed_at, detail, checks, containers,
                    latency_ms, consecutive_failures, consecutive_successes, since,
                    last_checked, alerted, alerted_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(slug) DO UPDATE SET
                    label=excluded.label,
                    status=excluded.status,
                    version=excluded.version,
                    deployed_at=excluded.deployed_at,
                    detail=excluded.detail,
                    checks=excluded.checks,
                    containers=excluded.containers,
                    latency_ms=excluded.latency_ms,
                    consecutive_failures=excluded.consecutive_failures,
                    consecutive_successes=excluded.consecutive_successes,
                    since=excluded.since,
                    last_checked=excluded.last_checked,
                    alerted=excluded.alerted,
                    alerted_at=excluded.alerted_at
                """,
                (
                    slug, label, status, version, deployed_at, detail,
                    json.dumps(checks, ensure_ascii=False),
                    json.dumps(containers, ensure_ascii=False),
                    latency_ms, consecutive_failures, consecutive_successes, since,
                    _now(), int(alerted), alerted_at,
                ),
            )
            self._conn.commit()

    def record_check(
        self, slug: str, status: str, latency_ms: int | None, detail: str | None
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO check_history (slug, checked_at, status, latency_ms, detail)"
                " VALUES (?,?,?,?,?)",
                (slug, _now(), status, latency_ms, detail),
            )
            self._conn.commit()

    def record_event(
        self,
        slug: str,
        kind: str,
        from_status: str | None,
        to_status: str | None,
        detail: str | None,
        notified: bool,
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (slug, occurred_at, kind, from_status, to_status,"
                " detail, notified) VALUES (?,?,?,?,?,?,?)",
                (slug, _now(), kind, from_status, to_status, detail, int(notified)),
            )
            self._conn.commit()

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events ORDER BY occurred_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def history(self, slug: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT checked_at, status, latency_ms, detail FROM check_history"
                " WHERE slug = ? ORDER BY checked_at DESC LIMIT ?",
                (slug, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def uptime_percent(self, slug: str, hours: int = 24) -> float | None:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS total,"
                " SUM(CASE WHEN status IN ('ok','degraded') THEN 1 ELSE 0 END) AS up"
                " FROM check_history WHERE slug = ? AND checked_at >= ?",
                (slug, cutoff),
            ).fetchone()
        if not row or not row["total"]:
            return None
        return round((row["up"] or 0) / row["total"] * 100, 2)

    def _set_meta(self, key: str, value: str | None) -> None:
        with self._lock:
            if value is None:
                self._conn.execute("DELETE FROM meta WHERE key = ?", (key,))
            else:
                self._conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?,?)"
                    " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
            self._conn.commit()

    def _get_meta(self, key: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else None

    def start_deploy(self, timeout_seconds: int) -> str:
        until = (
            datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        self._set_meta("deploy_until", until)
        self._set_meta("deploy_started_at", _now())
        return until

    def end_deploy(self) -> None:
        self._set_meta("deploy_until", None)
        self._set_meta("deploy_started_at", None)

    def deploy_state(self) -> dict[str, Any]:
        until = self._get_meta("deploy_until")
        return {
            "active": bool(until) and _now() < until,
            "until": until,
            "started_at": self._get_meta("deploy_started_at"),
        }

    def prune(self, retention_days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM check_history WHERE checked_at < ?", (cutoff,)
            )
            self._conn.execute("DELETE FROM events WHERE occurred_at < ?", (cutoff,))
            self._conn.commit()
            return cursor.rowcount
