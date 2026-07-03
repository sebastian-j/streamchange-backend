from abc import ABC, abstractmethod
from typing import Callable


class AbstractClient(ABC):
    def __init__(self, on_message: Callable) -> None:
        self.on_message = on_message

    @abstractmethod
    async def connect(self, channel: str | int) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass
