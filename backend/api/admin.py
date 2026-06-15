"""
Admin API — Real-time reasoning logs, session management, user management, WebSocket dashboard feed
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Optional
from data.crm_database import (
    get_user, get_orders_for_user, list_users, create_user, get_user_by_email
)
from data.refund_policy import REFUND_POLICY_TEXT

router = APIRouter()


# ─── Models ──────────────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: str
    password: str
    user_age: Optional[int] = None
    user_gender: Optional[str] = None
    user_location: Optional[str] = None


# ─── Admin WebSocket ──────────────────────────────────────────────────────────

@router.websocket("/ws/admin")
async def admin_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for admin dashboard — receives real-time reasoning logs
    and session updates from the chat handler.
    """
    from api.chat import register_admin_ws, unregister_admin_ws, SESSIONS

    await websocket.accept()
    register_admin_ws(websocket)

    # Send current session snapshot on connect
    sessions_snapshot = [
        {
            "session_id":      s["session_id"],
            "user_id":         s.get("user_id"),
            "user_email":      s.get("user_email"),
            "created_at":      s["created_at"],
            "message_count":   len(s["messages"]),
            "refund_decision": s.get("refund_decision"),
        }
        for s in SESSIONS.values()
    ]
    await websocket.send_json({
        "type":     "init",
        "sessions": sessions_snapshot,
    })

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_admin_ws(websocket)
    except Exception:
        unregister_admin_ws(websocket)


# ─── Policy ───────────────────────────────────────────────────────────────────

@router.get("/api/admin/policy")
async def get_policy():
    """Return the full refund policy document."""
    return {"policy": REFUND_POLICY_TEXT}


# ─── Sessions ─────────────────────────────────────────────────────────────────

@router.get("/api/admin/sessions")
async def get_admin_sessions():
    """Return all active chat sessions with full details."""
    from api.chat import SESSIONS
    return [
        {
            "session_id":            s["session_id"],
            "user_id":               s.get("user_id"),
            "user_email":            s.get("user_email"),
            "created_at":            s["created_at"],
            "message_count":         len(s["messages"]),
            "refund_decision":       s.get("refund_decision"),
            "reasoning_log_count":   len(s.get("reasoning_log", [])),
        }
        for s in SESSIONS.values()
    ]


@router.get("/api/admin/sessions/{session_id}/logs")
async def get_session_logs(session_id: str):
    """Return full reasoning logs for a specific session."""
    from api.chat import SESSIONS
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}
    return {
        "session_id":      session_id,
        "user_id":         session.get("user_id"),
        "user_email":      session.get("user_email"),
        "reasoning_log":   session.get("reasoning_log", []),
        "messages":        session.get("messages", []),
        "refund_decision": session.get("refund_decision"),
    }


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/api/admin/users")
async def get_all_users():
    """Return all registered users with order count and order presence flag."""
    users = list_users()
    result = []
    for u in users:
        orders = get_orders_for_user(u["user_id"])
        result.append({
            **u,
            "order_count": len(orders),
            "has_orders":  len(orders) > 0,
        })
    return result


@router.post("/api/admin/users", status_code=201)
async def create_new_user(body: CreateUserRequest):
    """
    Create a new user account.
    Returns 409 if email already exists.
    """
    # Check if email already taken
    existing = get_user_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"A user with email '{body.email}' already exists.",
        )

    user = create_user(
        email=body.email,
        plain_password=body.password,
        age=body.user_age,
        gender=body.user_gender,
        location=body.user_location,
    )
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user.")

    return {
        **user,
        "order_count": 0,
        "has_orders":  False,
        "message":     f"User '{body.email}' created successfully.",
    }


@router.get("/api/admin/users/{user_id}")
async def get_user_profile(user_id: str):
    """Return a specific user's profile with their orders."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    orders = get_orders_for_user(user_id)
    return {
        **user,
        "orders":      orders,
        "order_count": len(orders),
        "has_orders":  len(orders) > 0,
    }
