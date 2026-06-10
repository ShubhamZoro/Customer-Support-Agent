"""
Mock CRM Database — 15 Customer Profiles
"""
from datetime import datetime, timedelta

def _days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")

CRM_DATABASE = {
    "CUST-001": {
        "customer_id": "CUST-001",
        "name": "Alice Johnson",
        "email": "alice.johnson@email.com",
        "phone": "+1-555-0101",
        "tier": "platinum",
        "account_age_days": 1825,
        "loyalty_points": 12500,
        "address": "123 Oak Street, Austin, TX 78701",
        "refund_history": [
            {"refund_id": "REF-001", "order_id": "ORD-001A", "amount": 89.99, "date": _days_ago(200), "reason": "Defective product", "status": "approved"},
        ],
        "total_refunds_this_year": 1,
        "total_refund_amount_this_year": 89.99,
        "orders": {
            "ORD-1001": {
                "order_id": "ORD-1001",
                "date": _days_ago(10),
                "items": [{"name": "Wireless Headphones", "sku": "WH-500", "qty": 1, "price": 249.99}],
                "total": 249.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
            "ORD-1002": {
                "order_id": "ORD-1002",
                "date": _days_ago(55),
                "items": [{"name": "Laptop Stand", "sku": "LS-200", "qty": 1, "price": 79.99}],
                "total": 79.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 5.99,
            },
        },
    },

    "CUST-002": {
        "customer_id": "CUST-002",
        "name": "Bob Martinez",
        "email": "bob.martinez@email.com",
        "phone": "+1-555-0102",
        "tier": "gold",
        "account_age_days": 730,
        "loyalty_points": 4800,
        "address": "456 Pine Ave, Denver, CO 80201",
        "refund_history": [],
        "total_refunds_this_year": 0,
        "total_refund_amount_this_year": 0.0,
        "orders": {
            "ORD-2001": {
                "order_id": "ORD-2001",
                "date": _days_ago(5),
                "items": [
                    {"name": "Coffee Maker", "sku": "CM-300", "qty": 1, "price": 129.99},
                    {"name": "Coffee Beans 1kg", "sku": "CB-100", "qty": 2, "price": 24.99},
                ],
                "total": 179.97,
                "status": "delivered",
                "payment_method": "paypal",
                "shipping_cost": 0.0,
            },
        },
    },

    "CUST-003": {
        "customer_id": "CUST-003",
        "name": "Carol White",
        "email": "carol.white@email.com",
        "phone": "+1-555-0103",
        "tier": "silver",
        "account_age_days": 365,
        "loyalty_points": 1200,
        "address": "789 Maple Dr, Seattle, WA 98101",
        "refund_history": [
            {"refund_id": "REF-010", "order_id": "ORD-3000A", "amount": 45.00, "date": _days_ago(30), "reason": "Wrong item", "status": "approved"},
            {"refund_id": "REF-011", "order_id": "ORD-3000B", "amount": 120.00, "date": _days_ago(15), "reason": "Damaged in shipping", "status": "approved"},
        ],
        "total_refunds_this_year": 2,
        "total_refund_amount_this_year": 165.00,
        "orders": {
            "ORD-3001": {
                "order_id": "ORD-3001",
                "date": _days_ago(3),
                "items": [{"name": "Smart Watch", "sku": "SW-450", "qty": 1, "price": 199.99}],
                "total": 199.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 9.99,
            },
        },
    },

    "CUST-004": {
        "customer_id": "CUST-004",
        "name": "David Chen",
        "email": "david.chen@email.com",
        "phone": "+1-555-0104",
        "tier": "bronze",
        "account_age_days": 90,
        "loyalty_points": 300,
        "address": "321 Elm St, Chicago, IL 60601",
        "refund_history": [],
        "total_refunds_this_year": 0,
        "total_refund_amount_this_year": 0.0,
        "orders": {
            "ORD-4001": {
                "order_id": "ORD-4001",
                "date": _days_ago(45),
                "items": [{"name": "USB-C Hub", "sku": "UC-110", "qty": 1, "price": 59.99}],
                "total": 59.99,
                "status": "delivered",
                "payment_method": "debit_card",
                "shipping_cost": 5.99,
            },
        },
    },

    "CUST-005": {
        "customer_id": "CUST-005",
        "name": "Emma Davis",
        "email": "emma.davis@email.com",
        "phone": "+1-555-0105",
        "tier": "gold",
        "account_age_days": 540,
        "loyalty_points": 6700,
        "address": "654 Cedar Ln, Miami, FL 33101",
        "refund_history": [
            {"refund_id": "REF-020", "order_id": "ORD-5000A", "amount": 350.00, "date": _days_ago(20), "reason": "Not as described", "status": "approved"},
            {"refund_id": "REF-021", "order_id": "ORD-5000B", "amount": 180.00, "date": _days_ago(10), "reason": "Changed mind", "status": "approved"},
            {"refund_id": "REF-022", "order_id": "ORD-5000C", "amount": 95.00, "date": _days_ago(5), "reason": "Duplicate order", "status": "pending"},
        ],
        "total_refunds_this_year": 3,
        "total_refund_amount_this_year": 625.00,
        "orders": {
            "ORD-5001": {
                "order_id": "ORD-5001",
                "date": _days_ago(2),
                "items": [{"name": "Bluetooth Speaker", "sku": "BS-220", "qty": 1, "price": 149.99}],
                "total": 149.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
        },
    },

    "CUST-006": {
        "customer_id": "CUST-006",
        "name": "Frank Wilson",
        "email": "frank.wilson@email.com",
        "phone": "+1-555-0106",
        "tier": "platinum",
        "account_age_days": 2190,
        "loyalty_points": 25000,
        "address": "987 Birch Rd, Portland, OR 97201",
        "refund_history": [],
        "total_refunds_this_year": 0,
        "total_refund_amount_this_year": 0.0,
        "orders": {
            "ORD-6001": {
                "order_id": "ORD-6001",
                "date": _days_ago(7),
                "items": [
                    {"name": "4K Monitor", "sku": "MON-4K", "qty": 1, "price": 499.99},
                    {"name": "Monitor Stand", "sku": "MS-100", "qty": 1, "price": 49.99},
                ],
                "total": 549.98,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
            "ORD-6002": {
                "order_id": "ORD-6002",
                "date": _days_ago(70),
                "items": [{"name": "Mechanical Keyboard", "sku": "MK-700", "qty": 1, "price": 189.99}],
                "total": 189.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
        },
    },

    "CUST-007": {
        "customer_id": "CUST-007",
        "name": "Grace Lee",
        "email": "grace.lee@email.com",
        "phone": "+1-555-0107",
        "tier": "silver",
        "account_age_days": 280,
        "loyalty_points": 2100,
        "address": "147 Willow Way, Boston, MA 02101",
        "refund_history": [
            {"refund_id": "REF-030", "order_id": "ORD-7000A", "amount": 75.00, "date": _days_ago(180), "reason": "Defective", "status": "approved"},
        ],
        "total_refunds_this_year": 1,
        "total_refund_amount_this_year": 75.00,
        "orders": {
            "ORD-7001": {
                "order_id": "ORD-7001",
                "date": _days_ago(35),
                "items": [{"name": "Yoga Mat", "sku": "YM-50", "qty": 1, "price": 45.99}],
                "total": 45.99,
                "status": "delivered",
                "payment_method": "paypal",
                "shipping_cost": 6.99,
            },
        },
    },

    "CUST-008": {
        "customer_id": "CUST-008",
        "name": "Henry Brown",
        "email": "henry.brown@email.com",
        "phone": "+1-555-0108",
        "tier": "bronze",
        "account_age_days": 45,
        "loyalty_points": 120,
        "address": "258 Spruce St, Phoenix, AZ 85001",
        "refund_history": [],
        "total_refunds_this_year": 0,
        "total_refund_amount_this_year": 0.0,
        "orders": {
            "ORD-8001": {
                "order_id": "ORD-8001",
                "date": _days_ago(50),
                "items": [{"name": "Running Shoes", "sku": "RS-110", "qty": 1, "price": 89.99}],
                "total": 89.99,
                "status": "delivered",
                "payment_method": "debit_card",
                "shipping_cost": 7.99,
            },
        },
    },

    "CUST-009": {
        "customer_id": "CUST-009",
        "name": "Isabella Taylor",
        "email": "isabella.taylor@email.com",
        "phone": "+1-555-0109",
        "tier": "gold",
        "account_age_days": 900,
        "loyalty_points": 8900,
        "address": "369 Ash Ave, Nashville, TN 37201",
        "refund_history": [
            {"refund_id": "REF-040", "order_id": "ORD-9000A", "amount": 200.00, "date": _days_ago(100), "reason": "Not satisfied", "status": "approved"},
        ],
        "total_refunds_this_year": 1,
        "total_refund_amount_this_year": 200.00,
        "orders": {
            "ORD-9001": {
                "order_id": "ORD-9001",
                "date": _days_ago(20),
                "items": [{"name": "Air Purifier", "sku": "AP-300", "qty": 1, "price": 299.99}],
                "total": 299.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
        },
    },

    "CUST-010": {
        "customer_id": "CUST-010",
        "name": "James Anderson",
        "email": "james.anderson@email.com",
        "phone": "+1-555-0110",
        "tier": "bronze",
        "account_age_days": 120,
        "loyalty_points": 450,
        "address": "741 Oak Blvd, Las Vegas, NV 89101",
        "refund_history": [],
        "total_refunds_this_year": 0,
        "total_refund_amount_this_year": 0.0,
        "orders": {
            "ORD-10001": {
                "order_id": "ORD-10001",
                "date": _days_ago(40),
                "items": [
                    {"name": "Phone Case", "sku": "PC-15", "qty": 1, "price": 19.99},
                    {"name": "Screen Protector", "sku": "SP-15", "qty": 2, "price": 9.99},
                ],
                "total": 39.97,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 4.99,
            },
        },
    },

    "CUST-011": {
        "customer_id": "CUST-011",
        "name": "Karen Thomas",
        "email": "karen.thomas@email.com",
        "phone": "+1-555-0111",
        "tier": "silver",
        "account_age_days": 420,
        "loyalty_points": 3300,
        "address": "852 Fir Lane, Minneapolis, MN 55401",
        "refund_history": [
            {"refund_id": "REF-050", "order_id": "ORD-11000A", "amount": 55.00, "date": _days_ago(60), "reason": "Arrived late", "status": "approved"},
        ],
        "total_refunds_this_year": 1,
        "total_refund_amount_this_year": 55.00,
        "orders": {
            "ORD-11001": {
                "order_id": "ORD-11001",
                "date": _days_ago(8),
                "items": [{"name": "Digital Gift Card", "sku": "DGC-50", "qty": 1, "price": 50.00}],
                "total": 50.00,
                "status": "delivered",
                "payment_method": "paypal",
                "shipping_cost": 0.0,
                "is_digital": True,
            },
        },
    },

    "CUST-012": {
        "customer_id": "CUST-012",
        "name": "Leo Jackson",
        "email": "leo.jackson@email.com",
        "phone": "+1-555-0112",
        "tier": "platinum",
        "account_age_days": 1460,
        "loyalty_points": 18000,
        "address": "963 Pine Grove, Atlanta, GA 30301",
        "refund_history": [
            {"refund_id": "REF-060", "order_id": "ORD-12000A", "amount": 400.00, "date": _days_ago(90), "reason": "Defective product", "status": "approved"},
        ],
        "total_refunds_this_year": 1,
        "total_refund_amount_this_year": 400.00,
        "orders": {
            "ORD-12001": {
                "order_id": "ORD-12001",
                "date": _days_ago(14),
                "items": [{"name": "Gaming Chair", "sku": "GC-900", "qty": 1, "price": 449.99}],
                "total": 449.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
        },
    },

    "CUST-013": {
        "customer_id": "CUST-013",
        "name": "Mia Harris",
        "email": "mia.harris@email.com",
        "phone": "+1-555-0113",
        "tier": "bronze",
        "account_age_days": 60,
        "loyalty_points": 180,
        "address": "174 Magnolia Ct, Houston, TX 77001",
        "refund_history": [],
        "total_refunds_this_year": 0,
        "total_refund_amount_this_year": 0.0,
        "orders": {
            "ORD-13001": {
                "order_id": "ORD-13001",
                "date": _days_ago(35),
                "items": [{"name": "Personalized Mug", "sku": "PM-001", "qty": 2, "price": 24.99, "is_personalized": True}],
                "total": 49.98,
                "status": "delivered",
                "payment_method": "debit_card",
                "shipping_cost": 8.99,
            },
        },
    },

    "CUST-014": {
        "customer_id": "CUST-014",
        "name": "Nathan Clark",
        "email": "nathan.clark@email.com",
        "phone": "+1-555-0114",
        "tier": "gold",
        "account_age_days": 680,
        "loyalty_points": 5500,
        "address": "285 Sycamore Blvd, San Diego, CA 92101",
        "refund_history": [
            {"refund_id": "REF-070", "order_id": "ORD-14000A", "amount": 120.00, "date": _days_ago(150), "reason": "Damaged", "status": "approved"},
            {"refund_id": "REF-071", "order_id": "ORD-14000B", "amount": 80.00, "date": _days_ago(50), "reason": "Wrong color", "status": "approved"},
        ],
        "total_refunds_this_year": 2,
        "total_refund_amount_this_year": 200.00,
        "orders": {
            "ORD-14001": {
                "order_id": "ORD-14001",
                "date": _days_ago(25),
                "items": [{"name": "Desk Lamp", "sku": "DL-400", "qty": 1, "price": 64.99}],
                "total": 64.99,
                "status": "delivered",
                "payment_method": "credit_card",
                "shipping_cost": 0.0,
            },
        },
    },

    "CUST-015": {
        "customer_id": "CUST-015",
        "name": "Olivia Lewis",
        "email": "olivia.lewis@email.com",
        "phone": "+1-555-0115",
        "tier": "silver",
        "account_age_days": 500,
        "loyalty_points": 2900,
        "address": "396 Poplar Path, Philadelphia, PA 19101",
        "refund_history": [
            {"refund_id": "REF-080", "order_id": "ORD-15000A", "amount": 39.99, "date": _days_ago(300), "reason": "Changed mind", "status": "approved"},
        ],
        "total_refunds_this_year": 1,
        "total_refund_amount_this_year": 39.99,
        "orders": {
            "ORD-15001": {
                "order_id": "ORD-15001",
                "date": _days_ago(12),
                "items": [
                    {"name": "Fitness Tracker", "sku": "FT-220", "qty": 1, "price": 119.99},
                    {"name": "Replacement Band", "sku": "RB-220", "qty": 1, "price": 19.99},
                ],
                "total": 139.98,
                "status": "delivered",
                "payment_method": "paypal",
                "shipping_cost": 0.0,
            },
        },
    },
}


def get_customer(customer_id: str) -> dict | None:
    return CRM_DATABASE.get(customer_id.upper())


def get_order(order_id: str) -> tuple[dict | None, str | None]:
    """Returns (order, customer_id) or (None, None)"""
    for cust_id, customer in CRM_DATABASE.items():
        if order_id in customer["orders"]:
            return customer["orders"][order_id], cust_id
    return None, None


def search_customer_by_email(email: str) -> dict | None:
    for customer in CRM_DATABASE.values():
        if customer["email"].lower() == email.lower():
            return customer
    return None


def search_customer_by_name(name: str) -> list[dict]:
    name_lower = name.lower()
    return [c for c in CRM_DATABASE.values() if name_lower in c["name"].lower()]


def list_all_customers() -> list[dict]:
    return [
        {"customer_id": c["customer_id"], "name": c["name"], "email": c["email"], "tier": c["tier"]}
        for c in CRM_DATABASE.values()
    ]
