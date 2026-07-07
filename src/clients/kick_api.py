import logging

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import RequestException

from src.config import KICK_CHANNELS_URL
from src.schemas.chat import StreamData

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10


class KickAPIService:
    def __init__(self):
        self._session = AsyncSession(impersonate="chrome", timeout=REQUEST_TIMEOUT)

    async def aclose(self) -> None:
        await self._session.close()

    async def get_stream_info(self, channel_name: str) -> StreamData:
        try:
            return await self._request_stream_info(channel_name)
        except RequestException as e:
            logger.error("Błąd przy odpytywaniu Kick API: %s", e)
            raise

    async def _request_stream_info(self, channel_name: str) -> StreamData:
        url = f"{KICK_CHANNELS_URL}/{channel_name.lower().strip()}"

        response = await self._session.get(url)
        response.raise_for_status()
        res_data = response.json()

        livestream = res_data.get("livestream")

        if not livestream:
            return StreamData(is_live=False)

        categories = livestream.get("categories") or []
        game_name = categories[0].get("name") if categories else None

        return StreamData(
            is_live=True,
            title=livestream.get("session_title"),
            viewer_count=livestream.get("viewer_count", 0),
            game_name=game_name,
            started_at=livestream.get("created_at"),
        )
