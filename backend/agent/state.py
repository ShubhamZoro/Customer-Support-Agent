from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """LangGraph state for the refund agent."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    session_id: str
    customer_id: Optional[str]
    order_id: Optional[str]
    reasoning_log: Annotated[list[dict], operator.add]
    refund_decision: Optional[str]        # "approved" | "denied" | "escalated" | None
    refund_amount: Optional[float]
    iteration_count: int
