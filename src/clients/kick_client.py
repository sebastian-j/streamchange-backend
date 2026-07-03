import asyncio
import json
import logging
from typing import Callable

import websockets
from websockets.exceptions import ConnectionClosed

from src.clients.abstract_client import AbstractClient
from src.config import KICK_PUSHER_WS

logger = logging.getLogger(__name__)

MAX_RETRY_DELAY = 30


class KickClient(AbstractClient):
    def __init__(self, on_message: Callable) -> None:
        super().__init__(on_message)
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
            username = data["sender"]["username"]
            content = data["content"]
        except (KeyError, json.JSONDecodeError) as e:
            logger.warning(
                "Nieprawidłowa struktura wiadomości: %s | ramka: %r", e, frame
            )
            return

        try:
            await self.on_message(username, content)
        except Exception:
            logger.exception("Błąd podczas przetwarzania wiadomości od %s", username)
