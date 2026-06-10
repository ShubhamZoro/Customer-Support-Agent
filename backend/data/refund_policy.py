"""
Strict Refund Policy Document
"""

REFUND_POLICY_TEXT = """
=============================================================
  SHOPWAVE E-COMMERCE — OFFICIAL REFUND & RETURN POLICY
  Version 3.2 | Effective Date: January 1, 2025
=============================================================

1. RETURN WINDOWS
-----------------
1.1 Standard Members (Bronze/Silver): 30 days from delivery date.
1.2 Premium Members (Gold): 45 days from delivery date.
1.3 Elite Members (Platinum): 60 days from delivery date.
1.4 The return window begins on the confirmed delivery date, not the purchase date.

2. ELIGIBLE CONDITIONS FOR RETURN
----------------------------------
2.1 Defective or malfunctioning items — ALWAYS eligible regardless of return window.
2.2 Items damaged during shipping — eligible if reported within 72 hours of delivery.
2.3 Wrong item received (not what was ordered) — always eligible.
2.4 Item significantly not as described in the product listing — eligible within return window.
2.5 Unopened/unused items in original packaging — eligible within return window.

3. NON-REFUNDABLE ITEMS (ABSOLUTE RESTRICTIONS)
-------------------------------------------------
3.1 Digital goods (e-books, software licenses, digital gift cards, streaming subscriptions) — NO REFUNDS under any circumstance.
3.2 Personalized or custom-made items — NO REFUNDS unless defective.
3.3 Perishable goods (food, flowers, plants) — NO REFUNDS.
3.4 Intimate apparel and swimwear (hygiene reasons) — NO REFUNDS unless defective.
3.5 Hazardous materials and flammable items — NO REFUNDS.
3.6 Items marked as "Final Sale" or "Non-Returnable" at time of purchase — NO REFUNDS.

4. REFUND LIMITS PER CUSTOMER
-------------------------------
4.1 Maximum 3 refunds per calendar year per customer account.
4.2 Maximum single refund amount: $500.00 USD.
4.3 Customers who have exceeded limits must be escalated to supervisor review.
4.4 Refund history resets on January 1 each calendar year.

5. SHIPPING CHARGES
--------------------
5.1 Original shipping charges are NON-REFUNDABLE unless:
    (a) The return is due to our error (wrong item, defective), OR
    (b) The customer is Platinum tier.
5.2 Return shipping is the customer's responsibility unless we made an error.
5.3 Free shipping orders: no shipping refund applicable.

6. FRAUD PREVENTION & SUSPICIOUS ACTIVITY
-------------------------------------------
6.1 Customers with MORE THAN 2 refund requests within any 90-day rolling window are flagged for MANUAL REVIEW — do NOT auto-approve.
6.2 Customers with a pattern of "item not received" claims on delivered orders require supervisor review.
6.3 New accounts (less than 60 days old) requesting refunds over $200 require additional verification.
6.4 Any single refund exceeding $400 requires supervisor approval regardless of tier.

7. PROCESSING TIMELINE
-----------------------
7.1 Approved refunds are processed within 3-5 business days.
7.2 Credit card refunds: 5-10 business days to appear on statement.
7.3 PayPal refunds: 1-3 business days.
7.4 Gift card refunds: credited back to original gift card.
7.5 Cash refunds for debit card purchases: 3-5 business days.

8. PARTIAL REFUNDS
-------------------
8.1 Items returned in used/opened condition (when originally in good condition) may receive only a partial refund (50-75% of purchase price) at agent discretion.
8.2 Sets or bundles: refund only for the returned items within the bundle.
8.3 Items with missing accessories or packaging: 25% deduction.

9. ESCALATION TRIGGERS
------------------------
9.1 Refund amount exceeds $400.
9.2 Customer has 3 or more refunds in the past 90 days.
9.3 Account age less than 60 days with order value over $200.
9.4 Customer disputes the policy and escalation is requested.
9.5 Evidence of fraudulent activity or abuse.

10. AGENT AUTHORITY & DISCRETION
----------------------------------
10.1 Agents may use discretion for loyal Platinum/Gold members within policy limits.
10.2 Goodwill gestures (loyalty points, small credits) can be offered when a refund is denied but the customer has a good standing.
10.3 Agents CANNOT override the non-refundable items list (Section 3).
10.4 Agents CANNOT approve refunds exceeding $500 without supervisor sign-off.
=============================================================
"""


REFUND_POLICY_RULES = {
    "return_windows": {
        "bronze": 30,
        "silver": 30,
        "gold": 45,
        "platinum": 60,
    },
    "max_refunds_per_year": 3,
    "max_single_refund_amount": 500.00,
    "escalation_threshold_amount": 400.00,
    "fraud_window_days": 90,
    "fraud_refund_count_threshold": 2,
    "new_account_days": 60,
    "new_account_high_value_threshold": 200.00,
    "non_refundable_categories": [
        "digital_goods",
        "personalized_items",
        "perishables",
        "intimate_apparel",
        "hazardous_materials",
        "final_sale",
    ],
    "always_eligible_reasons": [
        "defective",
        "damaged_in_shipping",
        "wrong_item",
    ],
    "shipping_refund_eligible_for_platinum": True,
    "shipping_refund_for_company_error": True,
}
