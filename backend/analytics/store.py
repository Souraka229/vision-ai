"""Événements réellement observés -> SQLite ; statistiques calculées depuis ces événements."""
from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "analytics" / "events.db"


class EventStore:
    def __init__(self, path: Path = DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.execute("CREATE TABLE IF NOT EXISTS events(ts REAL, kind TEXT, name TEXT, value REAL)")
        self._db.execute("CREATE INDEX IF NOT EXISTS i_k ON events(kind, ts)")
        self._db.commit()
        self.recent: list[dict] = []

    def log(self, kind: str, name: str = "", value: float = 0.0) -> None:
        ts = time.time()
        with self._lock:
            self._db.execute("INSERT INTO events VALUES(?,?,?,?)", (ts, kind, name, value))
            self._db.commit()
            if kind in ("gesture", "command", "interaction"):  # métriques périodiques exclues du fil
                self.recent = ([{"ts": ts, "kind": kind, "name": name, "value": value}] + self.recent)[:30]

    def stats(self, since: float = 0.0) -> dict:
        with self._lock:
            q = lambda s, *a: self._db.execute(s, a).fetchall()
            by = lambda k: dict(q("SELECT name, COUNT(*) FROM events WHERE kind=? AND ts>=? GROUP BY name", k, since))
            peak = lambda k: q("SELECT COALESCE(MAX(value),0) FROM events WHERE kind=? AND ts>=?", k, since)[0][0]
            avg = lambda k: q("SELECT COALESCE(AVG(value),0) FROM events WHERE kind=? AND ts>=?", k, since)[0][0]
            return {
                "gestures": by("gesture"), "commands": by("command"),
                "interactions": q("SELECT COUNT(*) FROM events WHERE kind='interaction' AND ts>=?", since)[0][0],
                "max_people": int(peak("people")), "max_phones": int(peak("phones")),
                "avg_latency_ms": round(avg("latency"), 1), "avg_fps": round(avg("fps"), 1),
                "avg_ram_mb": round(avg("ram"), 1),
            }

    def clear(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM events")
            self._db.commit()
            self.recent = []
