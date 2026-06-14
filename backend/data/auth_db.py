"""
auth_db.py — In-memory session management for user login/logout.

Sessions are stored in a module-level dict keyed by session_id (UUID).
Each session holds: user_id, email, login_at.
"""
import uuid
from datetime import datetime
from typing import Optional

from data.crm_database import verify_user_password

# ─── Active sessions store ────────────────────────────────────────────────────
# { session_id: { user_id, email, login_at } }
ACTIVE_SESSIONS: dict[str, dict] = {}


def login(email: str, password: str) -> Optional[dict]:
    """
    Verify credentials. On success create a session and return:
        { session_id, user_id, email, login_at }
    Returns None on invalid credentials.
    """
    user = verify_user_password(email, password)
    if not user:
        return None

    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "user_id": user["user_id"],
        "email": user["email"],
        "login_at": datetime.now().isoformat(),
    }
    ACTIVE_SESSIONS[session_id] = session
    return session


def logout(session_id: str) -> bool:
    """Remove session. Returns True if session existed."""
    return ACTIVE_SESSIONS.pop(session_id, None) is not None


def get_session(session_id: str) -> Optional[dict]:
    """Return session dict or None if not found / expired."""
    return ACTIVE_SESSIONS.get(session_id)


def require_session(session_id: str) -> dict:
    """Return session or raise ValueError if invalid."""
    session = get_session(session_id)
    if not session:
        raise ValueError("Invalid or expired session. Please log in again.")
    return session
