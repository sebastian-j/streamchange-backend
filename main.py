from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.clients.twitch_client import TwitchClient

app = FastAPI()


@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    client = None

    try:
        config = await websocket.receive_json()
        channel = config.get("channel")
        platform = config.get("platform")

        if not channel:
            await websocket.close(code=4000, reason="Wrong channel name.")
            return
        elif platform != "twitch" and platform != "kick":
            await websocket.close(code=4001, reason="Unsupported platform.")
            return

        async def log_to_console(author: str, content: str):
            print(f"{author}: {content}")

        if platform == "twitch":
            client = TwitchClient(on_message=log_to_console)
        elif platform == "kick":
            # Tutaj dodać kick
            pass
        await client.connect(channel)

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if client:
            print("Disconnecting client...")
            await client.disconnect()
        print("WebSocket connection closed.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
