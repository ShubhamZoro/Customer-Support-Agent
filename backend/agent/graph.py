"""
LangGraph StateGraph — Refund Agent Loop
"""
import json
from datetime import datetime
from typing import Literal

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import ALL_TOOLS
from agent.prompts import SYSTEM_PROMPT
from config import settings

MAX_ITERATIONS = 15

# ─── Lazy singletons — initialized on first graph build ─────────────────────
_llm = None
_llm_with_tools = None
_tool_node = None


def _get_llm():
    global _llm, _llm_with_tools, _tool_node
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
            streaming=True,
        )
        _llm_with_tools = _llm.bind_tools(ALL_TOOLS)
        _tool_node = ToolNode(ALL_TOOLS)
    return _llm, _llm_with_tools, _tool_node


# ─────────────────────────────────────────────────────────────────────────────
# NODE: agent — LLM decides what to do
# ─────────────────────────────────────────────────────────────────────────────
def agent_node(state: AgentState) -> dict:
    messages = list(state["messages"])

    # Inject system message if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    # Safety: cap iterations
    iteration = state.get("iteration_count", 0)
    if iteration >= MAX_ITERATIONS:
        return {
            "messages": [AIMessage(content="I've reached the maximum reasoning steps. Please contact support directly.")],
            "iteration_count": iteration + 1,
            "reasoning_log": [_log_entry("agent", "Max iterations reached — terminating loop.", "warning")],
        }

    response = llm_with_tools.invoke(messages)

    # Build reasoning log entry
    log_entries = []
    if response.tool_calls:
        for tc in response.tool_calls:
            log_entries.append(_log_entry(
                node="agent",
                message=f"Calling tool: **{tc['name']}**",
                level="info",
                detail={"tool": tc["name"], "args": tc["args"]},
            ))
    else:
        log_entries.append(_log_entry(
            node="agent",
            message="Agent produced final response (no more tool calls).",
            level="success",
        ))

    # Extract refund decision from content if present
    decision = state.get("refund_decision")
    content_lower = (response.content or "").lower()
    if "approved" in content_lower and "refund" in content_lower:
        decision = "approved"
    elif "denied" in content_lower or "unfortunately" in content_lower:
        decision = "denied"
    elif "escalat" in content_lower:
        decision = "escalated"

    return {
        "messages": [response],
        "iteration_count": iteration + 1,
        "reasoning_log": log_entries,
        "refund_decision": decision,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE: tools — Execute the tool calls
# ─────────────────────────────────────────────────────────────────────────────
def tools_node(state: AgentState) -> dict:
    """Execute tool calls and log results."""
    result = tool_node.invoke(state)
    log_entries = []

    for msg in result.get("messages", []):
        if isinstance(msg, ToolMessage):
            try:
                content_data = json.loads(msg.content)
                status = content_data.get("status", "unknown")
                level = "success" if status in ("found", "approved", "escalated") else \
                        "error" if status in ("not_found", "denied") else "info"
                log_entries.append(_log_entry(
                    node="tool_executor",
                    message=f"Tool **{msg.name}** returned: `{status}`",
                    level=level,
                    detail=content_data,
                ))
            except Exception:
                log_entries.append(_log_entry(
                    node="tool_executor",
                    message=f"Tool **{msg.name}** returned result.",
                    level="info",
                ))

    return {
        **result,
        "reasoning_log": log_entries,
    }


# ─────────────────────────────────────────────────────────────────────────────
# EDGE: router — should_continue
# ─────────────────────────────────────────────────────────────────────────────
def should_continue(state: AgentState) -> Literal["tools", "end"]:
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if last_message is None:
        return "end"

    # If the last AI message has tool calls, go to tools node
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return "end"


# ─────────────────────────────────────────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────────────────────────────────────────
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)

    graph.set_entry_point("agent")

    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    graph.add_edge("tools", "agent")

    return graph.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


# ─────────────────────────────────────────────────────────────────────────────
# Helper: log entry factory
# ─────────────────────────────────────────────────────────────────────────────
def _log_entry(node: str, message: str, level: str = "info", detail: dict = None) -> dict:
    return {
        "timestamp": datetime.now().isoformat(),
        "node": node,
        "message": message,
        "level": level,
        "detail": detail or {},
    }
