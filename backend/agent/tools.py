"""
agent/tools.py — All tool functions available to the refund support agent.

Tools
-----
1. get_refund_policy      — Return full policy text or a named section
2. get_my_orders          — List all orders for the authenticated user
3. lookup_order           — Fetch order details; enforces user ownership
4. get_current_date       — Return today's date (for window math transparency)
5. check_refund_eligibility — Full policy gate: window + duplicate + payment method
6. initiate_refund        — Write DB update + send confirmation email
"""
import json
from datetime import datetime
from langchain_core.tools import tool

from data.crm_database import (
    get_order,
    get_order_for_user,
    get_orders_for_user,
    get_return_window,
    is_already_refunded,
    is_payment_non_refundable,
    initiate_refund_in_db,
    get_user,
    RETURN_WINDOWS,
)
from data.refund_policy import REFUND_POLICY_TEXT, REFUND_POLICY_RULES
from services.email_service import send_refund_initiated_email


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: Get Refund Policy
# ─────────────────────────────────────────────────────────────────────────────
@tool
def get_refund_policy(section: str = "full") -> str:
    """
    Retrieve the ShopWave refund policy document or a specific section.
    Use section='full' for the complete policy.
    Use one of these section names for a focused excerpt:
      'return_windows'  — return windows by product category
      'non_refundable'  — non-refundable items and payment methods
      'duplicate'       — duplicate refund restriction rules
      'ownership'       — user ownership and security rules
      'process'         — step-by-step refund process
      'timeline'        — processing timelines by payment method
      'fraud'           — fraud prevention rules
    """
    if section == "full":
        return REFUND_POLICY_TEXT

    section_map = {
        "return_windows": "1. RETURN WINDOWS BY PRODUCT CATEGORY",
        "non_refundable": "3. NON-REFUNDABLE ITEMS",
        "duplicate":      "4. DUPLICATE REFUND RESTRICTION",
        "ownership":      "5. USER OWNERSHIP & SECURITY",
        "process":        "6. REFUND PROCESS",
        "timeline":       "7. PROCESSING TIMELINE BY PAYMENT METHOD",
        "fraud":          "10. FRAUD PREVENTION",
    }
    key = section_map.get(section.lower(), "")
    if not key:
        return REFUND_POLICY_TEXT

    lines = REFUND_POLICY_TEXT.split("\n")
    in_section = False
    result = []
    for line in lines:
        if key in line:
            in_section = True
        if in_section:
            result.append(line)
            # Stop at the next numbered section heading
            if len(result) > 1 and line.strip() and line[0].isdigit() and line != lines[lines.index(line)]:
                if len(result) > 5:
                    break
    return "\n".join(result) if result else REFUND_POLICY_TEXT


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2: Get My Orders
# ─────────────────────────────────────────────────────────────────────────────
@tool
def get_my_orders(user_id: str) -> str:
    """
    Retrieve all orders belonging to the authenticated user.
    Pass the user_id of the currently logged-in customer.
    Returns a list of orders with their IDs, categories, prices, and current status.
    """
    user_id = user_id.strip().upper()
    orders = get_orders_for_user(user_id)

    if not orders:
        return json.dumps({
            "status": "no_orders",
            "user_id": user_id,
            "message": "No orders found for this account.",
            "orders": [],
        })

    summary = []
    for o in orders:
        days_elapsed = (
            datetime.now() -
            datetime.strptime(o["order_date"], "%Y-%m-%d")
        ).days
        window = get_return_window(o["product_category"])
        summary.append({
            "order_id":         o["order_id"],
            "product_id":       o["product_id"],
            "product_category": o["product_category"],
            "product_price":    o["product_price"],
            "order_quantity":   o["order_quantity"],
            "order_date":       o["order_date"],
            "return_status":    o["return_status"],
            "payment_method":   o["payment_method"],
            "shipping_method":  o["shipping_method"],
            "discount_applied": o["discount_applied"],
            "days_since_order": days_elapsed,
            "return_window_days": window,
            "within_window":    days_elapsed <= window,
        })

    return json.dumps({
        "status": "found",
        "user_id": user_id,
        "total_orders": len(summary),
        "orders": summary,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3: Lookup Order
# ─────────────────────────────────────────────────────────────────────────────
@tool
def lookup_order(order_id: str, user_id: str) -> str:
    """
    Look up details for a specific order by order ID.
    IMPORTANT: Always pass the user_id of the currently logged-in customer.
    This tool enforces ownership — it will reject requests where the order
    does not belong to the authenticated user.

    Returns full order details including category, price, status, and
    how many days remain in the return window.
    """
    order_id = order_id.strip().upper()
    user_id  = user_id.strip().upper()

    # First check if the order exists at all
    order_any = get_order(order_id)
    if not order_any:
        return json.dumps({
            "status": "not_found",
            "message": f"Order '{order_id}' was not found in the system.",
        })

    # Ownership check
    order = get_order_for_user(order_id, user_id)
    if not order:
        return json.dumps({
            "status": "forbidden",
            "message": (
                f"Order '{order_id}' does not belong to your account. "
                "You can only view and request refunds for your own orders."
            ),
        })

    # Compute timing
    try:
        order_dt = datetime.strptime(order["order_date"], "%Y-%m-%d")
        days_elapsed = (datetime.now() - order_dt).days
    except Exception:
        days_elapsed = 0

    window = get_return_window(order["product_category"])
    days_remaining = max(0, window - days_elapsed)

    return json.dumps({
        "status":           "found",
        "order_id":         order["order_id"],
        "product_id":       order["product_id"],
        "user_id":          order["user_id"],
        "product_category": order["product_category"],
        "product_price":    order["product_price"],
        "order_quantity":   order["order_quantity"],
        "order_date":       order["order_date"],
        "return_date":      order["return_date"],
        "return_status":    order["return_status"],
        "return_reason":    order["return_reason"],
        "payment_method":   order["payment_method"],
        "shipping_method":  order["shipping_method"],
        "discount_applied": order["discount_applied"],
        "days_since_order": days_elapsed,
        "return_window_days": window,
        "days_remaining_in_window": days_remaining,
        "within_window":    days_elapsed <= window,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4: Get Current Date
# ─────────────────────────────────────────────────────────────────────────────
@tool
def get_current_date() -> str:
    """
    Return the current server date and time.
    Use this together with an order's order_date to show the customer
    exactly how many days have elapsed and whether the return window is open.
    """
    now = datetime.now()
    return json.dumps({
        "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_date":     now.strftime("%Y-%m-%d"),
        "current_time":     now.strftime("%H:%M:%S"),
        "day_of_week":      now.strftime("%A"),
        "return_windows_reference": RETURN_WINDOWS,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5: Check Refund Eligibility
# ─────────────────────────────────────────────────────────────────────────────
@tool
def check_refund_eligibility(order_id: str, user_id: str, reason: str) -> str:
    """
    Perform the full policy eligibility check for a refund request.
    Always call this before initiating a refund.

    Checks performed (in order):
      1. Ownership — order must belong to user_id
      2. Duplicate — order must not already be refunded
      3. Payment method — Gift Card orders are non-refundable
      4. Return window — based on product category
      5. Always-eligible reasons (defective, wrong item, etc.)

    Returns a structured eligibility report with the decision and reasons.
    """
    order_id = order_id.strip().upper()
    user_id  = user_id.strip().upper()
    reason_lower = reason.lower()

    # ── 0. Existence check ──────────────────────────────────────────────────
    order_any = get_order(order_id)
    if not order_any:
        return json.dumps({
            "eligible": False,
            "reason":   f"Order '{order_id}' was not found in the system.",
            "policy_section": "N/A",
        })

    # ── 1. Ownership check ──────────────────────────────────────────────────
    order = get_order_for_user(order_id, user_id)
    if not order:
        return json.dumps({
            "eligible": False,
            "reason": (
                f"Order '{order_id}' does not belong to your account. "
                "You may only request refunds for your own orders (Policy §5)."
            ),
            "policy_section": "§5 — User Ownership & Security",
        })

    # ── 2. Duplicate refund check ───────────────────────────────────────────
    if is_already_refunded(order):
        return json.dumps({
            "eligible": False,
            "reason": (
                f"Order '{order_id}' has already been refunded "
                f"(current status: '{order['return_status']}'). "
                "Each order can only be refunded once (Policy §4)."
            ),
            "policy_section": "§4 — Duplicate Refund Restriction",
            "current_status": order["return_status"],
        })

    # ── 3. Payment method check ─────────────────────────────────────────────
    if is_payment_non_refundable(order):
        return json.dumps({
            "eligible": False,
            "reason": (
                f"This order was paid with '{order['payment_method']}', "
                "which is non-refundable (Policy §3.1). "
                "Gift Card payments cannot be refunded. "
                "You may be eligible for store credit — please contact support."
            ),
            "policy_section": "§3.1 — Gift Card Non-Refundable",
            "payment_method": order["payment_method"],
        })

    # ── 4. Always-eligible reasons (bypass window check) ───────────────────
    always_eligible_keywords = [
        "defective", "malfunction", "broken", "damaged",
        "wrong item", "wrong product", "not received", "never arrived",
    ]
    is_always_eligible = any(kw in reason_lower for kw in always_eligible_keywords)

    # ── 5. Return window check ──────────────────────────────────────────────
    try:
        order_dt = datetime.strptime(order["order_date"], "%Y-%m-%d")
        days_elapsed = (datetime.now() - order_dt).days
    except Exception:
        days_elapsed = 0

    window = get_return_window(order["product_category"])
    within_window = days_elapsed <= window

    if not within_window and not is_always_eligible:
        deadline = (
            datetime.strptime(order["order_date"], "%Y-%m-%d").replace(
                day=datetime.strptime(order["order_date"], "%Y-%m-%d").day
            )
        )
        from datetime import timedelta
        deadline_str = (datetime.strptime(order["order_date"], "%Y-%m-%d") +
                        timedelta(days=window)).strftime("%Y-%m-%d")

        return json.dumps({
            "eligible": False,
            "reason": (
                f"The return window for {order['product_category']} items is {window} days. "
                f"Your order was placed on {order['order_date']}, which was {days_elapsed} days ago "
                f"(deadline was {deadline_str}). "
                "The return window has expired (Policy §1). "
                "Note: defective, damaged, or wrong items are always eligible regardless of window."
            ),
            "policy_section": f"§1 — Return Windows by Category ({order['product_category']}: {window} days)",
            "days_elapsed":   days_elapsed,
            "window_days":    window,
            "deadline":       deadline_str,
        })

    # ── Eligible ─────────────────────────────────────────────────────────────
    refund_amount = round(
        (order["product_price"] * order["order_quantity"]) - order["discount_applied"],
        2,
    )
    refund_amount = max(0.0, refund_amount)

    timeline = {
        "Credit Card": "5–10 business days",
        "Debit Card":  "3–5 business days",
        "PayPal":      "1–3 business days",
    }.get(order["payment_method"], "3–7 business days")

    eligibility_notes = []
    if is_always_eligible:
        eligibility_notes.append(
            f"✓ Reason '{reason}' qualifies as always-eligible (no window limit applies)"
        )
    else:
        eligibility_notes.append(
            f"✓ Within return window: {days_elapsed}/{window} days elapsed since order date"
        )

    return json.dumps({
        "eligible":           True,
        "order_id":           order["order_id"],
        "product_category":   order["product_category"],
        "order_date":         order["order_date"],
        "days_elapsed":       days_elapsed,
        "return_window_days": window,
        "within_window":      within_window,
        "always_eligible":    is_always_eligible,
        "refund_amount":      refund_amount,
        "payment_method":     order["payment_method"],
        "processing_timeline": timeline,
        "eligibility_notes":  eligibility_notes,
        "policy_reference":   "ShopWave Refund Policy v5.0",
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 6: Initiate Refund
# ─────────────────────────────────────────────────────────────────────────────
@tool
def initiate_refund(order_id: str, user_id: str, reason: str) -> str:
    """
    Initiate an approved refund for an order.
    ONLY call this tool after check_refund_eligibility returns eligible=True.

    This tool will:
      1. Verify ownership one final time
      2. Update the order's return_status to 'Refund Initiated' in the database
      3. Send a confirmation email to the customer
      4. Return a confirmation with the refund amount and processing timeline

    Arguments:
      order_id — the order to refund
      user_id  — the logged-in user's ID (must match the order's user_id)
      reason   — the customer's stated reason for the return
    """
    order_id = order_id.strip().upper()
    user_id  = user_id.strip().upper()

    # Final ownership + existence check
    order = get_order_for_user(order_id, user_id)
    if not order:
        order_any = get_order(order_id)
        if not order_any:
            return json.dumps({
                "status":  "error",
                "message": f"Order '{order_id}' not found.",
            })
        return json.dumps({
            "status":  "forbidden",
            "message": f"Order '{order_id}' does not belong to your account.",
        })

    # Final duplicate guard
    if is_already_refunded(order):
        return json.dumps({
            "status":  "duplicate",
            "message": (
                f"Order '{order_id}' already has status '{order['return_status']}'. "
                "Cannot initiate a duplicate refund."
            ),
        })

    # Write to DB
    success = initiate_refund_in_db(order_id, reason)
    if not success:
        return json.dumps({
            "status":  "error",
            "message": f"Failed to update database for order '{order_id}'.",
        })

    # Compute refund amount
    refund_amount = round(
        (order["product_price"] * order["order_quantity"]) - order["discount_applied"],
        2,
    )
    refund_amount = max(0.0, refund_amount)

    # Send confirmation email
    user = get_user(user_id)
    user_email = user["email"] if user else None
    email_sent = False
    if user_email:
        email_sent = send_refund_initiated_email(
            to_email=user_email,
            order_id=order_id,
            product_category=order["product_category"],
            product_price=order["product_price"],
            order_quantity=order["order_quantity"],
            discount_applied=order["discount_applied"],
            payment_method=order["payment_method"],
            reason=reason,
        )

    timeline = {
        "Credit Card": "5–10 business days",
        "Debit Card":  "3–5 business days",
        "PayPal":      "1–3 business days",
    }.get(order["payment_method"], "3–7 business days")

    return json.dumps({
        "status":              "refund_initiated",
        "order_id":            order_id,
        "user_id":             user_id,
        "product_category":    order["product_category"],
        "refund_amount":       refund_amount,
        "payment_method":      order["payment_method"],
        "processing_timeline": timeline,
        "reason":              reason,
        "email_sent":          email_sent,
        "email_address":       user_email,
        "message": (
            f"✅ Refund of ${refund_amount:.2f} has been initiated for order {order_id}. "
            f"You will receive a confirmation at {user_email}. "
            f"Please allow {timeline} for the refund to appear."
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────────────────────
ALL_TOOLS = [
    get_refund_policy,
    get_my_orders,
    lookup_order,
    get_current_date,
    check_refund_eligibility,
    initiate_refund,
]
