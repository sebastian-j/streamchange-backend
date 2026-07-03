import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.clients.twitch_client import TwitchClient
from src.clients.kick_client import KickClient
from src.resolvers.kick_resolver import get_chatroom_id
from src.schemas.chat import ChatMessage

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    client = None

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

        if platform == "twitch":
            client = TwitchClient(on_message=send)
            await client.connect(channel)
        elif platform == "kick":
            client = KickClient(on_message=send)
            chatroom_id = await asyncio.to_thread(get_chatroom_id, channel)
            await client.connect(chatroom_id)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        print("Klient rozłączony.")
    except Exception as e:
        print(f"Błąd: {e}")
    finally:
        if client:
            print("Rozłączam klienta...")
            await client.disconnect()
        print("Połączenie zamknięte.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)