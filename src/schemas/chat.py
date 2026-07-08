from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    author: str
    message: str
    color: str
    is_vip: bool
    is_moderator: bool
    subscriber: int
    is_streamer: bool


class StreamData(BaseModel):
    is_live: bool
    title: Optional[str] = None
    viewer_count: int = 0
    game_name: Optional[str] = None
    started_at: Optional[str] = None
