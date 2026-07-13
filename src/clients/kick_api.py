import logging
import time

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import HTTPError, RequestException

from src.config import (
    KICK_CHANNELS_URL,
    KICK_CLIENT_ID,
    KICK_CLIENT_SECRET,
    KICK_TOKEN_URL,
    KICK_USERS_URL,
)
from src.schemas.chat import StreamData

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_MARGIN = 60
REQUEST_TIMEOUT = 10


class KickAPIService:
    def __init__(self):
        self._session = AsyncSession(impersonate="chrome", timeout=REQUEST_TIMEOUT)
        self.client_id = KICK_CLIENT_ID
        self.client_secret = KICK_CLIENT_SECRET
        self._access_token = None
        self._token_expires_at = 0.0

    async def aclose(self) -> None:
        await self._session.close()

    def _invalidate_token(self) -> None:
        self._access_token = None
        self._token_expires_at = 0.0

    async def _get_app_access_token(self) -> str:
        if self._access_token and time.monotonic() < self._token_expires_at:
            return self._access_token

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        response = await self._session.post(KICK_TOKEN_URL, data=data)
        response.raise_for_status()

        payload = response.json()
        self._access_token = payload["access_token"]
        expires_in = payload.get("expires_in", 0)
        self._token_expires_at = time.monotonic() + expires_in - TOKEN_EXPIRY_MARGIN
        return self._access_token

    async def get_avatar(self, user_id: str) -> str | None:
        try:
            return await self._request_avatar(user_id)
        except HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status == 401:
                logger.warning("Token Kicka odrzucony, odświeżam.")
                self._invalidate_token()
                return await self._request_avatar(user_id)
            logger.error("Kick API zwróciło błąd: %s", e)
            raise
        except RequestException as e:
            logger.error("Błąd przy odpytywaniu Kick API: %s", e)
            raise

    async def _request_avatar(self, user_id: str) -> str | None:
        token = await self._get_app_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {"id": user_id}

        response = await self._session.get(
            KICK_USERS_URL, headers=headers, params=params
        )
        response.raise_for_status()
        users = response.json().get("data", [])

        if not users:
            return None

        return users[0].get("profile_picture")

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
