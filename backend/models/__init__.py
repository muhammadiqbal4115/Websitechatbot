from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    sources: list[str] = []


class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str = "General"


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    active: Optional[int] = None


class AdminLogin(BaseModel):
    username: str
    password: str
