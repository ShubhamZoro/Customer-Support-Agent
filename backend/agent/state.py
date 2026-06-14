from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """LangGraph state for the refund agent."""
    messages:        Annotated[Sequence[BaseMessage], operator.add]
    session_id:      str
    user_id:         Optional[str]   # authenticated user's ID (e.g. 'USR-001')
    user_email:      Optional[str]   # authenticated user's email (for emails)
    order_id:        Optional[str]   # last referenced order
    reasoning_log:   Annotated[list[dict], operator.add]
    refund_decision: Optional[str]   # "refund_initiated" | "denied" | None
    refund_amount:   Optional[float]
    iteration_count: int
