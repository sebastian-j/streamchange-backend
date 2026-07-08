import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from src.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

Subscriber = Callable[[ChatMessage], Awaitable[None]]


class AbstractClient(ABC):
    def __init__(self) -> None:
        self._subscribers: set[Subscriber] = set()
        self._task: asyncio.Task | None = None

    def add_subscriber(self, callback: Subscriber) -> None:
        self._subscribers.add(callback)

    def remove_subscriber(self, callback: Subscriber) -> None:
        self._subscribers.discard(callback)

    def has_subscribers(self) -> bool:
        return bool(self._subscribers)

    async def _broadcast(self, chat_msg: ChatMessage) -> None:
        for subscriber_call in list(self._subscribers):
            try:
                await subscriber_call(chat_msg)
            except Exception:
                logger.warning(
                    "Nie udało się dostarczyć wiadomości subskrybentowi, odpinam go.",
                    exc_info=True,
                )
                self._subscribers.discard(subscriber_call)

    def _spawn(self, coro) -> None:
        self._task = asyncio.create_task(coro)

    async def _cancel_task(self) -> None:
        if self._task is None:
            return
        if self._task is not asyncio.current_task():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    @abstractmethod
    async def connect(self, channel: str | int) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass
