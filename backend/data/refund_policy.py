"""
refund_policy.py — Category-based refund rules + policy text loader.

RETURN_WINDOWS is imported from crm_database to ensure a single source of truth.
"""
from pathlib import Path

from data.crm_database import RETURN_WINDOWS, NON_REFUNDABLE_PAYMENT_METHODS

# ── Load policy text from the canonical plain-text file ──────────────────────
_POLICY_FILE = Path(__file__).parent / "refund_policy.txt"
REFUND_POLICY_TEXT = _POLICY_FILE.read_text(encoding="utf-8")


# ── Structured policy rules (used by the agent programmatically) ──────────────
REFUND_POLICY_RULES = {
    # Category-based return windows (days from order_date)
    "return_windows_by_category": RETURN_WINDOWS,

    # Payment methods that are entirely non-refundable
    "non_refundable_payment_methods": list(NON_REFUNDABLE_PAYMENT_METHODS),

    # Conditions that are ALWAYS eligible regardless of return window
    "always_eligible_reasons": [
        "defective",
        "damaged in shipping",
        "wrong item",
        "not received",
    ],

    # Conditions that are never eligible
    "non_refundable_item_types": [
        "personalized or custom-made items (unless defective)",
        "perishable goods",
        "final sale items",
        "digital goods after download",
        "subscriptions after first use",
    ],

    # Duplicate refund restriction
    "duplicate_refund_allowed": False,
    "already_refunded_statuses": ["Refund Initiated", "Returned"],

    # Fraud signal: flag if more than this many refunds in rolling window
    "fraud_window_days": 90,
    "fraud_refund_count_threshold": 3,

    # Ownership: order must belong to the requesting user
    "ownership_enforcement": True,
}
