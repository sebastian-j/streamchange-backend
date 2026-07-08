import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.schemas.chat import ChatMessage
from src.hub import Hub

logging.basicConfig(
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

app = FastAPI()
hub = Hub()
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from src.clients.twitch_client import TwitchClient
from src.clients.kick_client import KickClient
from src.resolvers.kick_resolver import get_chatroom_id
from src.schemas.chat import ChatMessage, StreamData
from src.clients.twitch_api import TwitchAPIService
from src.clients.kick_api import KickAPIService

twitch_api = TwitchAPIService()
kick_api = KickAPIService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await twitch_api.aclose()
    await kick_api.aclose()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stream-info", response_model=StreamData)
async def get_stream_info(
    channel: str = Query(..., description="Nazwa kanału"),
    platform: str = Query(..., description="Platforma"),
):
    if not channel:
        raise HTTPException(status_code=400, detail="Zła nazwa kanału.")

    platform = platform.lower().strip()

    if platform == "twitch":
        try:
            return await twitch_api.get_stream_info(channel)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Nie udało się pobrać danych z API Twitcha: {e}",
            )
    elif platform == "kick":
        try:
            return await kick_api.get_stream_info(channel)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Nie udało się pobrać danych z API Kicka: {e}",
            )
    else:
        raise HTTPException(status_code=400, detail="Nieobsługiwana platforma.")


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    key = None
    send = None

    try:
        config = await websocket.receive_json()
        channel = config.get("channel")
        platform = config.get("platform")

        if not channel:
            await websocket.close(code=4000, reason="Zła nazwa kanału.")
            return
        elif platform != "twitch" and platform != "kick":
            await websocket.close(code=4001, reason="Nieobsługiwana platforma.")
            return

        async def send(chat_msg: ChatMessage):
            await websocket.send_json(chat_msg.model_dump())

        key = await hub.subscribe(channel, platform, send)
        logger.info("Klient podłączony do %s/%s", platform, channel)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        logger.info("Klient rozłączony.")
    except Exception:
        logger.exception("Błąd w obsłudze połączenia WebSocket.")
    finally:
        if key is not None and send is not None:
            await hub.unsubscribe(key, send)
        logger.info("Połączenie zamknięte.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
