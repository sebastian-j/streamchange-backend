import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.blacklist import check_blacklist, load_blacklist
from src.clients.kick_api import KickAPIService
from src.clients.twitch_api import TwitchAPIService
from src.hub import Hub
from src.schemas.chat import ChatMessage, StreamData

logging.basicConfig(
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

hub = Hub()
twitch_api = TwitchAPIService()
kick_api = KickAPIService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_blacklist()
    yield
    await twitch_api.aclose()
    await kick_api.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/check-blacklist")
async def check_blacklist_endpoint(
    channel: str = Query(..., description="Nazwa kanału"),
    platform: str = Query(..., description="Platforma"),
):
    entry = check_blacklist(channel, platform)
    if entry:
        return {
            "blacklisted": True,
            "reason": entry.get("reason", "Kanał nieobsługiwany."),
            "category": entry.get("category", "Nieznana"),
        }
    return {"blacklisted": False}


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


@app.get("/api/avatar")
async def get_avatar(
    user_id: str = Query(..., description="ID użytkownika"),
    platform: str = Query(..., description="Platforma"),
):
    if not user_id:
        raise HTTPException(status_code=400, detail="Brak ID użytkownika.")

    platform = platform.lower().strip()

    if platform == "twitch":
        try:
            return {"url": await twitch_api.get_avatar(user_id)}
        except Exception:
            logger.exception("Nie udało się pobrać avatara z API Twitcha.")
            raise HTTPException(status_code=500, detail="Nie udało się pobrać avatara.")
    elif platform == "kick":
        try:
            return {"url": await kick_api.get_avatar(user_id)}
        except Exception:
            logger.exception("Nie udało się pobrać avatara z API Kicka.")
            raise HTTPException(status_code=500, detail="Nie udało się pobrać avatara.")
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

        blacklist_entry = check_blacklist(channel, platform)
        if blacklist_entry:
            reason = blacklist_entry.get("reason", "Kanał nieobsługiwany.")
            await websocket.close(code=4003, reason=reason)
            logger.info("Zablokowane połączenie do %s/%s - %s", platform, channel, reason)
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
