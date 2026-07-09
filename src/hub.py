import asyncio
import logging

from src.clients.abstract_client import AbstractClient, Subscriber
from src.clients.kick_client import KickClient
from src.clients.twitch_client import TwitchClient
from src.resolvers.kick_resolver import get_chatroom_id

logger = logging.getLogger(__name__)

ChannelKey = tuple[str, str | int]


class Hub:
    def __init__(self):
        self._clients: dict[ChannelKey, AbstractClient] = {}
        self._locks: dict[ChannelKey, asyncio.Lock] = {}

    def _get_lock(self, key: ChannelKey) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    async def _resolve(self, platform: str, channel: str) -> ChannelKey:
        if platform == "twitch":
            return platform, channel
        elif platform == "kick":
            chatroom_id = await asyncio.to_thread(get_chatroom_id, channel)
            return platform, chatroom_id

    def _build_client(self, platform: str) -> AbstractClient:
        if platform == "twitch":
            return TwitchClient()
        elif platform == "kick":
            return KickClient()

    async def subscribe(
        self, channel: str, platform: str, callback: Subscriber
    ) -> ChannelKey:
        key = await self._resolve(platform, channel)
        async with self._get_lock(key):
            client = self._clients.get(key)
            if not client:
                client = self._build_client(platform)
                await client.connect(key[1])
                self._clients[key] = client
                logger.info("Utworzono połączenie dla %s", key)
            else:
                logger.info("Reużywam połączenia dla %s", key)

            client.add_subscriber(callback)
        return key

    async def unsubscribe(self, key: ChannelKey, callback: Subscriber) -> None:
        lock = self._locks.get(key)
        if lock is None:
            return

        async with lock:
            client = self._clients.get(key)
            if client is None:
                return
            
            client.remove_subscriber(callback)
            
            if not client.has_subscribers():
                await client.disconnect()
                
                if key in self._clients:
                    del self._clients[key]

                if not lock._waiters:
                    if key in self._locks:
                        del self._locks[key]
                    logger.info("Zamknięto połączenie i wyczyszczono lock dla %s", key)
                else:
                    logger.info("Zamknięto połączenie dla %s, ale zachowano lock", key)
