import asyncio
import logging

from src.clients.abstract_client import AbstractClient
from src.config import TWITCH_IRC_HOST, TWITCH_IRC_PORT, TWITCH_NICK
from src.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)


class TwitchClient(AbstractClient):
    def __init__(self) -> None:
        super().__init__()
        self.reader = None
        self.writer = None
        self.current_channel = None

    async def connect(self, channel: str) -> None:
        self.current_channel = channel.lower().strip()

        self.reader, self.writer = await asyncio.open_connection(
            TWITCH_IRC_HOST, TWITCH_IRC_PORT
        )

        self.writer.write("PASS anonymous\r\n".encode("utf-8"))
        self.writer.write(f"NICK {TWITCH_NICK}\r\n".encode("utf-8"))
        self.writer.write(
            "CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership\r\n".encode(
                "utf-8"
            )
        )
        self.writer.write(f"JOIN #{self.current_channel}\r\n".encode("utf-8"))
        await self.writer.drain()
        logger.info("Połączono z czatem Twitch: #%s", self.current_channel)
        self._spawn(self._listen_loop())

    async def disconnect(self) -> None:
        await self._cancel_task()
        await self._close_connection()

    async def _close_connection(self) -> None:
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                logger.warning(
                    "Błąd podczas zamykania połączenia Twitch.", exc_info=True
                )

        self.reader = None
        self.writer = None

    async def _listen_loop(self) -> None:
        try:
            while self.reader and not self.reader.at_eof():
                line_bytes = await self.reader.readline()
                if not line_bytes:
                    break

                line = line_bytes.decode("utf-8", errors="ignore").strip()

                tags = {}
                if line.startswith("@"):
                    tags_part, line = line.split(" ", 1)
                    for item in tags_part[1:].split(";"):
                        if "=" in item:
                            k, v = item.split("=", 1)
                            tags[k] = v

                if line.startswith("PING"):
                    self.writer.write("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                    await self.writer.drain()
                    continue

                parts = line.split(" ", 2)
                if len(parts) > 2 and parts[1] == "PRIVMSG":
                    author = tags.get("display-name") or parts[0].split("!")[0][1:]
                    message_part = parts[2].split(":", 1)
                    content = message_part[1] if len(message_part) > 1 else ""

                    is_streamer = author.lower() == self.current_channel.lower()

                    sub_months = 0
                    if tags.get("subscriber") == "1":
                        sub_months = 1
                        badge_info = tags.get("badge-info")
                        if badge_info:
                            for badge in badge_info.split(","):
                                if badge.startswith("subscriber/"):
                                    try:
                                        sub_months = int(badge.split("/")[1])
                                    except (IndexError, ValueError):
                                        pass

                    chat_msg = ChatMessage(
                        author=author,
                        message=content,
                        color=tags.get("color") or "#A9A9A9",
                        is_vip=tags.get("vip") == "1",
                        is_moderator=tags.get("mod") == "1",
                        subscriber=sub_months,
                        is_streamer=is_streamer,
                    )

                    await self._broadcast(chat_msg)

        except asyncio.CancelledError:
            logger.info("Pętla nasłuchu Twitch zatrzymana: #%s", self.current_channel)
        finally:
            await self._close_connection()
