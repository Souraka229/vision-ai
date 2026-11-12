"""Profils locaux (admin / standard / invité) avec PIN haché. Un geste n'est jamais une preuve d'identité."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "profiles.db"
ROLES = ("admin", "standard", "guest")


def _hash(pin: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 120_000).hex()


class Profiles:
    def __init__(self, path: Path = DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY, role TEXT, salt BLOB, pin TEXT)")
        self._db.commit()
        self.sessions: dict[str, tuple[str, str, float]] = {}  # token -> (name, role, expiry)
        self._fails: dict[str, list[float]] = {}

    def has_users(self) -> bool:
        return self._db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0

    def create(self, name: str, role: str, pin: str) -> None:
        if role not in ROLES:
            raise ValueError("Rôle invalide")
        if not (pin.isdigit() and 4 <= len(pin) <= 8):
            raise ValueError("Le PIN doit contenir 4 à 8 chiffres")
        salt = secrets.token_bytes(16)
        self._db.execute("INSERT INTO users VALUES(?,?,?,?)", (name, role, salt, _hash(pin, salt)))
        self._db.commit()

    def list(self) -> list[dict]:
        return [{"name": n, "role": r} for n, r in self._db.execute("SELECT name, role FROM users")]

    def login(self, name: str, pin: str) -> str | None:
        now = time.time()
        fails = [t for t in self._fails.get(name, []) if now - t < 60]
        if len(fails) >= 5:
            raise PermissionError("Trop d'essais, réessayez dans 1 minute")
        row = self._db.execute("SELECT role, salt, pin FROM users WHERE name=?", (name,)).fetchone()
        if not row or not hmac.compare_digest(_hash(pin, row[1]), row[2]):
            self._fails[name] = fails + [now]
            return None
        token = secrets.token_urlsafe(24)
        self.sessions[token] = (name, row[0], now + 8 * 3600)
        return token

    def whoami(self, token: str | None) -> dict | None:
        s = self.sessions.get(token or "")
        if not s or s[2] < time.time():
            return None
        return {"name": s[0], "role": s[1]}

    def logout(self, token: str) -> None:
        self.sessions.pop(token, None)
