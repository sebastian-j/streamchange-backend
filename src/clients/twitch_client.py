from typing import Callable
from src.clients.abstract_client import AbstractClient
import asyncio

from src.config import TWITCH_IRC_HOST, TWITCH_IRC_PORT, TWITCH_NICK


class TwitchClient(AbstractClient):
    def __init__(self, on_message: Callable) -> None:
        self.reader = None
        self.writer = None
        super().__init__(on_message)

    async def connect(self, channel: str) -> None:
        self.reader, self.writer = await asyncio.open_connection(
            TWITCH_IRC_HOST, TWITCH_IRC_PORT
        )

        self.writer.write("PASS anonymous\r\n".encode("utf-8"))
        self.writer.write(f"NICK {TWITCH_NICK}\r\n".encode("utf-8"))
        self.writer.write(f"JOIN #{channel}\r\n".encode("utf-8"))
        await self.writer.drain()
        self._spawn(self._listen_loop())

    async def disconnect(self) -> None:
        await self._cancel_task()
        await self._close_connection()

    async def _close_connection(self) -> None:
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

        self.reader = None
        self.writer = None

    async def _listen_loop(self) -> None:
        try:
            while self.reader and not self.reader.at_eof():
                line_bytes = await self.reader.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="ignore").strip()

                if line.startswith("PING"):
                    self.writer.write("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    await self.writer.drain()
                    continue

                parts = line.split(" ", 2)
                if len(parts) > 2 and parts[1] == "PRIVMSG":
                    author = parts[0].split("!")[0][1:]
                    message_part = parts[2].split(":", 1)

                    if len(message_part) > 1:
                        content = message_part[1]
                        await self.on_message(author, content)

        except asyncio.CancelledError:
            print("Pętla zatrzymana.")
        finally:
            await self._close_connection()
