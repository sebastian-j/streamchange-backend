from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from src.schemas.chat import ChatMessage
from src.hub import Hub

app = FastAPI()
hub = Hub()


@app.get("/health")
async def health():
    return {"status": "ok"}


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

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        print("Klient rozłączony.")
    except Exception as e:
        print(f"Błąd: {e}")
    finally:
        if key is not None and send is not None:
            await hub.unsubscribe(key, send)
        print("Połączenie zamknięte.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
