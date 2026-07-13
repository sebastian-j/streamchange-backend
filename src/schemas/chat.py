from pydantic import BaseModel
from typing import Optional


class MessageFragment(BaseModel):
    type: str
    text: Optional[str] = None
    url: Optional[str] = None
    code: Optional[str] = None


class ChatMessage(BaseModel):
    user_id: Optional[str] = None
    author: str
    message: str
    color: str
    badges: Optional[list[str]] = None
    subscriber: int
    fragments: Optional[list[MessageFragment]] = None


class StreamData(BaseModel):
    is_live: bool
    title: Optional[str] = None
    viewer_count: int = 0
    game_name: Optional[str] = None
    started_at: Optional[str] = None
