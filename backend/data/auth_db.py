"""
auth_db.py — SQLite-backed session management for user login/logout.

Sessions are persisted in crm.db (sessions table) so they survive server
restarts.  Each session holds: session_id, user_id, email, login_at.
Sessions older than SESSION_TTL_DAYS are automatically pruned on startup.
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from data.crm_database import verify_user_password
from data.db import get_connection

SESSION_TTL_DAYS = 7

# ─── Table bootstrap ──────────────────────────────────────────────────────────

def _ensure_table():
    """Create the sessions table if it doesn't exist and prune old rows."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            email      TEXT NOT NULL,
            login_at   TEXT NOT NULL
        )
    """)
    # Remove sessions older than TTL
    cutoff = (datetime.now() - timedelta(days=SESSION_TTL_DAYS)).isoformat()
    conn.execute("DELETE FROM sessions WHERE login_at < ?", (cutoff,))
    conn.commit()


_ensure_table()


# ─── Public API ───────────────────────────────────────────────────────────────

def login(email: str, password: str) -> Optional[dict]:
    """
    Verify credentials. On success create a persistent session and return:
        { session_id, user_id, email, login_at }
    Returns None on invalid credentials.
    """
    user = verify_user_password(email, password)
    if not user:
        return None

    session_id = str(uuid.uuid4())
    login_at   = datetime.now().isoformat()

    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (session_id, user_id, email, login_at) VALUES (?, ?, ?, ?)",
        (session_id, user["user_id"], user["email"], login_at),
    )
    conn.commit()

    return {
        "session_id": session_id,
        "user_id":    user["user_id"],
        "email":      user["email"],
        "login_at":   login_at,
    }


def logout(session_id: str) -> bool:
    """Remove session. Returns True if session existed."""
    conn   = get_connection()
    cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    return cursor.rowcount > 0


def get_session(session_id: str) -> Optional[dict]:
    """Return session dict or None if not found / expired."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT session_id, user_id, email, login_at FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "session_id": row["session_id"],
        "user_id":    row["user_id"],
        "email":      row["email"],
        "login_at":   row["login_at"],
    }


def require_session(session_id: str) -> dict:
    """Return session or raise ValueError if invalid."""
    session = get_session(session_id)
    if not session:
        raise ValueError("Invalid or expired session. Please log in again.")
    return session
