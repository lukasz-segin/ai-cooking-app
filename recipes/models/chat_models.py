from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TokenUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_items=1)
    model: str = Field(..., min_length=1)
    stream: bool = False
    json_mode: bool = False
    provider: Literal["openai", "anthropic"] = "openai"
    conversation_id: Optional[str] = None
    max_tokens: Optional[int] = 1024
    max_completion_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    content: str
    model: str
    provider: str
    token_usage: Optional[TokenUsage] = None
    finish_reason: Optional[str] = None 