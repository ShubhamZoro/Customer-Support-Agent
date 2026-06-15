"""
crm_database.py — SQLite-backed data accessors for the orders/users schema.

Tables: users, orders

Return-window policy is defined here (RETURN_WINDOWS) as the single source
of truth and is imported by refund_policy.py and agent tools.
"""
import hashlib
import sqlite3
from datetime import datetime
from typing import Optional

from data.db import get_connection


# ─── Category-based return window (days) — THE single source of truth ─────────
RETURN_WINDOWS: dict[str, int] = {
    "Electronics": 30,
    "Clothing": 15,
    "Home": 30,
    "Books": 14,
    "Toys": 21,
    "Subscription": 7,
    "Services": 7,
}

# Payment methods that are entirely non-refundable
NON_REFUNDABLE_PAYMENT_METHODS: set[str] = {"Gift Card"}

# Return statuses that mean a refund has already been processed
ALREADY_REFUNDED_STATUSES: set[str] = {"Refund Initiated", "Returned"}


def _hash_password(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


def _row_to_order(row: sqlite3.Row) -> dict:
    return {
        "order_id":         row["order_id"],
        "product_id":       row["product_id"],
        "user_id":          row["user_id"],
        "order_date":       row["order_date"],
        "return_date":      row["return_date"],
        "product_category": row["product_category"],
        "product_price":    row["product_price"],
        "order_quantity":   row["order_quantity"],
        "return_reason":    row["return_reason"],
        "return_status":    row["return_status"],
        "days_to_return":   row["days_to_return"],
        "payment_method":   row["payment_method"],
        "shipping_method":  row["shipping_method"],
        "discount_applied": row["discount_applied"],
    }


def _row_to_user(row: sqlite3.Row) -> dict:
    return {
        "user_id":       row["user_id"],
        "email":         row["email"],
        "user_age":      row["user_age"],
        "user_gender":   row["user_gender"],
        "user_location": row["user_location"],
    }


# ─── User queries ─────────────────────────────────────────────────────────────

def get_user(user_id: str) -> Optional[dict]:
    """Return user dict (no password) or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id.upper(),)
    ).fetchone()
    return _row_to_user(row) if row else None


def list_users() -> list[dict]:
    """Return all users (no password hashes)."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
    return [_row_to_user(r) for r in rows]


def next_user_id() -> str:
    """Generate the next sequential USR-XXX id."""
    conn = get_connection()
    row = conn.execute("SELECT user_id FROM users ORDER BY user_id DESC LIMIT 1").fetchone()
    if not row:
        return "USR-001"
    last = row["user_id"]  # e.g. "USR-008"
    try:
        num = int(last.split("-")[1]) + 1
    except (IndexError, ValueError):
        num = 1
    return f"USR-{num:03d}"


def create_user(email: str, plain_password: str, age: int = None,
                gender: str = None, location: str = None) -> Optional[dict]:
    """
    Create a new user. Returns the created user dict, or None if email already exists.
    """
    conn = get_connection()
    # Check uniqueness
    existing = conn.execute(
        "SELECT user_id FROM users WHERE LOWER(email) = LOWER(?)", (email,)
    ).fetchone()
    if existing:
        return None

    user_id = next_user_id()
    pw_hash = _hash_password(plain_password)
    conn.execute(
        """INSERT INTO users (user_id, email, password_hash, user_age, user_gender, user_location)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, email, pw_hash, age, gender, location),
    )
    conn.commit()
    return get_user(user_id)


def get_user_by_email(email: str) -> Optional[dict]:
    """Return user dict (no password) or None."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)
    ).fetchone()
    return _row_to_user(row) if row else None


def verify_user_password(email: str, plain_password: str) -> Optional[dict]:
    """Verify credentials. Returns user dict on success, None on failure."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)
    ).fetchone()
    if not row:
        return None
    if row["password_hash"] != _hash_password(plain_password):
        return None
    return _row_to_user(row)


# ─── Order queries ────────────────────────────────────────────────────────────

def get_order(order_id: str) -> Optional[dict]:
    """Return order dict or None (no ownership check)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ?", (order_id.upper(),)
    ).fetchone()
    return _row_to_order(row) if row else None


def get_order_for_user(order_id: str, user_id: str) -> Optional[dict]:
    """
    Return order dict ONLY if the order belongs to the given user.
    Returns None if not found OR if the order belongs to a different user.
    Callers should distinguish using get_order() first when needed.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM orders WHERE order_id = ? AND user_id = ?",
        (order_id.upper(), user_id.upper()),
    ).fetchone()
    return _row_to_order(row) if row else None


def get_orders_for_user(user_id: str) -> list[dict]:
    """Return all orders belonging to a user, newest first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC",
        (user_id.upper(),),
    ).fetchall()
    return [_row_to_order(r) for r in rows]


def get_return_window(product_category: str) -> int:
    """Return the policy return window (days) for a given product category."""
    return RETURN_WINDOWS.get(product_category, 30)


def days_since_order(order_date: str) -> int:
    """Calculate days elapsed since order_date (YYYY-MM-DD)."""
    try:
        d = datetime.strptime(order_date, "%Y-%m-%d")
        return (datetime.now() - d).days
    except Exception:
        return 0


def is_already_refunded(order: dict) -> bool:
    """True if the order has already been refunded or has a refund in progress."""
    return order["return_status"] in ALREADY_REFUNDED_STATUSES


def is_payment_non_refundable(order: dict) -> bool:
    """True if the payment method is non-refundable (e.g. Gift Card)."""
    return order["payment_method"] in NON_REFUNDABLE_PAYMENT_METHODS


# ─── Refund mutation ──────────────────────────────────────────────────────────

def initiate_refund_in_db(order_id: str, reason: str) -> bool:
    """
    Set return_status = 'Refund Initiated', return_date = today, days_to_return = N.
    Returns True on success, False if order not found.
    """
    conn = get_connection()
    order = get_order(order_id)
    if not order:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    elapsed = days_since_order(order["order_date"])

    conn.execute(
        """UPDATE orders
           SET return_status  = 'Refund Initiated',
               return_date    = ?,
               return_reason  = ?,
               days_to_return = ?
           WHERE order_id = ?""",
        (today, reason, elapsed, order_id.upper()),
    )
    conn.commit()
    return True
