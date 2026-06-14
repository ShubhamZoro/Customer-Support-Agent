"""
Admin API — Real-time reasoning logs, session management, WebSocket dashboard feed
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from data.crm_database import get_user, get_orders_for_user
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


@router.get("/api/admin/policy")
async def get_policy():
    """Return the full refund policy document."""
    return {"policy": REFUND_POLICY_TEXT}


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
