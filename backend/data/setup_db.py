"""
setup_db.py — Create and seed the SQLite database for the Refund Support Agent.
Run: python data/setup_db.py [--force]

Tables
------
users   — registered users (email, password_hash, demographics)
orders  — order records with full return tracking fields
"""
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "crm.db"

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")


def _hash_password(plain: str) -> str:
    """SHA-256 hash (bcrypt preferred in production; sha256 fine for demo)."""
    return hashlib.sha256(plain.encode()).hexdigest()


# ─── Seed data ───────────────────────────────────────────────────────────────

USERS = [
    {
        "user_id": "USR-001", "email": "alice.johnson@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 32, "user_gender": "Female", "user_location": "Austin",
    },
    {
        "user_id": "USR-002", "email": "bob.martinez@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 45, "user_gender": "Male", "user_location": "Denver",
    },
    {
        "user_id": "USR-003", "email": "carol.white@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 28, "user_gender": "Female", "user_location": "Seattle",
    },
    {
        "user_id": "USR-004", "email": "david.chen@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 37, "user_gender": "Male", "user_location": "Chicago",
    },
    {
        "user_id": "USR-005", "email": "emma.davis@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 24, "user_gender": "Female", "user_location": "Miami",
    },
    {
        "user_id": "USR-006", "email": "frank.wilson@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 55, "user_gender": "Male", "user_location": "Portland",
    },
    {
        "user_id": "USR-007", "email": "grace.lee@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 30, "user_gender": "Female", "user_location": "Boston",
    },
    {
        "user_id": "USR-008", "email": "henry.brown@demo.com",
        "password_hash": _hash_password("password123"),
        "user_age": 41, "user_gender": "Male", "user_location": "Phoenix",
    },
]

# Return-window policy per category (days)
_RETURN_WINDOWS = {
    "Electronics": 30,
    "Clothing": 15,
    "Home": 30,
    "Books": 14,
    "Toys": 21,
    "Subscription": 7,
}

# Orders — mix of statuses, categories, dates, and edge cases
ORDERS = [
    # ── USR-001 (alice) ────────────────────────────────────────────────────
    {
        "order_id": "ORD-1001", "product_id": "PROD-WH500", "user_id": "USR-001",
        "order_date": _days_ago(10), "return_date": None,
        "product_category": "Electronics", "product_price": 249.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Credit Card", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    {
        "order_id": "ORD-1002", "product_id": "PROD-LS200", "user_id": "USR-001",
        "order_date": _days_ago(40),  # OUTSIDE 30-day window → Electronics
        "return_date": None,
        "product_category": "Electronics", "product_price": 79.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Credit Card", "shipping_method": "Express", "discount_applied": 10.0,
    },
    # ── USR-002 (bob) ──────────────────────────────────────────────────────
    {
        "order_id": "ORD-2001", "product_id": "PROD-CM300", "user_id": "USR-002",
        "order_date": _days_ago(5), "return_date": None,
        "product_category": "Home", "product_price": 129.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "PayPal", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    {
        "order_id": "ORD-2002", "product_id": "PROD-JKT10", "user_id": "USR-002",
        "order_date": _days_ago(20),  # OUTSIDE 15-day Clothing window
        "return_date": None,
        "product_category": "Clothing", "product_price": 59.99, "order_quantity": 2,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Debit Card", "shipping_method": "Standard", "discount_applied": 5.0,
    },
    # ── USR-003 (carol) ────────────────────────────────────────────────────
    {
        "order_id": "ORD-3001", "product_id": "PROD-SW450", "user_id": "USR-003",
        "order_date": _days_ago(3), "return_date": None,
        "product_category": "Electronics", "product_price": 199.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Credit Card", "shipping_method": "Next-Day", "discount_applied": 20.0,
    },
    {
        # Already refunded — duplicate attempt must be blocked
        "order_id": "ORD-3002", "product_id": "PROD-BK001", "user_id": "USR-003",
        "order_date": _days_ago(8), "return_date": _days_ago(2),
        "product_category": "Books", "product_price": 24.99, "order_quantity": 1,
        "return_reason": "Damaged in shipping", "return_status": "Refund Initiated",
        "days_to_return": 6,
        "payment_method": "PayPal", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    # ── USR-004 (david) ────────────────────────────────────────────────────
    {
        "order_id": "ORD-4001", "product_id": "PROD-TY200", "user_id": "USR-004",
        "order_date": _days_ago(15), "return_date": None,
        "product_category": "Toys", "product_price": 39.99, "order_quantity": 2,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Debit Card", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    {
        # Gift Card payment — non-refundable
        "order_id": "ORD-4002", "product_id": "PROD-CLT50", "user_id": "USR-004",
        "order_date": _days_ago(4), "return_date": None,
        "product_category": "Clothing", "product_price": 45.00, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Gift Card", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    # ── USR-005 (emma) ─────────────────────────────────────────────────────
    {
        "order_id": "ORD-5001", "product_id": "PROD-BS220", "user_id": "USR-005",
        "order_date": _days_ago(2), "return_date": None,
        "product_category": "Electronics", "product_price": 149.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Credit Card", "shipping_method": "Express", "discount_applied": 15.0,
    },
    {
        # Subscription — only 7-day window
        "order_id": "ORD-5002", "product_id": "PROD-SUB01", "user_id": "USR-005",
        "order_date": _days_ago(10),  # OUTSIDE 7-day Subscription window
        "return_date": None,
        "product_category": "Subscription", "product_price": 9.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "PayPal", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    # ── USR-006 (frank) ────────────────────────────────────────────────────
    {
        "order_id": "ORD-6001", "product_id": "PROD-MON4K", "user_id": "USR-006",
        "order_date": _days_ago(7), "return_date": None,
        "product_category": "Electronics", "product_price": 499.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Credit Card", "shipping_method": "Express", "discount_applied": 50.0,
    },
    {
        "order_id": "ORD-6002", "product_id": "PROD-BK020", "user_id": "USR-006",
        "order_date": _days_ago(12), "return_date": None,
        "product_category": "Books", "product_price": 19.99, "order_quantity": 3,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Debit Card", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    # ── USR-007 (grace) ────────────────────────────────────────────────────
    {
        "order_id": "ORD-7001", "product_id": "PROD-YM50", "user_id": "USR-007",
        "order_date": _days_ago(18), "return_date": None,
        "product_category": "Home", "product_price": 45.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "PayPal", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    {
        "order_id": "ORD-7002", "product_id": "PROD-CLT99", "user_id": "USR-007",
        "order_date": _days_ago(8),  # WITHIN 15-day Clothing window
        "return_date": None,
        "product_category": "Clothing", "product_price": 89.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Credit Card", "shipping_method": "Next-Day", "discount_applied": 10.0,
    },
    # ── USR-008 (henry) ────────────────────────────────────────────────────
    {
        "order_id": "ORD-8001", "product_id": "PROD-RS110", "user_id": "USR-008",
        "order_date": _days_ago(25), "return_date": None,
        "product_category": "Clothing", "product_price": 89.99, "order_quantity": 1,
        "return_reason": None, "return_status": "Not Returned", "days_to_return": None,
        "payment_method": "Debit Card", "shipping_method": "Standard", "discount_applied": 0.0,
    },
    {
        # Already fully returned
        "order_id": "ORD-8002", "product_id": "PROD-TY100", "user_id": "USR-008",
        "order_date": _days_ago(15), "return_date": _days_ago(5),
        "product_category": "Toys", "product_price": 29.99, "order_quantity": 1,
        "return_reason": "Wrong item", "return_status": "Returned",
        "days_to_return": 10,
        "payment_method": "PayPal", "shipping_method": "Standard", "discount_applied": 0.0,
    },
]


# ─── Schema ──────────────────────────────────────────────────────────────────

def create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       TEXT PRIMARY KEY,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            user_age      INTEGER,
            user_gender   TEXT,
            user_location TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            order_id         TEXT PRIMARY KEY,
            product_id       TEXT NOT NULL,
            user_id          TEXT NOT NULL,
            order_date       TEXT NOT NULL,          -- YYYY-MM-DD
            return_date      TEXT,                   -- YYYY-MM-DD or NULL
            product_category TEXT NOT NULL,          -- Electronics/Clothing/Home/Books/Toys/Subscription
            product_price    REAL NOT NULL,
            order_quantity   INTEGER NOT NULL DEFAULT 1,
            return_reason    TEXT,
            return_status    TEXT NOT NULL DEFAULT 'Not Returned',
                                                     -- 'Not Returned' | 'Refund Initiated' | 'Returned'
            days_to_return   INTEGER,                -- NULL until returned
            payment_method   TEXT NOT NULL,          -- Credit Card/Debit Card/PayPal/Gift Card
            shipping_method  TEXT NOT NULL,          -- Standard/Express/Next-Day
            discount_applied REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_user     ON orders(user_id);
        CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders(return_status);
        CREATE INDEX IF NOT EXISTS idx_users_email     ON users(email);
    """)
    conn.commit()


def seed(conn: sqlite3.Connection):
    conn.executemany(
        """INSERT OR IGNORE INTO users
           (user_id, email, password_hash, user_age, user_gender, user_location)
           VALUES (:user_id, :email, :password_hash, :user_age, :user_gender, :user_location)""",
        USERS,
    )
    conn.executemany(
        """INSERT OR IGNORE INTO orders
           (order_id, product_id, user_id, order_date, return_date,
            product_category, product_price, order_quantity,
            return_reason, return_status, days_to_return,
            payment_method, shipping_method, discount_applied)
           VALUES (:order_id, :product_id, :user_id, :order_date, :return_date,
                   :product_category, :product_price, :order_quantity,
                   :return_reason, :return_status, :days_to_return,
                   :payment_method, :shipping_method, :discount_applied)""",
        ORDERS,
    )
    conn.commit()


def setup(force: bool = False):
    if force and DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed old database: {DB_PATH}")

    print(f"Setting up database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    seed(conn)
    conn.close()

    # Verify
    conn = sqlite3.connect(DB_PATH)
    users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()
    print(f"  users : {users}")
    print(f"  orders: {orders}")
    print("Done.")
    print()
    print("Demo login credentials (all passwords: password123):")
    for u in USERS:
        print(f"  {u['email']}")


if __name__ == "__main__":
    import sys
    setup(force="--force" in sys.argv)