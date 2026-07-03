from pydantic import BaseModel


class ChatMessage(BaseModel):
    author: str
    message: str
    color: str
    is_vip: bool
    is_moderator: bool
    subscriber: int
    is_streamer: bool