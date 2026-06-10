"""
Admin API — Real-time reasoning logs, session management, WebSocket dashboard feed
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from data.crm_database import list_all_customers, CRM_DATABASE
from data.refund_policy import REFUND_POLICY_TEXT

router = APIRouter()


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
            "session_id": s["session_id"],
            "created_at": s["created_at"],
            "message_count": len(s["messages"]),
            "refund_decision": s.get("refund_decision"),
            "customer_id": s.get("customer_id"),
        }
        for s in SESSIONS.values()
    ]
    await websocket.send_json({
        "type": "init",
        "sessions": sessions_snapshot,
    })

    try:
        while True:
            # Keep connection alive — admin WS is primarily push-based
            await websocket.receive_text()
    except WebSocketDisconnect:
        unregister_admin_ws(websocket)
    except Exception:
        unregister_admin_ws(websocket)


@router.get("/api/admin/customers")
async def get_all_customers():
    """Return all CRM customers for admin view."""
    return list_all_customers()


@router.get("/api/admin/customers/{customer_id}")
async def get_customer_detail(customer_id: str):
    """Return full customer profile."""
    customer = CRM_DATABASE.get(customer_id.upper())
    if not customer:
        return {"error": "Customer not found"}
    return customer


@router.get("/api/admin/policy")
async def get_policy():
    """Return the full refund policy document."""
    return {"policy": REFUND_POLICY_TEXT}


@router.get("/api/admin/sessions")
async def get_admin_sessions():
    """Return all active sessions with full details."""
    from api.chat import SESSIONS
    return [
        {
            "session_id": s["session_id"],
            "created_at": s["created_at"],
            "message_count": len(s["messages"]),
            "refund_decision": s.get("refund_decision"),
            "customer_id": s.get("customer_id"),
            "reasoning_log_count": len(s.get("reasoning_log", [])),
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
        "session_id": session_id,
        "reasoning_log": session.get("reasoning_log", []),
        "messages": session.get("messages", []),
        "refund_decision": session.get("refund_decision"),
        "customer_id": session.get("customer_id"),
    }
