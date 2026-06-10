"""
WebSocket Chat API — streams agent reasoning and responses to the frontend
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage, AIMessage

from agent.graph import get_graph
from agent.state import AgentState

router = APIRouter()

# ─── In-memory session store ─────────────────────────────────────────────────
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


def get_or_create_session(session_id: str) -> dict:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "reasoning_log": [],
            "refund_decision": None,
            "customer_id": None,
            "order_id": None,
        }
    return SESSIONS[session_id]


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = get_or_create_session(session_id)
    graph = get_graph()

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_message = payload.get("message", "").strip()

            if not user_message:
                continue

            # Store user message
            session["messages"].append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.now().isoformat(),
            })

            # Send typing indicator
            await websocket.send_json({"type": "typing", "status": True})

            # Build LangGraph input state
            history_messages = [
                HumanMessage(content=m["content"]) if m["role"] == "user"
                else AIMessage(content=m["content"])
                for m in session["messages"][:-1]  # all but the current user msg
            ]
            history_messages.append(HumanMessage(content=user_message))

            state: AgentState = {
                "messages": history_messages,
                "session_id": session_id,
                "customer_id": session.get("customer_id"),
                "order_id": session.get("order_id"),
                "reasoning_log": [],
                "refund_decision": session.get("refund_decision"),
                "refund_amount": None,
                "iteration_count": 0,
            }

            # Run the graph and collect logs
            all_logs = []
            final_response = ""

            async for event in graph.astream(state, stream_mode="values"):
                new_logs = event.get("reasoning_log", [])
                for log in new_logs:
                    if log not in all_logs:
                        all_logs.append(log)
                        # Stream each reasoning step to client
                        await websocket.send_json({
                            "type": "reasoning_log",
                            "log": log,
                        })
                        # Broadcast to admin subscribers
                        await broadcast_to_admins({
                            "type": "reasoning_log",
                            "session_id": session_id,
                            "log": log,
                        })
                        await asyncio.sleep(0)

                # Track final state
                last_messages = event.get("messages", [])
                if last_messages:
                    last = last_messages[-1]
                    if isinstance(last, AIMessage) and last.content:
                        final_response = last.content

                if event.get("customer_id"):
                    session["customer_id"] = event["customer_id"]
                if event.get("order_id"):
                    session["order_id"] = event["order_id"]
                if event.get("refund_decision"):
                    session["refund_decision"] = event["refund_decision"]

            # Store and send final AI response
            session["messages"].append({
                "role": "assistant",
                "content": final_response,
                "timestamp": datetime.now().isoformat(),
            })
            session["reasoning_log"].extend(all_logs)

            # Stop typing indicator
            await websocket.send_json({"type": "typing", "status": False})

            # Send final response
            await websocket.send_json({
                "type": "message",
                "role": "assistant",
                "content": final_response,
                "timestamp": datetime.now().isoformat(),
                "refund_decision": session.get("refund_decision"),
            })

            # Broadcast session update to admins
            await broadcast_to_admins({
                "type": "session_update",
                "session_id": session_id,
                "session": {
                    "session_id": session_id,
                    "created_at": session["created_at"],
                    "message_count": len(session["messages"]),
                    "refund_decision": session.get("refund_decision"),
                    "customer_id": session.get("customer_id"),
                },
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Agent error: {str(e)}",
            })
        except Exception:
            pass


@router.get("/api/sessions")
async def list_sessions():
    return [
        {
            "session_id": s["session_id"],
            "created_at": s["created_at"],
            "message_count": len(s["messages"]),
            "refund_decision": s.get("refund_decision"),
            "customer_id": s.get("customer_id"),
        }
        for s in SESSIONS.values()
    ]


@router.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}
    return session
