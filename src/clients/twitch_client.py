from src.clients.abstract_client import AbstractClient
import asyncio


class TwitchClient(AbstractClient):
    TWITCH_IRC_HOST = "irc.chat.twitch.tv"
    TWITCH_IRC_PORT = 6667
    NICK = "justinfan12345"

    def __init__(self, on_message):
        self.reader = None
        self.writer = None
        self._read_task = None
        self.on_message = on_message

    async def connect(self, channel: str) -> None:
        self.reader, self.writer = await asyncio.open_connection(
            self.TWITCH_IRC_HOST, self.TWITCH_IRC_PORT
        )

        self.writer.write("PASS anonymous\r\n".encode("utf-8"))
        self.writer.write(f"NICK {self.NICK}\r\n".encode("utf-8"))
        self.writer.write(f"JOIN #{channel}\r\n".encode("utf-8"))
        await self.writer.drain()
        self._read_task = asyncio.create_task(self._listen_loop())

    async def disconnect(self) -> None:
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

        self.reader = None
        self.writer = None
        self._read_task = None

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
            print("Listen loop cancelled.")
        finally:
            await self.disconnect()
