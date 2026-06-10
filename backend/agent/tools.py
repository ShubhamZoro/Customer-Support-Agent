"""
LangGraph Agent Tools — All tool functions the agent can call
"""
import json
from datetime import datetime, timedelta
from langchain_core.tools import tool

from data.crm_database import (
    get_customer, get_order,
    search_customer_by_email, search_customer_by_name
)
from data.refund_policy import REFUND_POLICY_RULES, REFUND_POLICY_TEXT


# ─── In-memory store for approved/denied refunds (demo) ─────────────────────
PROCESSED_REFUNDS: list[dict] = []


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: Lookup Customer
# ─────────────────────────────────────────────────────────────────────────────
@tool
def lookup_customer(query: str) -> str:
    """
    Look up a customer from the CRM database.
    Accepts a customer ID (e.g. 'CUST-001'), email address, or partial name.
    Returns full customer profile including tier, account age, and order IDs.
    """
    query = query.strip()
    customer = None

    # Try by customer ID
    if query.upper().startswith("CUST-"):
        customer = get_customer(query)
    # Try by email
    elif "@" in query:
        customer = search_customer_by_email(query)
    # Try by name
    else:
        results = search_customer_by_name(query)
        if len(results) == 1:
            customer = results[0]
        elif len(results) > 1:
            names = [f"{c['customer_id']} - {c['name']}" for c in results]
            return json.dumps({
                "status": "multiple_found",
                "message": "Multiple customers found. Please specify:",
                "customers": names
            })

    if not customer:
        return json.dumps({
            "status": "not_found",
            "message": f"No customer found for query: '{query}'"
        })

    # Return a clean profile summary
    order_ids = list(customer["orders"].keys())
    return json.dumps({
        "status": "found",
        "customer_id": customer["customer_id"],
        "name": customer["name"],
        "email": customer["email"],
        "tier": customer["tier"],
        "account_age_days": customer["account_age_days"],
        "loyalty_points": customer["loyalty_points"],
        "total_refunds_this_year": customer["total_refunds_this_year"],
        "total_refund_amount_this_year": customer["total_refund_amount_this_year"],
        "order_ids": order_ids,
        "refund_history_count": len(customer["refund_history"]),
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2: Lookup Order
# ─────────────────────────────────────────────────────────────────────────────
@tool
def lookup_order(order_id: str) -> str:
    """
    Look up details for a specific order by order ID.
    Returns order date, items, total amount, status, and shipping cost.
    """
    order_id = order_id.strip().upper()
    order, customer_id = get_order(order_id)

    if not order:
        return json.dumps({
            "status": "not_found",
            "message": f"Order '{order_id}' not found in the system."
        })

    # Calculate days since delivery
    try:
        order_date = datetime.strptime(order["date"], "%Y-%m-%d")
        days_since_order = (datetime.now() - order_date).days
    except Exception:
        days_since_order = None

    result = {
        "status": "found",
        "order_id": order["order_id"],
        "customer_id": customer_id,
        "order_date": order["date"],
        "days_since_order": days_since_order,
        "items": order["items"],
        "total": order["total"],
        "order_status": order["status"],
        "payment_method": order["payment_method"],
        "shipping_cost": order["shipping_cost"],
        "is_digital": order.get("is_digital", False),
        "has_personalized_items": any(
            item.get("is_personalized", False) for item in order["items"]
        ),
    }
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3: Check Refund Eligibility
# ─────────────────────────────────────────────────────────────────────────────
@tool
def check_refund_eligibility(customer_id: str, order_id: str, reason: str) -> str:
    """
    Check whether a refund request is eligible under the refund policy.
    Provide the customer_id, order_id, and the reason for the refund request.
    Returns a detailed eligibility report with policy rule citations.
    """
    policy = REFUND_POLICY_RULES
    issues = []
    eligibility_flags = []

    customer = get_customer(customer_id.strip().upper())
    if not customer:
        return json.dumps({"eligible": False, "reason": "Customer not found."})

    order, _ = get_order(order_id.strip().upper())
    if not order:
        return json.dumps({"eligible": False, "reason": "Order not found."})

    tier = customer["tier"].lower()
    reason_lower = reason.lower()

    # ── 1. Return Window Check ──────────────────────────────────────────────
    window_days = policy["return_windows"].get(tier, 30)
    try:
        order_date = datetime.strptime(order["date"], "%Y-%m-%d")
        days_elapsed = (datetime.now() - order_date).days
    except Exception:
        days_elapsed = 0

    always_eligible_reasons = ["defective", "damaged", "wrong item", "wrong_item",
                               "damaged_in_shipping", "not received"]
    is_always_eligible = any(r in reason_lower for r in always_eligible_reasons)

    if days_elapsed > window_days and not is_always_eligible:
        issues.append(
            f"POLICY §1: Return window expired. {tier.capitalize()} tier has {window_days} days; "
            f"{days_elapsed} days have passed since order date."
        )
    else:
        eligibility_flags.append(f"✓ Within return window ({days_elapsed}/{window_days} days)")

    # ── 2. Non-Refundable Items Check ───────────────────────────────────────
    if order.get("is_digital", False):
        issues.append("POLICY §3.1: Order contains digital goods — non-refundable under all circumstances.")

    if order.get("has_personalized_items") or any(
        item.get("is_personalized", False) for item in order.get("items", [])
    ):
        if not is_always_eligible:
            issues.append("POLICY §3.2: Order contains personalized items — non-refundable unless defective.")
        else:
            eligibility_flags.append("✓ Personalized item eligible due to defect claim")

    # ── 3. Annual Refund Limit ──────────────────────────────────────────────
    refunds_this_year = customer["total_refunds_this_year"]
    max_per_year = policy["max_refunds_per_year"]
    if refunds_this_year >= max_per_year:
        issues.append(
            f"POLICY §4.1: Annual refund limit reached. Customer has {refunds_this_year}/{max_per_year} refunds this year."
        )
    else:
        eligibility_flags.append(f"✓ Within annual limit ({refunds_this_year}/{max_per_year} refunds this year)")

    # ── 4. Amount Limit Check ───────────────────────────────────────────────
    order_amount = order["total"]
    max_amount = policy["max_single_refund_amount"]
    escalation_threshold = policy["escalation_threshold_amount"]

    needs_escalation = False
    if order_amount > max_amount:
        issues.append(
            f"POLICY §4.2: Order total ${order_amount} exceeds max refund amount ${max_amount}. "
            f"Maximum refundable: ${max_amount}."
        )
    elif order_amount > escalation_threshold:
        needs_escalation = True
        eligibility_flags.append(
            f"⚠ Amount ${order_amount} exceeds ${escalation_threshold} — requires supervisor approval (POLICY §9.1)"
        )
    else:
        eligibility_flags.append(f"✓ Amount ${order_amount} within refund limits")

    # ── 5. Fraud Signal Check ───────────────────────────────────────────────
    fraud_window = policy["fraud_window_days"]
    fraud_threshold = policy["fraud_refund_count_threshold"]

    recent_refunds = [
        r for r in customer["refund_history"]
        if (datetime.now() - datetime.strptime(r["date"], "%Y-%m-%d")).days <= fraud_window
    ]
    if len(recent_refunds) >= fraud_threshold:
        needs_escalation = True
        issues.append(
            f"POLICY §6.1: Fraud signal detected — {len(recent_refunds)} refunds in the past {fraud_window} days "
            f"(threshold: {fraud_threshold}). Requires manual review."
        )

    # ── 6. New Account + High Value Check ───────────────────────────────────
    new_acct_days = policy["new_account_days"]
    high_value = policy["new_account_high_value_threshold"]
    if customer["account_age_days"] < new_acct_days and order_amount > high_value:
        needs_escalation = True
        issues.append(
            f"POLICY §6.3: New account ({customer['account_age_days']} days old) requesting "
            f"refund over ${high_value} (${order_amount}) — requires additional verification."
        )

    # ── 7. Shipping Refund Eligibility ──────────────────────────────────────
    shipping_cost = order["shipping_cost"]
    shipping_refundable = (
        tier == "platinum"
        or is_always_eligible
        and shipping_cost > 0
    )

    # ── Final Determination ─────────────────────────────────────────────────
    is_eligible = len(issues) == 0
    refund_amount = min(order_amount, max_amount)
    if shipping_refundable and shipping_cost > 0:
        refund_amount += shipping_cost

    return json.dumps({
        "eligible": is_eligible,
        "needs_escalation": needs_escalation,
        "customer_tier": tier,
        "days_since_order": days_elapsed,
        "return_window_days": window_days,
        "order_amount": order_amount,
        "recommended_refund_amount": round(refund_amount, 2) if is_eligible else 0.0,
        "shipping_refundable": shipping_refundable,
        "eligibility_flags": eligibility_flags,
        "issues": issues,
        "policy_reference": "ShopWave Refund Policy v3.2",
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4: Get Refund History
# ─────────────────────────────────────────────────────────────────────────────
@tool
def get_refund_history(customer_id: str) -> str:
    """
    Retrieve the complete refund history for a customer.
    Useful for detecting refund patterns, fraud signals, or checking annual limits.
    """
    customer = get_customer(customer_id.strip().upper())
    if not customer:
        return json.dumps({"status": "not_found", "message": "Customer not found."})

    history = customer["refund_history"]
    now = datetime.now()

    # Calculate refunds in last 90 days
    recent_90 = [
        r for r in history
        if (now - datetime.strptime(r["date"], "%Y-%m-%d")).days <= 90
    ]

    return json.dumps({
        "status": "found",
        "customer_id": customer_id,
        "total_refunds_all_time": len(history),
        "total_refunds_this_year": customer["total_refunds_this_year"],
        "total_refund_amount_this_year": customer["total_refund_amount_this_year"],
        "refunds_last_90_days": len(recent_90),
        "fraud_flag": len(recent_90) >= REFUND_POLICY_RULES["fraud_refund_count_threshold"],
        "refund_history": history,
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5: Approve Refund
# ─────────────────────────────────────────────────────────────────────────────
@tool
def approve_refund(order_id: str, amount: float, reason: str) -> str:
    """
    Approve and process a refund for an order.
    Only call this after verifying eligibility with check_refund_eligibility.
    Provide the order_id, refund amount, and a brief reason for approval.
    """
    order, customer_id = get_order(order_id.strip().upper())
    if not order:
        return json.dumps({"status": "error", "message": f"Order {order_id} not found."})

    customer = get_customer(customer_id)
    payment_method = order["payment_method"]

    timeline = {
        "credit_card": "5-10 business days",
        "debit_card": "3-5 business days",
        "paypal": "1-3 business days",
        "gift_card": "Credited back to gift card immediately",
    }.get(payment_method, "3-7 business days")

    refund_record = {
        "refund_id": f"REF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_id": order_id,
        "customer_id": customer_id,
        "customer_name": customer["name"] if customer else "Unknown",
        "amount": round(amount, 2),
        "reason": reason,
        "status": "approved",
        "processed_at": datetime.now().isoformat(),
        "timeline": timeline,
        "payment_method": payment_method,
    }
    PROCESSED_REFUNDS.append(refund_record)

    return json.dumps({
        "status": "approved",
        "refund_id": refund_record["refund_id"],
        "order_id": order_id,
        "amount": round(amount, 2),
        "payment_method": payment_method,
        "processing_timeline": timeline,
        "message": f"Refund of ${amount:.2f} approved successfully for order {order_id}.",
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 6: Deny Refund
# ─────────────────────────────────────────────────────────────────────────────
@tool
def deny_refund(order_id: str, reason: str, policy_section: str) -> str:
    """
    Formally deny a refund request with a specific policy-based reason.
    Provide order_id, a clear reason for denial, and the relevant policy section.
    """
    order, customer_id = get_order(order_id.strip().upper())
    if not order:
        return json.dumps({"status": "error", "message": f"Order {order_id} not found."})

    customer = get_customer(customer_id) if customer_id else None

    denial_record = {
        "refund_id": f"DENIAL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_id": order_id,
        "customer_id": customer_id,
        "customer_name": customer["name"] if customer else "Unknown",
        "reason": reason,
        "policy_section": policy_section,
        "status": "denied",
        "processed_at": datetime.now().isoformat(),
    }
    PROCESSED_REFUNDS.append(denial_record)

    return json.dumps({
        "status": "denied",
        "order_id": order_id,
        "reason": reason,
        "policy_section": policy_section,
        "message": f"Refund for order {order_id} has been denied.",
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 7: Escalate to Human
# ─────────────────────────────────────────────────────────────────────────────
@tool
def escalate_to_human(customer_id: str, order_id: str, reason: str) -> str:
    """
    Escalate this refund case to a human supervisor for manual review.
    Use when: refund > $400, fraud signals detected, new account high-value order,
    customer disputes decision, or other complex circumstances.
    """
    escalation_record = {
        "escalation_id": f"ESC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "customer_id": customer_id,
        "order_id": order_id,
        "reason": reason,
        "status": "escalated",
        "escalated_at": datetime.now().isoformat(),
        "priority": "high" if "fraud" in reason.lower() else "normal",
    }
    PROCESSED_REFUNDS.append(escalation_record)

    return json.dumps({
        "status": "escalated",
        "escalation_id": escalation_record["escalation_id"],
        "customer_id": customer_id,
        "order_id": order_id,
        "reason": reason,
        "expected_response": "24-48 business hours",
        "message": (
            f"Case escalated to supervisor review. "
            f"Reference: {escalation_record['escalation_id']}. "
            f"A supervisor will contact the customer within 24-48 hours."
        ),
    })


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 8: Get Refund Policy
# ─────────────────────────────────────────────────────────────────────────────
@tool
def get_refund_policy(section: str = "full") -> str:
    """
    Retrieve the full refund policy document or a specific section.
    Use 'full' for the complete policy, or specify a topic like 'return_windows',
    'non_refundable', 'limits', 'fraud', 'escalation'.
    """
    if section == "full":
        return REFUND_POLICY_TEXT

    section_map = {
        "return_windows": "SECTION 1",
        "non_refundable": "SECTION 3",
        "limits": "SECTION 4",
        "fraud": "SECTION 6",
        "escalation": "SECTION 9",
    }
    key = section_map.get(section.lower(), "SECTION 1")
    lines = REFUND_POLICY_TEXT.split("\n")
    in_section = False
    result = []
    for line in lines:
        if key in line:
            in_section = True
        if in_section:
            result.append(line)
            if len(result) > 20:
                break
    return "\n".join(result) if result else REFUND_POLICY_TEXT


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry
# ─────────────────────────────────────────────────────────────────────────────
ALL_TOOLS = [
    lookup_customer,
    lookup_order,
    check_refund_eligibility,
    get_refund_history,
    approve_refund,
    deny_refund,
    escalate_to_human,
    get_refund_policy,
]
