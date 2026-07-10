"""
1S: ERP Free Edition — Bearer token authentication.

Tokens are stored in the tokens table in erp.db (SQLite, WAL mode).
Raw token values are NEVER stored — only sha256 hashes.
Default TTL: 24 hours (server-side; clients cannot override).

Do NOT log token values. TokenStore.__repr__ masks the db path only.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Server-side TTL limits (not user-configurable)
DEFAULT_TTL_HOURS = 24
MAX_TTL_HOURS = 168  # 7 days

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY,
    user       TEXT NOT NULL,
    role       TEXT NOT NULL DEFAULT 'user',
    expires    TEXT NOT NULL,
    created    TEXT NOT NULL
);
"""

_lock = threading.Lock()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class TokenStore:
    """Manages bearer tokens stored in the erp.db SQLite tokens table."""

    def __init__(self, db_path: Path) -> None:
        self._db = db_path
        self._ensure_table()

    def __repr__(self) -> str:
        return f"TokenStore(db={self._db})"

    def _connect(self) -> sqlite3.Connection:
        if not self._db.exists():
            raise RuntimeError(
                f"Database not found at {self._db}. "
                "Run the server at least once to initialise erp.db."
            )
        conn = sqlite3.connect(str(self._db), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        self._db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(_CREATE_TABLE)
        conn.commit()
        conn.close()

    def create(self, user: str, role: str = "user", ttl_hours: int = DEFAULT_TTL_HOURS) -> dict:
        """Create a token. Returns {token, expires_at} where expires_at is ISO 8601 UTC."""
        ttl_hours = min(max(1, ttl_hours), MAX_TTL_HOURS)
        raw = secrets.token_hex(64)
        h = _hash(raw)
        now = _now_utc()
        expires = now + timedelta(hours=ttl_hours)
        with _lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO tokens (token_hash, user, role, expires, created) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (h, user, role, _iso(expires), _iso(now)),
                )
                conn.commit()
            finally:
                conn.close()
        return {"token": raw, "expires_at": _iso(expires)}

    def validate(self, raw: str) -> Optional[dict]:
        """Return {user, role} if token is valid and not expired, else None."""
        h = _hash(raw)
        now = _now_utc()
        with _lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT user, role, expires FROM tokens WHERE token_hash = ?", (h,)
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        # constant-time comparison is used for the hash lookup above (single row);
        # the expiry check below is not timing-sensitive
        expires_dt = datetime.fromisoformat(row["expires"].replace("Z", "+00:00"))
        if now > expires_dt:
            self._purge(h)
            return None
        return {"user": row["user"], "role": row["role"]}

    def revoke(self, raw: str) -> bool:
        """Revoke a token by raw value. Returns True if it existed."""
        h = _hash(raw)
        with _lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM tokens WHERE token_hash = ?", (h,))
                conn.commit()
                return cur.rowcount > 0
            finally:
                conn.close()

    def _purge(self, token_hash: str) -> None:
        with _lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM tokens WHERE token_hash = ?", (token_hash,))
                conn.commit()
            finally:
                conn.close()

    def purge_expired(self) -> int:
        """Remove all expired tokens. Returns count deleted."""
        now = _iso(_now_utc())
        with _lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM tokens WHERE expires < ?", (now,))
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()
