import sqlite3
import time
import secrets
from pathlib import Path
from typing import Optional

from config.settings import settings

DB_PATH = Path("tokens.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY, expires_at INTEGER)"
    )
    return conn


def issue_token(ttl: Optional[int] = None) -> str:
    """Generate and store a token with an expiry."""
    token = secrets.token_hex(32)
    expires_at = int(time.time()) + int(ttl or settings.TOKEN_TTL)
    with _get_conn() as conn:
        conn.execute(
            "REPLACE INTO tokens (token, expires_at) VALUES (?, ?)",
            (token, expires_at),
        )
        conn.commit()
    return token


def revoke_token(token: str) -> None:
    """Remove a token from the store."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        conn.commit()


def is_token_valid(token: str) -> bool:
    """Check if a token exists and has not expired."""
    now = int(time.time())
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT expires_at FROM tokens WHERE token = ?", (token,)
        ).fetchone()
        if not row:
            return False
        expires_at = row[0]
        if expires_at < now:
            conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
            conn.commit()
            return False
        return True
