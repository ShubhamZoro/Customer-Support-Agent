import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")
try:
    from data.crm_database import list_users, create_user, next_user_id
    print("  [OK] crm_database imports (list_users, create_user, next_user_id)")
except Exception as e:
    print(f"  [FAIL] crm_database: {e}")

try:
    from data.auth_db import login, logout, get_session
    print("  [OK] auth_db imports")
except Exception as e:
    print(f"  [FAIL] auth_db: {e}")

try:
    from api.admin import router as admin_router
    print("  [OK] api.admin router")
except Exception as e:
    print(f"  [FAIL] api.admin: {e}")

try:
    from api.auth import router as auth_router
    print("  [OK] api.auth router")
except Exception as e:
    print(f"  [FAIL] api.auth: {e}")

try:
    from agent.prompts import build_system_prompt
    prompt = build_system_prompt("USR-001", "test@test.com")
    has_no_order = "no_orders" in prompt or "No-Order" in prompt
    print(f"  [OK] agent.prompts — no-order rule present: {has_no_order}")
except Exception as e:
    print(f"  [FAIL] agent.prompts: {e}")

print()
print("Checking database...")
try:
    from data.crm_database import list_users
    users = list_users()
    print(f"  [OK] {len(users)} users in DB:")
    for u in users:
        print(f"       {u['user_id']}  {u['email']}")
    nxt = next_user_id()
    print(f"  [OK] Next user ID would be: {nxt}")
except Exception as e:
    print(f"  [FAIL] DB query: {e}")

print()
print("Testing user creation (dry run - no actual insert)...")
try:
    from data.crm_database import get_user_by_email
    test = get_user_by_email("alice.johnson@demo.com")
    if test:
        print(f"  [OK] get_user_by_email works: {test['user_id']}")
    else:
        print("  [WARN] alice not found — may need to re-seed DB")
except Exception as e:
    print(f"  [FAIL] get_user_by_email: {e}")

print()
print("All checks done.")
