import asyncio
import json
import logging

import websockets
from websockets.exceptions import ConnectionClosed

from src.clients.abstract_client import AbstractClient
from src.clients.emotes import parse_kick_emotes, strip_kick_emote_tokens
from src.config import KICK_PUSHER_WS
from src.known_bots import is_known_bot
from src.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

MAX_RETRY_DELAY = 30

KICK_BADGE_MAP = {
    "broadcaster": "broadcaster",
    "moderator": "moderator",
    "vip": "vip",
    "subscriber": "subscriber",
    "founder": "founder",
    "verified": "certified",
    "og": "og",
    "bot": "bot",
}


class KickClient(AbstractClient):
    def __init__(self) -> None:
        super().__init__()
        self.ws = None
        self.running = False

    async def connect(self, channel: int) -> None:
        self.running = True
        self._spawn(self._run(channel))

    async def _run(self, channel: int) -> None:
        delay = 1

        while self.running:
            try:
                async with websockets.connect(KICK_PUSHER_WS, ping_interval=30) as ws:
                    self.ws = ws
                    delay = 1

                    await ws.send(
                        json.dumps(
                            {
                                "event": "pusher:subscribe",
                                "data": {
                                    "auth": "",
                                    "channel": f"chatrooms.{channel}.v2",
                                },
                            }
                        )
                    )
                    logger.info("Połączono z czatem Kick: chatroom %s", channel)

                    async for raw in ws:
                        if not self.running:
                            return
                        await self._handle_frame(raw)

            except ConnectionClosed as e:
                if not self.running:
                    return
                logger.warning(
                    "WebSocket rozłączony: %s. Ponowna próba za %ds...", e, delay
                )
            except Exception as e:
                if not self.running:
                    return
                logger.error(
                    "Nieoczekiwany błąd: %s. Ponowna próba za %ds...", e, delay
                )

            await asyncio.sleep(delay)
            delay = min(delay * 2, MAX_RETRY_DELAY)

    async def disconnect(self) -> None:
        self.running = False
        if self.ws:
            await self.ws.close()
        await self._cancel_task()

    async def _handle_frame(self, raw: str) -> None:
        try:
            frame = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Nie można zdekodować ramki: %r", raw)
            return

        if frame.get("event") != "App\\Events\\ChatMessageEvent":
            return

        try:
            data = json.loads(frame["data"])
            sender = data["sender"]
            username = sender["username"]
            content = data["content"]
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(
                "Nieprawidłowa struktura wiadomości: %s | ramka: %r", e, frame
            )
            return

        identity = sender.get("identity") or {}

        subscriber = 0
        badges = []
        for badge in identity.get("badges") or []:
            badge_type = badge.get("type")
            if badge_type == "subscriber":
                subscriber = badge.get("count", 0)
            mapped = KICK_BADGE_MAP.get(badge_type)
            if mapped and mapped not in badges:
                badges.append(mapped)

        if "bot" not in badges and is_known_bot(username):
            badges.append("bot")
        fragments = parse_kick_emotes(content)

        sender_id = sender.get("id")

        chat_msg = ChatMessage(
            user_id=str(sender_id) if sender_id is not None else None,
            author=username,
            message=strip_kick_emote_tokens(content),
            color=identity.get("color") or "#000000",
            badges=badges or None,
            subscriber=subscriber,
            fragments=fragments,
        )

        try:
            await self._broadcast(chat_msg)
        except Exception:
            logger.exception("Błąd podczas przetwarzania wiadomości od %s", username)
