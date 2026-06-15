"""
WebSocket Chat API — streams agent reasoning and responses to the frontend.

Authentication
--------------
Every WebSocket connection must include the auth session token as a query
parameter: ws://host/ws/chat/{chat_session_id}?auth={auth_session_id}

The auth_session_id is obtained from POST /api/auth/login and maps to a
specific user_id + email. The agent receives this context so it can enforce
order ownership automatically.
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import get_graph
from agent.state import AgentState
from data.auth_db import get_session
from data.crm_database import get_user

router = APIRouter()

# ─── In-memory chat session store ────────────────────────────────────────────
SESSIONS: dict[str, dict] = {}
# Admin WebSocket subscribers
ADMIN_SUBSCRIBERS: list[WebSocket] = []


def register_admin_ws(ws: WebSocket):
    ADMIN_SUBSCRIBERS.append(ws)


def unregister_admin_ws(ws: WebSocket):
    if ws in ADMIN_SUBSCRIBERS:
        ADMIN_SUBSCRIBERS.remove(ws)


async def broadcast_to_admins(payload: dict):
    dead = []
    for ws in ADMIN_SUBSCRIBERS:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        unregister_admin_ws(ws)


def get_or_create_session(session_id: str, user_id: str, user_email: str) -> dict:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "session_id":      session_id,
            "user_id":         user_id,
            "user_email":      user_email,
            "created_at":      datetime.now().isoformat(),
            "messages":        [],
            "reasoning_log":   [],
            "refund_decision": None,
            "order_id":        None,
        }
    return SESSIONS[session_id]


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
    auth: str = Query(default=""),
):
    # Accept WebSocket connection (origin check handled by auth token below)
    await websocket.accept()

    # ── Authentication gate ──────────────────────────────────────────────────
    auth_session = get_session(auth) if auth else None
    if not auth_session:
        await websocket.send_json({
            "type":    "auth_error",
            "message": "Please log in to use the support chat. "
                       "Use POST /api/auth/login to obtain a session token.",
        })
        await websocket.close(code=1008)
        return

    user_id    = auth_session["user_id"]
    user_email = auth_session["email"]

    # Optionally enrich with full user profile
    user = get_user(user_id)
    user_name = user_email.split("@")[0].split(".")[0].capitalize() if user_email else "Customer"

    session = get_or_create_session(session_id, user_id, user_email)
    graph   = get_graph()

    # Send welcome confirmation
    await websocket.send_json({
        "type":       "authenticated",
        "user_id":    user_id,
        "user_email": user_email,
        "user_name":  user_name,
        "message":    f"Welcome back, {user_name}! How can I help you today?",
    })

    try:
        while True:
            data         = await websocket.receive_text()
            payload      = json.loads(data)
            user_message = payload.get("message", "").strip()

            if not user_message:
                continue

            # Store user message
            session["messages"].append({
                "role":      "user",
                "content":   user_message,
                "timestamp": datetime.now().isoformat(),
            })

            # Send typing indicator
            await websocket.send_json({"type": "typing", "status": True})

            # Build LangGraph input state
            history_messages = [
                HumanMessage(content=m["content"]) if m["role"] == "user"
                else AIMessage(content=m["content"])
                for m in session["messages"][:-1]
            ]
            history_messages.append(HumanMessage(content=user_message))

            state: AgentState = {
                "messages":        history_messages,
                "session_id":      session_id,
                "user_id":         user_id,
                "user_email":      user_email,
                "order_id":        session.get("order_id"),
                "reasoning_log":   [],
                "refund_decision": session.get("refund_decision"),
                "refund_amount":   None,
                "iteration_count": 0,
            }

            # Run the graph and collect logs
            all_logs       = []
            final_response = ""
            final_decision = session.get("refund_decision")

            async for event in graph.astream(state, stream_mode="values"):
                new_logs = event.get("reasoning_log", [])
                for log in new_logs:
                    if log not in all_logs:
                        all_logs.append(log)
                        await websocket.send_json({
                            "type": "reasoning_log",
                            "log":  log,
                        })
                        await broadcast_to_admins({
                            "type":       "reasoning_log",
                            "session_id": session_id,
                            "log":        log,
                        })
                        await asyncio.sleep(0)

                last_messages = event.get("messages", [])
                if last_messages:
                    last = last_messages[-1]
                    if isinstance(last, AIMessage) and last.content:
                        final_response = last.content

                if event.get("order_id"):
                    session["order_id"] = event["order_id"]
                if event.get("refund_decision"):
                    final_decision = event["refund_decision"]
                    session["refund_decision"] = final_decision

            # Store assistant response
            session["messages"].append({
                "role":      "assistant",
                "content":   final_response,
                "timestamp": datetime.now().isoformat(),
            })
            session["reasoning_log"].extend(all_logs)

            # Stop typing indicator
            await websocket.send_json({"type": "typing", "status": False})

            # Send final response
            await websocket.send_json({
                "type":            "message",
                "role":            "assistant",
                "content":         final_response,
                "timestamp":       datetime.now().isoformat(),
                "refund_decision": final_decision,
            })

            # Broadcast session update to admins
            await broadcast_to_admins({
                "type":       "session_update",
                "session_id": session_id,
                "session": {
                    "session_id":      session_id,
                    "user_id":         user_id,
                    "user_email":      user_email,
                    "created_at":      session["created_at"],
                    "message_count":   len(session["messages"]),
                    "refund_decision": final_decision,
                },
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type":    "error",
                "message": f"Agent error: {str(e)}",
            })
        except Exception:
            pass


@router.get("/api/sessions")
async def list_sessions():
    return [
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


@router.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}
    return session
