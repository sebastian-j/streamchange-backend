import logging
import time

import httpx

from src.config import (
    STREAMS_URL,
    TOKEN_URL,
    TWITCH_CLIENT_ID,
    TWITCH_CLIENT_SECRET,
)
from src.schemas.chat import StreamData

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_MARGIN = 60
REQUEST_TIMEOUT = 10


class TwitchAPIService:
    def __init__(self):
        self.client_id = TWITCH_CLIENT_ID
        self.client_secret = TWITCH_CLIENT_SECRET
        self._access_token = None
        self._token_expires_at = 0.0
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _invalidate_token(self) -> None:
        self._access_token = None
        self._token_expires_at = 0.0

    async def _get_app_access_token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            response = await self._client.post(TOKEN_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Twitch odrzucił żądanie o token: %s", e)
            raise
        except httpx.RequestError as e:
            logger.error("Błąd sieci przy pobieraniu tokenu Twitcha: %s", e)
            raise

        data = response.json()
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 0)
        self._token_expires_at = time.monotonic() + expires_in - TOKEN_EXPIRY_MARGIN
        return self._access_token

    async def get_stream_info(self, channel_name: str) -> StreamData:
        try:
            return await self._request_stream_info(channel_name)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.warning("Token Twitcha odrzucony, odświeżam.")
                self._invalidate_token()
                return await self._request_stream_info(channel_name)
            logger.error("Twitch API zwróciło błąd: %s", e)
            raise
        except httpx.RequestError as e:
            logger.error("Błąd sieci przy odpytywaniu Twitch API: %s", e)
            raise

    async def _request_stream_info(self, channel_name: str) -> StreamData:
        token = await self._get_app_access_token()
        headers = {"Client-ID": self.client_id, "Authorization": f"Bearer {token}"}
        params = {"user_login": channel_name.lower().strip()}

        response = await self._client.get(STREAMS_URL, headers=headers, params=params)
        response.raise_for_status()
        res_data = response.json()

        streams = res_data.get("data", [])

        if not streams:
            return StreamData(is_live=False)

        stream = streams[0]
        return StreamData(
            is_live=True,
            title=stream.get("title"),
            viewer_count=stream.get("viewer_count", 0),
            game_name=stream.get("game_name"),
            started_at=stream.get("started_at"),
        )
