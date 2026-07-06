import httpx
from src.config import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
from src.schemas.chat import StreamData

class TwitchAPIService:
    def __init__(self):
        self.client_id = TWITCH_CLIENT_ID
        self.client_secret = TWITCH_CLIENT_SECRET
        self._access_token = None

    async def _get_app_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def get_stream_info(self, channel_name: str) -> StreamData:
        token = await self._get_app_access_token()
        url = "https://api.twitch.tv/helix/streams"
        
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {token}"
        }
        params = {
            "user_login": channel_name.lower().strip()
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
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
                started_at=stream.get("started_at")
            )