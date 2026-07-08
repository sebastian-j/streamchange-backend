import asyncio

from src.clients.abstract_client import AbstractClient, Subscriber
from src.clients.kick_client import KickClient
from src.clients.twitch_client import TwitchClient
from src.resolvers.kick_resolver import get_chatroom_id


ChannelKey = tuple[str, str | int]


class Hub:
    def __init__(self):
        self._clients: dict[ChannelKey, AbstractClient] = {}

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
        client = self._clients.get(key)
        if not client:
            client = self._build_client(platform)
            await client.connect(key[1])
            self._clients[key] = client

        client.add_subscriber(callback)
        return key

    async def unsubscribe(self, key: ChannelKey, callback: Subscriber) -> None:
        client = self._clients.get(key)
        if client is None:
            return
        client.remove_subscriber(callback)
        if not client.has_subscribers():
            await client.disconnect()
            del self._clients[key]
