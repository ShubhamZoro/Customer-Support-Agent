from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: str = ""


class ReasoningLogEntry(BaseModel):
    timestamp: str
    node: str
    message: str
    level: str  # "info" | "success" | "error" | "warning"
    detail: dict = {}


class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    refund_decision: Optional[str] = None
    customer_id: Optional[str] = None


class VoiceTranscribeResponse(BaseModel):
    text: str
    language: Optional[str] = None


class VoiceSynthesizeRequest(BaseModel):
    text: str
    voice: str = "alloy"
