from abc import ABC, abstractmethod


class AbstractClient(ABC):
    @abstractmethod
    async def connect(self, channel: str) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass
