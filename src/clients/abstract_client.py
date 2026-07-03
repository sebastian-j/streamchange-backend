import asyncio
from abc import ABC, abstractmethod
from typing import Callable


class AbstractClient(ABC):
    def __init__(self, on_message: Callable) -> None:
        self.on_message = on_message
        self._task: asyncio.Task | None = None

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
