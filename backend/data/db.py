"""
db.py — Thin SQLite connection helper for the CRM database.

Usage:
    from data.db import get_connection
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (cid,)).fetchone()
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

# Module-level cached connection (single-threaded / single-process use)
_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Return a cached sqlite3 connection to crm.db.

    The connection uses sqlite3.Row as row_factory so columns are accessible
    by name: ``row["customer_id"]``.
    Raises FileNotFoundError if crm.db does not exist (run setup_db.py first).
    """
    global _conn
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run `python data/setup_db.py` to create and seed it."
        )
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
        _conn.execute("PRAGMA journal_mode = WAL")   # safe for concurrent reads
    return _conn


def close_connection():
    """Explicitly close the cached connection (e.g. on app shutdown)."""
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
